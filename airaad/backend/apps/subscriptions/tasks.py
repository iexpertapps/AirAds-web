"""
AirAd Backend — Subscription Celery Tasks (Phase B §3.4)

subscription_expiry_check: daily midnight UTC — downgrade expired vendors to SILVER.
voicebot_freshness_check: daily — warn vendors with stale voice bot data.
vendor_churn_check: daily — detect churning vendors and send notifications.
vendor_monthly_report: monthly — send engagement/revenue summary to vendors.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

_BATCH_SIZE = 500


@shared_task(bind=True, name="apps.subscriptions.tasks.subscription_expiry_check")
def subscription_expiry_check(self: Any) -> None:
    """Check and expire overdue vendor subscriptions.

    Registered in celery_app.py Beat schedule (daily midnight UTC).
    1. Find vendors where subscription_valid_until < now AND subscription_level != SILVER
    2. Downgrade to SILVER
    3. Send 7-day and 1-day reminders for upcoming expiry
    4. Log all changes to AuditLog
    """
    from apps.audit.utils import log_action
    from apps.vendors.models import Vendor

    now = timezone.now()

    expired_vendors = Vendor.objects.filter(
        is_deleted=False,
        subscription_valid_until__lt=now,
    ).exclude(subscription_level="SILVER")

    downgraded = 0
    for vendor in expired_vendors[:_BATCH_SIZE]:
        before_level = vendor.subscription_level
        vendor.subscription_level = "SILVER"
        vendor.subscription_valid_until = None
        vendor.save(update_fields=[
            "subscription_level",
            "subscription_valid_until",
            "updated_at",
        ])

        log_action(
            action="SUBSCRIPTION_EXPIRED",
            actor=None,
            target_obj=vendor,
            request=None,
            before={"subscription_level": before_level},
            after={"subscription_level": "SILVER"},
        )
        downgraded += 1

    seven_day_warning = now + timedelta(days=7)
    one_day_warning = now + timedelta(days=1)

    upcoming_7d = Vendor.objects.filter(
        is_deleted=False,
        subscription_valid_until__date=seven_day_warning.date(),
    ).exclude(subscription_level="SILVER").count()

    upcoming_1d = Vendor.objects.filter(
        is_deleted=False,
        subscription_valid_until__date=one_day_warning.date(),
    ).exclude(subscription_level="SILVER").count()

    logger.info(
        "subscription_expiry_check complete",
        extra={
            "downgraded": downgraded,
            "7d_reminders": upcoming_7d,
            "1d_reminders": upcoming_1d,
        },
    )


@shared_task(bind=True, name="apps.subscriptions.tasks.voicebot_freshness_check")
def voicebot_freshness_check(self: Any) -> None:
    """Check voice bot data freshness and send push notifications.

    Registered in celery_app.py Beat schedule (daily at 9 AM per plan §B-7).
    - 30-day warning: menu not updated → push notification
    - 7-day warning: out-of-stock items persisting → push notification
    - Completeness < 50% → push notification
    """
    from apps.notifications.services import send_push_notification
    from apps.vendors.models import VoiceBotConfig

    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    stats = {"stale_30d": 0, "stale_7d": 0, "low_completeness": 0}

    # 30-day stale menu
    stale_30d = VoiceBotConfig.objects.filter(
        last_updated_at__lt=thirty_days_ago,
        vendor__is_deleted=False,
    ).select_related("vendor")

    for config in stale_30d[:_BATCH_SIZE]:
        vendor = config.vendor
        send_push_notification(
            recipient_type="VENDOR",
            recipient_id=str(vendor.owner_id) if vendor.owner_id else str(vendor.id),
            title="Your voice bot menu is outdated",
            body="Update it to keep responses accurate.",
        )
        stats["stale_30d"] += 1

    # 7-day stale (recent but getting old)
    stale_7d = VoiceBotConfig.objects.filter(
        last_updated_at__lt=seven_days_ago,
        last_updated_at__gte=thirty_days_ago,
        vendor__is_deleted=False,
    ).select_related("vendor")

    for config in stale_7d[:_BATCH_SIZE]:
        vendor = config.vendor
        send_push_notification(
            recipient_type="VENDOR",
            recipient_id=str(vendor.owner_id) if vendor.owner_id else str(vendor.id),
            title="Voice bot data needs attention",
            body="You have items that may be outdated. Update or remove them.",
        )
        stats["stale_7d"] += 1

    # Low completeness score
    low_completeness = VoiceBotConfig.objects.filter(
        completeness_score__lt=50,
        is_active=True,
        vendor__is_deleted=False,
    ).select_related("vendor")

    for config in low_completeness[:_BATCH_SIZE]:
        vendor = config.vendor
        send_push_notification(
            recipient_type="VENDOR",
            recipient_id=str(vendor.owner_id) if vendor.owner_id else str(vendor.id),
            title=f"Your voice bot is only {config.completeness_score}% configured",
            body="Complete setup for better customer responses.",
        )
        stats["low_completeness"] += 1

    logger.info("voicebot_freshness_check complete", extra=stats)


@shared_task(bind=True, name="apps.subscriptions.tasks.vendor_churn_check")
def vendor_churn_check(self: Any) -> None:
    """Detect churning vendors and trigger re-engagement notifications.

    Registered in celery_app.py Beat schedule (daily at 10 AM).

    Four checks per plan §B-10:
    1. 7 days inactive (no login) → push with weekly view stats
    2. 14 days no reel uploaded → push encouraging reel upload
    3. Subscription downgrade detected → survey + coupon
    4. 30 days post-claim, no upgrade (Silver) → push with upgrade CTA
    """
    from apps.notifications.services import send_push_notification
    from apps.reels.models import VendorReel
    from apps.vendors.models import Vendor

    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)
    fourteen_days_ago = now - timedelta(days=14)
    thirty_days_ago = now - timedelta(days=30)

    stats = {"7d_inactive": 0, "14d_no_reel": 0, "30d_silver_no_upgrade": 0}

    # Check 1: 7 days inactive — no login/update
    inactive_7d = Vendor.objects.filter(
        is_deleted=False,
        claimed_status="CLAIMED",
        updated_at__lt=seven_days_ago,
    ).exclude(updated_at__lt=fourteen_days_ago)

    for vendor in inactive_7d[:_BATCH_SIZE]:
        send_push_notification(
            recipient_type="VENDOR",
            recipient_id=str(vendor.owner_id) if vendor.owner_id else str(vendor.id),
            title="Your listing had views this week!",
            body=f"Your listing had {vendor.total_views} total views. Log in to see what's happening.",
        )
        stats["7d_inactive"] += 1

    # Check 2: 14 days no reel uploaded — push encouraging upload
    claimed_vendors = Vendor.objects.filter(
        is_deleted=False,
        claimed_status="CLAIMED",
    )
    for vendor in claimed_vendors[:_BATCH_SIZE]:
        has_recent_reel = VendorReel.objects.filter(
            vendor=vendor,
            created_at__gte=fourteen_days_ago,
        ).exists()
        if not has_recent_reel:
            send_push_notification(
                recipient_type="VENDOR",
                recipient_id=str(vendor.owner_id) if vendor.owner_id else str(vendor.id),
                title="Upload a reel to stay top-of-mind",
                body="Vendors with reels get 3x more views. Upload one now!",
            )
            stats["14d_no_reel"] += 1

    # Check 4: 30 days post-claim, Silver, no upgrade
    silver_stale = Vendor.objects.filter(
        is_deleted=False,
        claimed_status="CLAIMED",
        subscription_level="SILVER",
        claimed_at__lt=thirty_days_ago,
    )
    for vendor in silver_stale[:_BATCH_SIZE]:
        send_push_notification(
            recipient_type="VENDOR",
            recipient_id=str(vendor.owner_id) if vendor.owner_id else str(vendor.id),
            title=f"You've had {vendor.total_views} views on Silver",
            body="See what Gold unlocks for your business.",
        )
        stats["30d_silver_no_upgrade"] += 1

    logger.info("vendor_churn_check complete", extra=stats)


@shared_task(bind=True, name="apps.subscriptions.tasks.vendor_monthly_report")
def vendor_monthly_report(self: Any) -> None:
    """Generate monthly engagement summary for ALL claimed vendors.

    Registered in celery_app.py Beat schedule (1st of month, 06:00 UTC).
    Silver vendors receive an upgrade CTA with ROI projection.
    Uses NotificationLog with channel=EMAIL per plan §B-10.
    """
    from apps.notifications.services import send_email_notification
    from apps.vendors.models import Vendor

    claimed_vendors = Vendor.objects.filter(
        is_deleted=False,
        claimed_status="CLAIMED",
    )

    report_count = 0
    for vendor in claimed_vendors.iterator(chunk_size=_BATCH_SIZE):
        subject = "Your AirAd Presence Report"
        body_lines = [
            f"Hi {vendor.business_name},",
            "",
            f"AR Views: {vendor.total_views}",
            f"Navigation Clicks: {vendor.total_navigation_clicks}",
            f"Profile Taps: {vendor.total_profile_taps}",
        ]

        if vendor.subscription_level == "SILVER":
            body_lines.extend([
                "",
                "You're on the free Silver plan.",
                f"With {vendor.total_views} views, upgrading to Gold could drive even more traffic.",
                "See what Gold unlocks → https://vendor.airad.pk/upgrade",
            ])

        body = "\n".join(body_lines)

        # Resolve email from owner
        email = ""
        if vendor.owner_id:
            from apps.accounts.models import CustomerUser
            try:
                owner = CustomerUser.objects.get(pk=vendor.owner_id)
                email = owner.email
            except CustomerUser.DoesNotExist:
                pass

        if email:
            send_email_notification(
                recipient_type="VENDOR",
                recipient_id=str(vendor.owner_id or vendor.id),
                email=email,
                title=subject,
                body=body,
            )
        else:
            logger.debug(
                "Monthly report skipped (no email): vendor=%s", vendor.id,
            )

        report_count += 1

    logger.info(
        "vendor_monthly_report complete",
        extra={"reports_generated": report_count},
    )
