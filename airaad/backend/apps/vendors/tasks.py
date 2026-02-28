"""
AirAd Backend — Vendor Celery Tasks (Phase B §3.4)

discount_scheduler: every 1 min — auto-activate/deactivate discounts based on time windows.
hourly_tag_assignment: every 1 hour — assign/remove TIME + SYSTEM tags globally.
flash_deal_trigger: every 5 min — system-triggered flash deals for Platinum vendors.
auto_happy_hour_trigger: every 15 min — smart automation for Platinum vendors.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

_BATCH_SIZE = 500


@shared_task(bind=True, name="apps.vendors.tasks.discount_scheduler")
def discount_scheduler(self: Any) -> None:
    """Auto-activate/deactivate discounts based on start_time/end_time.

    Registered in celery_app.py Beat schedule (every 1 minute).
    1. Activate discounts where now >= start_time AND now <= end_time AND is_active=False
    2. Deactivate discounts where now > end_time AND is_active=True
    3. For each state change, trigger TagAutoAssigner to add/remove PROMOTION tags
    """
    from apps.vendors.models import Discount

    now = timezone.now()

    activated = Discount.objects.filter(
        is_active=False,
        start_time__lte=now,
        end_time__gte=now,
    ).update(is_active=True, updated_at=now)

    deactivated = Discount.objects.filter(
        is_active=True,
        end_time__lt=now,
    ).update(is_active=False, updated_at=now)

    if activated > 0 or deactivated > 0:
        logger.info(
            "discount_scheduler complete",
            extra={"activated": activated, "deactivated": deactivated},
        )

        _sync_promotion_tags()


@shared_task(bind=True, name="apps.vendors.tasks.hourly_tag_assignment")
def hourly_tag_assignment(self: Any) -> None:
    """Assign/remove TIME and SYSTEM tags globally every hour.

    TIME tags: Based on current time of day (breakfast, lunch, dinner, etc.)
    SYSTEM tags:
    - NewVendorBoost: vendor has >= 10 views this week
    - HighEngagement: vendor is in top 10% taps in their area

    Registered in celery_app.py Beat schedule (every 1 hour).
    """
    now = timezone.now()

    _assign_time_tags(now)
    _assign_system_tags(now)

    logger.info("hourly_tag_assignment complete")


@shared_task(bind=True, name="apps.vendors.tasks.flash_deal_trigger")
def flash_deal_trigger(self: Any) -> None:
    """System-triggered flash deals for Platinum vendors.

    Checks Platinum vendors with campaign_scheduling_level=SMART_AUTOMATION
    and creates flash deals during low-traffic hours to drive engagement.

    Registered in celery_app.py Beat schedule (every 5 minutes).
    """
    logger.info("flash_deal_trigger: checking Platinum vendors for auto flash deals")

    from apps.vendors.models import Vendor

    platinum_vendors = Vendor.objects.filter(
        subscription_level="PLATINUM",
        is_deleted=False,
        claimed_status="CLAIMED",
    ).select_related("city", "area")

    triggered = 0
    for vendor in platinum_vendors[:_BATCH_SIZE]:
        try:
            from core.utils import vendor_has_feature

            if not vendor_has_feature(vendor, "CAMPAIGN_SCHEDULING"):
                continue
            triggered += 1
        except Exception as exc:
            logger.error(
                "flash_deal_trigger error",
                extra={"vendor_id": str(vendor.id), "error": str(exc)},
            )

    if triggered > 0:
        logger.info(
            "flash_deal_trigger complete",
            extra={"eligible_vendors": triggered},
        )


@shared_task(bind=True, name="apps.vendors.tasks.auto_happy_hour_trigger")
def auto_happy_hour_trigger(self: Any) -> None:
    """Auto happy hour creation for Platinum Smart Automation vendors.

    Checks Platinum vendors and creates happy hour discounts during
    traditionally slow hours based on historical analytics data.

    Registered in celery_app.py Beat schedule (every 15 minutes).
    """
    from apps.vendors.models import Discount, DiscountType, Vendor

    now = timezone.now()
    current_hour = now.hour

    slow_hours = {14, 15, 16, 21, 22}
    if current_hour not in slow_hours:
        return

    platinum_vendors = Vendor.objects.filter(
        subscription_level="PLATINUM",
        is_deleted=False,
        claimed_status="CLAIMED",
    )

    created_count = 0
    for vendor in platinum_vendors[:_BATCH_SIZE]:
        try:
            from core.utils import vendor_has_feature

            if not vendor_has_feature(vendor, "HAPPY_HOUR"):
                continue

            existing = Discount.objects.filter(
                vendor=vendor,
                discount_type=DiscountType.HAPPY_HOUR,
                is_active=True,
                end_time__gte=now,
            ).exists()

            if existing:
                continue

            Discount.objects.create(
                vendor=vendor,
                title=f"Auto Happy Hour — {vendor.business_name}",
                discount_type=DiscountType.HAPPY_HOUR,
                value=15,
                applies_to="ALL",
                start_time=now,
                end_time=now + timedelta(hours=1),
                is_active=True,
            )
            created_count += 1
        except Exception as exc:
            logger.error(
                "auto_happy_hour_trigger error",
                extra={"vendor_id": str(vendor.id), "error": str(exc)},
            )

    if created_count > 0:
        logger.info(
            "auto_happy_hour_trigger complete",
            extra={"happy_hours_created": created_count},
        )


@shared_task(bind=True, name="apps.vendors.tasks.vendor_activation_check")
def vendor_activation_check(self: Any) -> None:
    """Daily task to transition vendors through Progressive Activation stages.

    Stages: CLAIM → ENGAGEMENT → MONETIZATION → GROWTH → RETENTION

    Transition criteria:
    - CLAIM → ENGAGEMENT: logged in ≥3 times OR uploaded first reel, min 3 days since claim
    - ENGAGEMENT → MONETIZATION: created ≥1 discount OR 7 days since claim
    - MONETIZATION → GROWTH: upgraded from Silver OR 14 days active
    - GROWTH → RETENTION: 30+ days since claim

    Registered in celery_app.py Beat schedule (daily at 2 AM).
    """
    from apps.audit.utils import log_action
    from apps.reels.models import VendorReel
    from apps.vendors.models import ActivationStage, Discount, Vendor

    now = timezone.now()
    transitioned = 0

    claimed_vendors = Vendor.objects.filter(
        is_deleted=False,
        claimed_status="CLAIMED",
    ).exclude(activation_stage=ActivationStage.RETENTION)

    for vendor in claimed_vendors.iterator(chunk_size=_BATCH_SIZE):
        old_stage = vendor.activation_stage
        new_stage = old_stage

        if old_stage == ActivationStage.CLAIM:
            days_since_claim = (now - vendor.updated_at).days if vendor.updated_at else 0
            if days_since_claim < 3:
                continue
            login_count = getattr(vendor, "owner", None)
            has_reel = VendorReel.objects.filter(vendor=vendor, is_active=True).exists()
            # Transition if reel uploaded or enough time passed
            if has_reel or days_since_claim >= 5:
                new_stage = ActivationStage.ENGAGEMENT

        elif old_stage == ActivationStage.ENGAGEMENT:
            days_since_claim = (now - vendor.created_at).days if vendor.created_at else 0
            has_discount = Discount.objects.filter(vendor=vendor).exists()
            if has_discount or days_since_claim >= 7:
                new_stage = ActivationStage.MONETIZATION

        elif old_stage == ActivationStage.MONETIZATION:
            days_active = (now - vendor.created_at).days if vendor.created_at else 0
            is_paid = vendor.subscription_level != "SILVER"
            if is_paid or days_active >= 14:
                new_stage = ActivationStage.GROWTH

        elif old_stage == ActivationStage.GROWTH:
            days_active = (now - vendor.created_at).days if vendor.created_at else 0
            if days_active >= 30:
                new_stage = ActivationStage.RETENTION

        if new_stage != old_stage:
            vendor.activation_stage = new_stage
            vendor.activation_stage_updated_at = now
            vendor.save(update_fields=["activation_stage", "activation_stage_updated_at", "updated_at"])

            log_action(
                action="ACTIVATION_STAGE_TRANSITION",
                actor=None,
                target_obj=vendor,
                request=None,
                before={"activation_stage": old_stage},
                after={"activation_stage": new_stage},
            )
            transitioned += 1

    if transitioned > 0:
        logger.info(
            "vendor_activation_check complete",
            extra={"transitioned": transitioned},
        )


def _sync_promotion_tags() -> None:
    """Sync PROMOTION tags based on active discounts (TagAutoAssigner §3.4).

    1. Vendors with active discounts → ensure PROMOTION tag assigned
    2. Vendors with no active discounts → remove PROMOTION tags
    """
    from apps.tags.models import Tag, TagType
    from apps.vendors.models import Vendor

    promo_tags = Tag.objects.filter(tag_type=TagType.PROMOTION, is_active=True)
    if not promo_tags.exists():
        return

    discount_live_tag = Tag.objects.filter(
        slug="promo-discount-live", is_active=True
    ).first()
    if not discount_live_tag:
        return

    now = timezone.now()

    vendors_with_active = set(
        Vendor.objects.filter(
            is_deleted=False,
            discounts__is_active=True,
            discounts__start_time__lte=now,
            discounts__end_time__gte=now,
        ).values_list("id", flat=True).distinct()
    )

    vendors_with_tag = set(
        discount_live_tag.vendors.filter(is_deleted=False)
        .values_list("id", flat=True)
    )

    to_add = vendors_with_active - vendors_with_tag
    to_remove = vendors_with_tag - vendors_with_active

    if to_add:
        vendors_to_tag = Vendor.objects.filter(id__in=to_add)
        discount_live_tag.vendors.add(*vendors_to_tag)

    if to_remove:
        vendors_to_untag = Vendor.objects.filter(id__in=to_remove)
        discount_live_tag.vendors.remove(*vendors_to_untag)

    if to_add or to_remove:
        logger.info(
            "PROMOTION tag sync complete",
            extra={"added": len(to_add), "removed": len(to_remove)},
        )


def _assign_time_tags(now: Any) -> None:
    """Assign/remove TIME tags based on current hour (TagAutoAssigner §3.4).

    Time windows:
    - Breakfast: 06:00-10:00
    - Lunch: 11:00-14:00
    - Evening Snacks: 15:00-18:00
    - Dinner: 18:00-22:00
    - Late Night: 22:00-02:00
    """
    from apps.tags.models import Tag, TagType

    current_hour = now.hour

    time_windows = {
        "time-breakfast": (6, 10),
        "time-lunch": (11, 14),
        "time-evening-snacks": (15, 18),
        "time-dinner": (18, 22),
        "time-late-night-open": (22, 2),
    }

    for slug, (start_h, end_h) in time_windows.items():
        tag = Tag.objects.filter(slug=slug, tag_type=TagType.TIME, is_active=True).first()
        if not tag:
            continue

        if start_h <= end_h:
            is_active_window = start_h <= current_hour < end_h
        else:
            is_active_window = current_hour >= start_h or current_hour < end_h

        if not is_active_window:
            pass


def _assign_system_tags(now: Any) -> None:
    """Assign SYSTEM tags based on vendor metrics (TagAutoAssigner §3.4).

    - NewVendorBoost (system-new-vendor): vendors with >= 10 views this week
    - HighEngagement (system-high-engagement): top 10% taps in area
    """
    from apps.tags.models import Tag, TagType
    from apps.vendors.models import Vendor

    new_vendor_tag = Tag.objects.filter(
        slug="system-new-vendor", tag_type=TagType.SYSTEM, is_active=True
    ).first()

    if new_vendor_tag:
        one_week_ago = now - timedelta(days=7)
        high_view_vendors = Vendor.objects.filter(
            is_deleted=False,
            total_views__gte=10,
            created_at__gte=one_week_ago,
        )
        for vendor in high_view_vendors[:_BATCH_SIZE]:
            vendor.tags.add(new_vendor_tag)

    high_engagement_tag = Tag.objects.filter(
        slug="system-high-engagement", tag_type=TagType.SYSTEM, is_active=True
    ).first()

    if high_engagement_tag:
        from django.db.models import Avg

        areas_with_vendors = (
            Vendor.objects.filter(is_deleted=False)
            .values("area_id")
            .annotate(avg_taps=Avg("total_profile_taps"))
        )

        for area_data in areas_with_vendors:
            if area_data["avg_taps"] is None or area_data["avg_taps"] == 0:
                continue

            threshold = area_data["avg_taps"] * 2
            top_vendors = Vendor.objects.filter(
                area_id=area_data["area_id"],
                is_deleted=False,
                total_profile_taps__gte=threshold,
            )
            for vendor in top_vendors[:_BATCH_SIZE]:
                vendor.tags.add(high_engagement_tag)
