"""
AirAd Backend — Reel Service Layer (Phase B §B-9, R4)

All reel business logic lives here — views are thin wrappers.
Tier-based upload limits enforced via SubscriptionPackage.max_videos.
Every mutation calls log_action() (R5).
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.audit.utils import log_action
from apps.reels.models import ModerationStatus, ReelStatus, VendorReel
from apps.subscriptions.models import SubscriptionPackage
from apps.vendors.models import Vendor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_reel_limit(vendor: Vendor) -> int:
    """Return the maximum number of active reels allowed for a vendor's tier.

    Returns:
        Max reel count. 999 means effectively unlimited (Platinum).
    """
    pkg = SubscriptionPackage.objects.filter(
        level=vendor.subscription_level, is_active=True
    ).first()
    if not pkg:
        return 1  # fallback to Silver default
    return pkg.max_videos


def _active_reel_count(vendor_id) -> int:
    """Count active (non-archived) reels for a vendor."""
    return VendorReel.objects.filter(
        vendor_id=vendor_id,
        is_active=True,
    ).exclude(status=ReelStatus.ARCHIVED).count()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@transaction.atomic
def create_reel(
    vendor_id: str,
    title: str,
    s3_key: str,
    duration_seconds: int,
    thumbnail_s3_key: str = "",
    *,
    request: Any = None,
) -> VendorReel:
    """Create a new reel for a vendor, enforcing tier upload limits.

    Args:
        vendor_id: UUID of the vendor.
        title: Reel display title.
        s3_key: S3 object key of the uploaded video.
        duration_seconds: Duration in seconds.
        thumbnail_s3_key: Optional thumbnail S3 key.
        request: HTTP request for audit logging.

    Returns:
        The created VendorReel instance.

    Raises:
        ValueError: If the vendor has reached their tier reel limit.
        Vendor.DoesNotExist: If vendor_id is invalid.
    """
    vendor = Vendor.objects.get(pk=vendor_id)
    limit = _get_reel_limit(vendor)
    current = _active_reel_count(vendor_id)

    if current >= limit:
        raise ValueError(
            f"Reel limit reached ({current}/{limit}). "
            f"Upgrade subscription to upload more reels."
        )

    reel = VendorReel.objects.create(
        vendor=vendor,
        title=title,
        s3_key=s3_key,
        thumbnail_s3_key=thumbnail_s3_key,
        duration_seconds=duration_seconds,
        status=ReelStatus.PROCESSING,
        moderation_status=ModerationStatus.PENDING,
    )

    log_action(
        action="REEL_CREATED",
        actor=None,
        target_obj=reel,
        request=request,
        before={},
        after={"title": title, "vendor_id": str(vendor_id)},
    )
    logger.info("Reel created: %s for vendor %s", reel.pk, vendor_id)
    return reel


def list_vendor_reels(vendor_id: str) -> list[dict]:
    """List all reels for a vendor (owner view — includes all statuses).

    Args:
        vendor_id: UUID of the vendor.

    Returns:
        List of reel dicts with presigned URLs.
    """
    from core.storage import generate_presigned_url

    reels = VendorReel.objects.filter(
        vendor_id=vendor_id, is_active=True
    ).order_by("display_order", "-created_at")

    result = []
    for r in reels:
        entry = {
            "id": str(r.pk),
            "title": r.title,
            "video_url": generate_presigned_url(r.s3_key) if r.s3_key else None,
            "thumbnail_url": (
                generate_presigned_url(r.thumbnail_s3_key)
                if r.thumbnail_s3_key
                else None
            ),
            "duration_seconds": r.duration_seconds,
            "status": r.status,
            "moderation_status": r.moderation_status,
            "view_count": r.view_count,
            "completion_count": r.completion_count,
            "display_order": r.display_order,
            "created_at": r.created_at.isoformat(),
        }
        result.append(entry)
    return result


def list_public_reels(vendor_slug: str) -> list[dict]:
    """List publicly visible reels for a vendor (ACTIVE + APPROVED only).

    Args:
        vendor_slug: Slug of the vendor.

    Returns:
        List of public reel dicts with presigned URLs.
    """
    from core.storage import generate_presigned_url

    reels = VendorReel.objects.filter(
        vendor__slug=vendor_slug,
        status=ReelStatus.ACTIVE,
        moderation_status=ModerationStatus.APPROVED,
        is_active=True,
    ).order_by("display_order", "-created_at")

    result = []
    for r in reels:
        result.append({
            "id": str(r.pk),
            "title": r.title,
            "video_url": generate_presigned_url(r.s3_key) if r.s3_key else None,
            "thumbnail_url": (
                generate_presigned_url(r.thumbnail_s3_key)
                if r.thumbnail_s3_key
                else None
            ),
            "duration_seconds": r.duration_seconds,
            "view_count": r.view_count,
            "display_order": r.display_order,
            "created_at": r.created_at.isoformat(),
        })
    return result


@transaction.atomic
def update_reel(
    reel_id: str,
    vendor_id: str,
    data: dict,
    *,
    request: Any = None,
) -> VendorReel:
    """Update reel metadata (title, display_order, thumbnail).

    Args:
        reel_id: UUID of the reel.
        vendor_id: UUID of the vendor (ownership check).
        data: Dict of fields to update.
        request: HTTP request for audit logging.

    Returns:
        Updated VendorReel instance.

    Raises:
        VendorReel.DoesNotExist: If reel not found or not owned by vendor.
    """
    reel = VendorReel.objects.get(pk=reel_id, vendor_id=vendor_id, is_active=True)

    allowed = {"title", "display_order", "thumbnail_s3_key"}
    changed = {}
    for field in allowed:
        if field in data:
            old_val = getattr(reel, field)
            setattr(reel, field, data[field])
            changed[field] = {"old": old_val, "new": data[field]}

    if changed:
        reel.save(update_fields=[*changed.keys(), "updated_at"])
        log_action(
            action="REEL_UPDATED",
            actor=None,
            target_obj=reel,
            request=request,
            before={k: v["old"] for k, v in changed.items()},
            after={k: v["new"] for k, v in changed.items()},
        )
        logger.info("Reel updated: %s — fields: %s", reel_id, list(changed.keys()))

    return reel


@transaction.atomic
def archive_reel(
    reel_id: str,
    vendor_id: str,
    *,
    request: Any = None,
) -> None:
    """Archive (soft-delete) a reel.

    Args:
        reel_id: UUID of the reel.
        vendor_id: UUID of the vendor (ownership check).
        request: HTTP request for audit logging.

    Raises:
        VendorReel.DoesNotExist: If reel not found or not owned by vendor.
    """
    reel = VendorReel.objects.get(pk=reel_id, vendor_id=vendor_id, is_active=True)
    reel.status = ReelStatus.ARCHIVED
    reel.is_active = False
    reel.save(update_fields=["status", "is_active", "updated_at"])

    log_action(
        action="REEL_ARCHIVED",
        actor=None,
        target_obj=reel,
        request=request,
        before={"status": ReelStatus.ACTIVE, "is_active": True},
        after={"status": ReelStatus.ARCHIVED, "is_active": False},
    )
    logger.info("Reel archived: %s", reel_id)


def record_reel_view(reel_id: str) -> None:
    """Increment view count for a reel and dispatch analytics event.

    Args:
        reel_id: UUID of the reel.
    """
    from apps.analytics.models import AnalyticsEvent, EventType
    from django.db.models import F

    updated = VendorReel.objects.filter(pk=reel_id, is_active=True).update(
        view_count=F("view_count") + 1
    )
    if not updated:
        return

    reel = VendorReel.objects.filter(pk=reel_id).values("vendor_id").first()
    if reel:
        AnalyticsEvent.objects.create(
            event_type=EventType.REEL_VIEWED,
            vendor_id=reel["vendor_id"],
            metadata={"reel_id": str(reel_id)},
        )


# ---------------------------------------------------------------------------
# Admin moderation
# ---------------------------------------------------------------------------

@transaction.atomic
def moderate_reel(
    reel_id: str,
    status: str,
    notes: str = "",
    *,
    admin_user: Any = None,
    request: Any = None,
) -> VendorReel:
    """Approve or reject a reel (admin action).

    Args:
        reel_id: UUID of the reel.
        status: Target moderation status (APPROVED or REJECTED).
        notes: Admin notes.
        admin_user: AdminUser performing the action.
        request: HTTP request for audit logging.

    Returns:
        Updated VendorReel instance.

    Raises:
        VendorReel.DoesNotExist: If reel not found.
        ValueError: If status is invalid.
    """
    if status not in (ModerationStatus.APPROVED, ModerationStatus.REJECTED):
        raise ValueError(f"Invalid moderation status: {status}")

    reel = VendorReel.objects.select_for_update().get(pk=reel_id)
    reel.moderation_status = status
    reel.moderation_notes = notes

    # Auto-activate approved reels, deactivate rejected ones
    if status == ModerationStatus.APPROVED:
        reel.status = ReelStatus.ACTIVE
    elif status == ModerationStatus.REJECTED:
        reel.status = ReelStatus.REJECTED

    reel.save(update_fields=[
        "moderation_status", "moderation_notes", "status", "updated_at"
    ])

    log_action(
        action=f"REEL_{status}",
        actor=admin_user,
        target_obj=reel,
        request=request,
        before={"moderation_status": ModerationStatus.PENDING},
        after={"moderation_status": status, "notes": notes},
    )
    logger.info("Reel %s: %s by admin %s", status.lower(), reel_id, admin_user)
    return reel


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_ip(request: Any) -> str:
    """Extract client IP from request, return empty string if unavailable."""
    if request is None:
        return ""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
