"""
AirAd Backend — Discount Service Layer (Phase B §B-6, R4)

All discount business logic lives here — views are thin wrappers.
Tier-gated happy hours enforced via SubscriptionPackage.daily_happy_hours_allowed.
Every mutation calls AuditLog (R5).
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.subscriptions.models import SubscriptionPackage
from apps.vendors.models import Discount, DiscountType, Vendor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_ip(request: Any) -> str:
    if request is None:
        return ""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _daily_happy_hour_count(vendor_id: str) -> int:
    """Count happy hours created today for a vendor."""
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return Discount.objects.filter(
        vendor_id=vendor_id,
        discount_type=DiscountType.HAPPY_HOUR,
        created_at__gte=today_start,
    ).count()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def list_vendor_discounts(vendor_id: str) -> list[dict]:
    """List all discounts for a vendor.

    Args:
        vendor_id: UUID of the vendor.

    Returns:
        List of discount dicts.
    """
    discounts = Discount.objects.filter(vendor_id=vendor_id).order_by("-created_at")
    result = []
    for d in discounts:
        result.append({
            "id": str(d.pk),
            "title": d.title,
            "discount_type": d.discount_type,
            "value": str(d.value),
            "applies_to": d.applies_to,
            "item_description": d.item_description,
            "start_time": d.start_time.isoformat(),
            "end_time": d.end_time.isoformat(),
            "is_recurring": d.is_recurring,
            "recurrence_days": d.recurrence_days,
            "is_active": d.is_active,
            "min_order_value": str(d.min_order_value),
            "ar_badge_text": d.ar_badge_text,
            "delivery_radius_m": d.delivery_radius_m,
            "free_delivery_distance_m": d.free_delivery_distance_m,
            "views_during_campaign": d.views_during_campaign,
            "taps_during_campaign": d.taps_during_campaign,
            "navigation_clicks_during_campaign": d.navigation_clicks_during_campaign,
            "created_at": d.created_at.isoformat(),
        })
    return result


@transaction.atomic
def create_discount(
    vendor_id: str,
    data: dict,
    *,
    request: Any = None,
) -> Discount:
    """Create a discount for a vendor.

    Args:
        vendor_id: UUID of the vendor.
        data: Dict with discount fields.
        request: HTTP request for audit logging.

    Returns:
        The created Discount instance.

    Raises:
        Vendor.DoesNotExist: If vendor not found.
    """
    vendor = Vendor.objects.get(pk=vendor_id)

    discount = Discount.objects.create(
        vendor=vendor,
        title=data["title"],
        discount_type=data["discount_type"],
        value=data["value"],
        applies_to=data.get("applies_to", "ALL"),
        item_description=data.get("item_description", ""),
        start_time=data["start_time"],
        end_time=data["end_time"],
        is_recurring=data.get("is_recurring", False),
        recurrence_days=data.get("recurrence_days", []),
        min_order_value=data.get("min_order_value", 0),
        ar_badge_text=data.get("ar_badge_text", ""),
        delivery_radius_m=data.get("delivery_radius_m"),
        free_delivery_distance_m=data.get("free_delivery_distance_m"),
    )

    AuditLog.objects.create(
        action="DISCOUNT_CREATED",
        entity_type="Discount",
        entity_id=str(discount.pk),
        actor_id=str(vendor.owner_id) if vendor.owner_id else None,
        ip_address=_get_ip(request),
        metadata={"title": data["title"], "vendor_id": str(vendor_id)},
    )
    logger.info("Discount created: %s for vendor %s", discount.pk, vendor_id)
    return discount


@transaction.atomic
def update_discount(
    discount_id: str,
    vendor_id: str,
    data: dict,
    *,
    request: Any = None,
) -> Discount:
    """Partially update a discount.

    Args:
        discount_id: UUID of the discount.
        vendor_id: UUID of the vendor (ownership check).
        data: Dict of fields to update.
        request: HTTP request for audit logging.

    Returns:
        Updated Discount instance.

    Raises:
        Discount.DoesNotExist: If not found or not owned by vendor.
    """
    discount = Discount.objects.get(pk=discount_id, vendor_id=vendor_id)

    allowed = {
        "title", "value", "applies_to", "item_description",
        "start_time", "end_time", "is_recurring", "recurrence_days",
        "min_order_value", "ar_badge_text", "delivery_radius_m",
        "free_delivery_distance_m",
    }
    changed = {}
    for field in allowed:
        if field in data:
            old_val = getattr(discount, field)
            setattr(discount, field, data[field])
            changed[field] = {"old": str(old_val), "new": str(data[field])}

    if changed:
        discount.save(update_fields=[*changed.keys(), "updated_at"])
        AuditLog.objects.create(
            action="DISCOUNT_UPDATED",
            entity_type="Discount",
            entity_id=str(discount.pk),
            actor_id=str(discount.vendor.owner_id) if discount.vendor.owner_id else None,
            ip_address=_get_ip(request),
            metadata=changed,
        )
        logger.info("Discount updated: %s — fields: %s", discount_id, list(changed.keys()))

    return discount


@transaction.atomic
def deactivate_discount(
    discount_id: str,
    vendor_id: str,
    *,
    request: Any = None,
) -> None:
    """Deactivate a discount (soft-delete).

    Args:
        discount_id: UUID of the discount.
        vendor_id: UUID of the vendor (ownership check).
        request: HTTP request for audit logging.

    Raises:
        Discount.DoesNotExist: If not found or not owned by vendor.
    """
    discount = Discount.objects.get(pk=discount_id, vendor_id=vendor_id)
    discount.is_active = False
    discount.save(update_fields=["is_active", "updated_at"])

    AuditLog.objects.create(
        action="DISCOUNT_DEACTIVATED",
        entity_type="Discount",
        entity_id=str(discount.pk),
        actor_id=str(discount.vendor.owner_id) if discount.vendor.owner_id else None,
        ip_address=_get_ip(request),
        metadata={"vendor_id": str(vendor_id)},
    )
    logger.info("Discount deactivated: %s", discount_id)


def get_discount_analytics(discount_id: str, vendor_id: str) -> dict:
    """Get campaign performance analytics for a discount.

    Args:
        discount_id: UUID of the discount.
        vendor_id: UUID of the vendor (ownership check).

    Returns:
        Dict with campaign performance metrics.

    Raises:
        Discount.DoesNotExist: If not found or not owned by vendor.
    """
    d = Discount.objects.get(pk=discount_id, vendor_id=vendor_id)
    return {
        "id": str(d.pk),
        "title": d.title,
        "is_active": d.is_active,
        "start_time": d.start_time.isoformat(),
        "end_time": d.end_time.isoformat(),
        "views_during_campaign": d.views_during_campaign,
        "taps_during_campaign": d.taps_during_campaign,
        "navigation_clicks_during_campaign": d.navigation_clicks_during_campaign,
        "is_currently_active": d.is_currently_active,
    }


# ---------------------------------------------------------------------------
# Happy Hour (tier-gated)
# ---------------------------------------------------------------------------

@transaction.atomic
def create_happy_hour(
    vendor_id: str,
    data: dict,
    *,
    request: Any = None,
) -> Discount:
    """Create a happy hour discount (tier-gated).

    Args:
        vendor_id: UUID of the vendor.
        data: Dict with happy hour fields.
        request: HTTP request for audit logging.

    Returns:
        The created Discount instance.

    Raises:
        ValueError: If vendor has exceeded daily happy hour limit for their tier.
        Vendor.DoesNotExist: If vendor not found.
    """
    vendor = Vendor.objects.get(pk=vendor_id)
    pkg = SubscriptionPackage.objects.filter(
        level=vendor.subscription_level, is_active=True
    ).first()

    daily_limit = pkg.daily_happy_hours_allowed if pkg else 0
    if daily_limit == 0:
        raise ValueError("Happy hours are not available on your subscription tier.")

    current_count = _daily_happy_hour_count(vendor_id)
    if current_count >= daily_limit:
        raise ValueError(
            f"Daily happy hour limit reached ({current_count}/{daily_limit})."
        )

    data["discount_type"] = DiscountType.HAPPY_HOUR
    if not data.get("ar_badge_text"):
        data["ar_badge_text"] = "Happy Hour"

    return create_discount(vendor_id, data, request=request)


# ---------------------------------------------------------------------------
# Admin moderation
# ---------------------------------------------------------------------------

@transaction.atomic
def admin_remove_discount(
    discount_id: str,
    notes: str = "",
    *,
    admin_user: Any = None,
    request: Any = None,
) -> None:
    """Admin removal of a fraudulent/violating discount.

    Args:
        discount_id: UUID of the discount.
        notes: Admin notes for removal reason.
        admin_user: AdminUser performing the action.
        request: HTTP request for audit logging.

    Raises:
        Discount.DoesNotExist: If not found.
    """
    discount = Discount.objects.get(pk=discount_id)
    discount.is_active = False
    discount.save(update_fields=["is_active", "updated_at"])

    AuditLog.objects.create(
        action="DISCOUNT_ADMIN_REMOVED",
        entity_type="Discount",
        entity_id=str(discount.pk),
        actor_id=str(admin_user.pk) if admin_user else None,
        ip_address=_get_ip(request),
        metadata={
            "notes": notes,
            "vendor_id": str(discount.vendor_id),
            "title": discount.title,
        },
    )
    logger.info("Discount admin-removed: %s by %s", discount_id, admin_user)
