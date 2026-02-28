"""
AirAd Backend — Admin Vendor Management Service Layer (Phase B §3.7)

All admin management logic lives here — views only call these functions.
Every mutation calls log_action() (R5).
All multi-step mutations wrapped in @transaction.atomic.
"""

import logging
from typing import Any

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.audit.utils import log_action

logger = logging.getLogger(__name__)


@transaction.atomic
def verify_vendor(
    vendor_id: str,
    actor: Any,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Mark a vendor as admin-verified (badge in UI).

    Args:
        vendor_id: UUID string of the vendor.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Dict with updated vendor status.

    Raises:
        ValueError: If vendor not found.
    """
    from apps.vendors.models import Vendor

    try:
        vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    except Vendor.DoesNotExist:
        raise ValueError("Vendor not found")

    before = {"is_verified": vendor.is_verified}
    vendor.is_verified = True
    vendor.save(update_fields=["is_verified", "updated_at"])

    log_action(
        action="VENDOR_VERIFIED",
        actor=actor,
        target_obj=vendor,
        request=request,
        before=before,
        after={"is_verified": True},
    )

    return {
        "vendor_id": str(vendor.id),
        "business_name": vendor.business_name,
        "is_verified": vendor.is_verified,
    }


@transaction.atomic
def suspend_vendor(
    vendor_id: str,
    reason: str,
    actor: Any,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Suspend a vendor — soft-deletes and logs the reason.

    Args:
        vendor_id: UUID string of the vendor.
        reason: Suspension reason text.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Dict with suspension status.

    Raises:
        ValueError: If vendor not found or reason is empty.
    """
    from apps.vendors.models import Vendor

    if not reason or not reason.strip():
        raise ValueError("Suspension reason is required")

    try:
        vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    except Vendor.DoesNotExist:
        raise ValueError("Vendor not found")

    before = {
        "is_deleted": vendor.is_deleted,
        "is_verified": vendor.is_verified,
    }

    vendor.is_deleted = True
    vendor.is_verified = False
    vendor.save(update_fields=["is_deleted", "is_verified", "updated_at"])

    log_action(
        action="VENDOR_SUSPENDED",
        actor=actor,
        target_obj=vendor,
        request=request,
        before=before,
        after={
            "is_deleted": True,
            "is_verified": False,
            "suspension_reason": reason,
        },
    )

    return {
        "vendor_id": str(vendor.id),
        "business_name": vendor.business_name,
        "suspended": True,
        "reason": reason,
    }


@transaction.atomic
def approve_claim(
    vendor_id: str,
    actor: Any,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Approve a vendor claim — set claimed_status to CLAIMED.

    Args:
        vendor_id: UUID string of the vendor.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Dict with claim status.

    Raises:
        ValueError: If vendor not found or not in CLAIM_PENDING state.
    """
    from apps.vendors.models import ClaimedStatus, Vendor

    try:
        vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    except Vendor.DoesNotExist:
        raise ValueError("Vendor not found")

    if vendor.claimed_status != ClaimedStatus.CLAIM_PENDING:
        raise ValueError(
            f"Vendor claim status must be CLAIM_PENDING to approve (current: {vendor.claimed_status})"
        )

    before = {"claimed_status": vendor.claimed_status}
    vendor.claimed_status = ClaimedStatus.CLAIMED
    vendor.claimed_at = timezone.now()
    vendor.save(update_fields=["claimed_status", "claimed_at", "updated_at"])

    log_action(
        action="VENDOR_CLAIM_APPROVED",
        actor=actor,
        target_obj=vendor,
        request=request,
        before=before,
        after={"claimed_status": ClaimedStatus.CLAIMED},
    )

    return {
        "vendor_id": str(vendor.id),
        "business_name": vendor.business_name,
        "claimed_status": vendor.claimed_status,
        "claimed_at": vendor.claimed_at.isoformat() if vendor.claimed_at else None,
    }


@transaction.atomic
def reject_claim(
    vendor_id: str,
    reason: str,
    actor: Any,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Reject a vendor claim — set claimed_status to CLAIM_REJECTED.

    Args:
        vendor_id: UUID string of the vendor.
        reason: Rejection reason text.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Dict with claim rejection status.

    Raises:
        ValueError: If vendor not found, not pending, or reason empty.
    """
    from apps.vendors.models import ClaimedStatus, Vendor

    if not reason or not reason.strip():
        raise ValueError("Rejection reason is required")

    try:
        vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    except Vendor.DoesNotExist:
        raise ValueError("Vendor not found")

    if vendor.claimed_status != ClaimedStatus.CLAIM_PENDING:
        raise ValueError(
            f"Vendor claim status must be CLAIM_PENDING to reject (current: {vendor.claimed_status})"
        )

    before = {"claimed_status": vendor.claimed_status}
    vendor.claimed_status = ClaimedStatus.CLAIM_REJECTED
    vendor.owner = None
    vendor.save(update_fields=["claimed_status", "owner", "updated_at"])

    log_action(
        action="VENDOR_CLAIM_REJECTED",
        actor=actor,
        target_obj=vendor,
        request=request,
        before=before,
        after={
            "claimed_status": ClaimedStatus.CLAIM_REJECTED,
            "rejection_reason": reason,
        },
    )

    return {
        "vendor_id": str(vendor.id),
        "business_name": vendor.business_name,
        "claimed_status": vendor.claimed_status,
        "reason": reason,
    }


@transaction.atomic
def approve_location(
    vendor_id: str,
    actor: Any,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Approve a vendor location change request.

    Args:
        vendor_id: UUID string of the vendor.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Dict with location approval status.

    Raises:
        ValueError: If vendor not found or no pending location.
    """
    from apps.vendors.models import Vendor

    try:
        vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    except Vendor.DoesNotExist:
        raise ValueError("Vendor not found")

    if not vendor.location_pending_review:
        raise ValueError("No pending location change for this vendor")

    before = {"location_pending_review": True}
    vendor.location_pending_review = False
    vendor.save(update_fields=["location_pending_review", "updated_at"])

    log_action(
        action="VENDOR_LOCATION_APPROVED",
        actor=actor,
        target_obj=vendor,
        request=request,
        before=before,
        after={"location_pending_review": False},
    )

    return {
        "vendor_id": str(vendor.id),
        "business_name": vendor.business_name,
        "location_pending_review": False,
    }


@transaction.atomic
def reject_location(
    vendor_id: str,
    reason: str,
    actor: Any,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Reject a vendor location change request — revert to baseline GPS.

    Args:
        vendor_id: UUID string of the vendor.
        reason: Rejection reason text.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Dict with location rejection status.

    Raises:
        ValueError: If vendor not found or reason empty.
    """
    from apps.vendors.models import Vendor

    if not reason or not reason.strip():
        raise ValueError("Rejection reason is required")

    try:
        vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    except Vendor.DoesNotExist:
        raise ValueError("Vendor not found")

    before = {
        "location_pending_review": vendor.location_pending_review,
    }

    if vendor.gps_baseline:
        vendor.gps_point = vendor.gps_baseline

    vendor.location_pending_review = False
    vendor.save(update_fields=["location_pending_review", "gps_point", "updated_at"])

    log_action(
        action="VENDOR_LOCATION_REJECTED",
        actor=actor,
        target_obj=vendor,
        request=request,
        before=before,
        after={
            "location_pending_review": False,
            "rejection_reason": reason,
            "reverted_to_baseline": bool(vendor.gps_baseline),
        },
    )

    return {
        "vendor_id": str(vendor.id),
        "business_name": vendor.business_name,
        "location_pending_review": False,
        "reason": reason,
    }


@transaction.atomic
def launch_city(
    city_id: str,
    actor: Any,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Mark a city as active/launched.

    Args:
        city_id: UUID string of the city.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Dict with city launch status.

    Raises:
        ValueError: If city not found.
    """
    from apps.geo.models import City

    try:
        city = City.objects.get(id=city_id)
    except City.DoesNotExist:
        raise ValueError("City not found")

    before = {"is_active": city.is_active}
    city.is_active = True
    city.save(update_fields=["is_active"])

    log_action(
        action="CITY_LAUNCHED",
        actor=actor,
        target_obj=city,
        request=request,
        before=before,
        after={"is_active": True},
    )

    return {
        "city_id": str(city.id),
        "city_name": city.name,
        "is_active": True,
    }


@transaction.atomic
def bulk_assign_tags(
    vendor_ids: list[str],
    tag_ids: list[str],
    actor: Any,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Bulk assign tags to multiple vendors.

    Args:
        vendor_ids: List of vendor UUID strings.
        tag_ids: List of tag UUID strings.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Dict with assignment summary.

    Raises:
        ValueError: If no vendor_ids or tag_ids provided.
    """
    from apps.tags.models import Tag, TagType
    from apps.vendors.models import Vendor

    if not vendor_ids or not tag_ids:
        raise ValueError("vendor_ids and tag_ids are required")

    tags = Tag.objects.filter(id__in=tag_ids, is_active=True).exclude(
        tag_type=TagType.SYSTEM
    )
    if not tags.exists():
        raise ValueError("No valid non-SYSTEM tags found")

    vendors = Vendor.objects.filter(id__in=vendor_ids, is_deleted=False)
    if not vendors.exists():
        raise ValueError("No valid vendors found")

    assigned_count = 0
    for vendor in vendors:
        vendor.tags.add(*tags)
        assigned_count += 1

    tag_names = list(tags.values_list("name", flat=True))

    log_action(
        action="BULK_TAG_ASSIGNED",
        actor=actor,
        target_obj=None,
        request=request,
        before={},
        after={
            "vendor_count": assigned_count,
            "tags": tag_names,
        },
    )

    return {
        "vendors_updated": assigned_count,
        "tags_assigned": tag_names,
    }


def get_moderation_queue() -> dict[str, Any]:
    """Return combined moderation queue: pending reels + pending claims.

    Returns:
        Dict with pending_reels and pending_claims lists.
    """
    from apps.reels.models import VendorReel
    from apps.vendors.models import Vendor

    # Pending reels awaiting moderation
    pending_reels = VendorReel.objects.filter(
        moderation_status="PENDING", is_active=True
    ).select_related("vendor__area").order_by("created_at")[:50]

    def _thumbnail_url(s3_key: str) -> str:
        """Generate presigned thumbnail URL, return empty string on failure."""
        if not s3_key:
            return ""
        try:
            from core.storage import generate_presigned_url
            return generate_presigned_url(s3_key)
        except Exception:
            return ""

    reels_list = [
        {
            "id": str(r.pk),
            "title": r.title,
            "vendor_name": r.vendor.business_name,
            "vendor_id": str(r.vendor_id),
            "vendor_area": r.vendor.area.name if r.vendor.area_id else "",
            "duration_seconds": r.duration_seconds,
            "thumbnail_url": _thumbnail_url(r.thumbnail_s3_key),
            "s3_key": r.s3_key,
            "moderation_notes": r.moderation_notes,
            "view_count": r.view_count,
            "created_at": r.created_at.isoformat(),
        }
        for r in pending_reels
    ]

    # Pending claims
    pending_claims = Vendor.objects.filter(
        claimed_status="CLAIM_PENDING", is_deleted=False
    ).select_related("area").order_by("updated_at")[:50]

    claims_list = [
        {
            "vendor_id": str(v.pk),
            "business_name": v.business_name,
            "area_name": v.area.name if v.area_id else "",
            "claimed_by": str(v.owner_id) if v.owner_id else None,
            "updated_at": v.updated_at.isoformat(),
            "created_at": v.created_at.isoformat(),
        }
        for v in pending_claims
    ]

    return {
        "pending_reels": reels_list,
        "pending_reels_count": len(reels_list),
        "pending_claims": claims_list,
        "pending_claims_count": len(claims_list),
        "total_pending": len(reels_list) + len(claims_list),
    }
