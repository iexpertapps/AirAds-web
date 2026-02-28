"""
AirAd Backend — seed_vendor_portal Management Command

Creates a fully claimed vendor with:
- CustomerUser owner (phone: +923001234567, OTP: 005261)
- Vendor claimed at GOLD tier
- 4 sample discounts (active, expired, happy hour, BOGO)
- VoiceBotConfig with realistic data
- 3 sample reels
- Analytics view/tap events for the last 14 days

Prerequisite: run seed_data first (geo hierarchy + vendors + tags).
Idempotent — safe to run multiple times.

Usage:
    python manage.py seed_vendor_portal
"""

import hashlib
import logging
import random
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

logger = logging.getLogger(__name__)

DEMO_PHONE = "+923001234567"
DEMO_VENDOR_SLUG = "zamzama-grill-house"


def _hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.strip().encode("utf-8")).hexdigest()


class Command(BaseCommand):
    help = (
        "Seed a fully claimed vendor for the Vendor Portal demo. "
        "Run seed_data first."
    )

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("seed_vendor_portal starting..."))

        try:
            with transaction.atomic():
                owner = self._ensure_customer_user()
                vendor = self._claim_vendor(owner)
                self._set_subscription(vendor)
                self._seed_discounts(vendor)
                self._seed_voicebot(vendor)
                self._seed_reels(vendor)
                self._seed_analytics(vendor)
        except Exception as exc:
            raise CommandError(f"seed_vendor_portal failed: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(
            f"\nseed_vendor_portal complete.\n"
            f"  Login phone: {DEMO_PHONE}\n"
            f"  OTP code:    005261 (manual mode)\n"
            f"  Vendor:      {vendor.business_name} ({vendor.subscription_level})"
        ))

    # -----------------------------------------------------------------
    # 1. CustomerUser
    # -----------------------------------------------------------------
    def _ensure_customer_user(self) -> Any:
        from apps.accounts.models import CustomerUser, UserType
        from core.encryption import encrypt

        phone_hash = _hash_phone(DEMO_PHONE)
        user, created = CustomerUser.objects.get_or_create(
            phone_hash=phone_hash,
            defaults={
                "phone_encrypted": encrypt(DEMO_PHONE),
                "full_name": "Demo Vendor Owner",
                "email": "vendor@airaad.com",
                "user_type": UserType.VENDOR,
                "is_active": True,
                "is_phone_verified": True,
            },
        )
        if created:
            self.stdout.write(f"  Created CustomerUser: {user.full_name}")
        else:
            if user.user_type != UserType.VENDOR:
                user.user_type = UserType.VENDOR
                user.save(update_fields=["user_type"])
            self.stdout.write(f"  CustomerUser exists: {user.full_name}")
        return user

    # -----------------------------------------------------------------
    # 2. Claim vendor
    # -----------------------------------------------------------------
    def _claim_vendor(self, owner: Any) -> Any:
        from apps.vendors.models import ClaimedStatus, Vendor

        try:
            vendor = Vendor.objects.get(slug=DEMO_VENDOR_SLUG)
        except Vendor.DoesNotExist:
            raise CommandError(
                f"Vendor '{DEMO_VENDOR_SLUG}' not found. Run seed_data first."
            )

        if vendor.claimed_status != ClaimedStatus.CLAIMED:
            vendor.claimed_status = ClaimedStatus.CLAIMED
            vendor.owner = owner
            vendor.claimed_at = timezone.now()
            vendor.is_verified = True
            vendor.activation_stage = "ENGAGEMENT"
            vendor.save(update_fields=[
                "claimed_status", "owner", "claimed_at",
                "is_verified", "activation_stage", "updated_at",
            ])
            self.stdout.write(f"  Claimed vendor: {vendor.business_name}")
        else:
            self.stdout.write(f"  Vendor already claimed: {vendor.business_name}")

        return vendor

    # -----------------------------------------------------------------
    # 3. Set subscription to GOLD
    # -----------------------------------------------------------------
    def _set_subscription(self, vendor: Any) -> None:
        from apps.subscriptions.models import SubscriptionLevel

        if vendor.subscription_level != SubscriptionLevel.GOLD:
            vendor.subscription_level = SubscriptionLevel.GOLD
            vendor.subscription_valid_until = timezone.now() + timedelta(days=30)
            vendor.save(update_fields=[
                "subscription_level", "subscription_valid_until", "updated_at",
            ])
            self.stdout.write("  Set subscription: GOLD (30 days)")
        else:
            self.stdout.write("  Subscription already GOLD")

    # -----------------------------------------------------------------
    # 4. Sample discounts
    # -----------------------------------------------------------------
    def _seed_discounts(self, vendor: Any) -> None:
        from apps.vendors.models import Discount, DiscountType

        now = timezone.now()
        discounts = [
            {
                "title": "Weekend 20% Off All Grills",
                "discount_type": DiscountType.PERCENTAGE,
                "value": Decimal("20.00"),
                "applies_to": "ALL",
                "item_description": "Valid on all grill items during weekends",
                "start_time": now - timedelta(hours=2),
                "end_time": now + timedelta(days=2),
                "is_active": True,
                "min_order_value": Decimal("500.00"),
            },
            {
                "title": "Lunch Special — PKR 200 Off",
                "discount_type": DiscountType.FIXED_AMOUNT,
                "value": Decimal("200.00"),
                "applies_to": "LUNCH_MENU",
                "item_description": "Flat discount on lunch combos",
                "start_time": now - timedelta(days=7),
                "end_time": now - timedelta(days=1),
                "is_active": False,
                "min_order_value": Decimal("300.00"),
            },
            {
                "title": "Evening Happy Hour",
                "discount_type": DiscountType.HAPPY_HOUR,
                "value": Decimal("30.00"),
                "applies_to": "BEVERAGES",
                "item_description": "30% off all beverages 5-7 PM",
                "start_time": now.replace(hour=17, minute=0, second=0),
                "end_time": now.replace(hour=19, minute=0, second=0) + timedelta(days=1),
                "is_active": True,
                "is_recurring": True,
                "recurrence_days": [1, 2, 3, 4, 5],
                "min_order_value": Decimal("0.00"),
            },
            {
                "title": "Buy 1 Get 1 Free — Seekh Kebab",
                "discount_type": DiscountType.BUY_ONE_GET_ONE,
                "value": Decimal("0.00"),
                "applies_to": "ITEM_SPECIFIC",
                "item_description": "Buy one seekh kebab plate, get another free",
                "start_time": now,
                "end_time": now + timedelta(days=5),
                "is_active": True,
                "min_order_value": Decimal("0.00"),
                "ar_badge_text": "BOGO!",
            },
        ]

        created_count = 0
        for d in discounts:
            obj, created = Discount.objects.get_or_create(
                vendor=vendor,
                title=d["title"],
                defaults=d,
            )
            if created:
                created_count += 1

        self.stdout.write(f"  Discounts: {created_count} created, {len(discounts) - created_count} existed")

    # -----------------------------------------------------------------
    # 5. VoiceBotConfig
    # -----------------------------------------------------------------
    def _seed_voicebot(self, vendor: Any) -> None:
        from apps.vendors.models import VoiceBotConfig

        config, created = VoiceBotConfig.objects.get_or_create(
            vendor=vendor,
            defaults={
                "menu_items": [
                    "Seekh Kebab Platter — PKR 850",
                    "Chicken Tikka — PKR 750",
                    "Beef Steak — PKR 1200",
                    "Mixed Grill Family Pack — PKR 2500",
                    "Chapli Kebab — PKR 650",
                    "Grilled Fish — PKR 900",
                ],
                "opening_hours_summary": (
                    "Mon-Thu 12 PM to 11 PM, "
                    "Fri-Sat 12 PM to midnight, "
                    "Sun closed"
                ),
                "delivery_info": {
                    "delivers": True,
                    "min_order": 500,
                    "delivery_fee": 100,
                    "area": "DHA Phase 5-8",
                },
                "discount_summary": "Weekend 20% off grills, BOGO Seekh Kebab, Happy Hour beverages 5-7 PM",
                "custom_qa_pairs": [
                    {"q": "Do you have parking?", "a": "Yes, free valet parking available."},
                    {"q": "Is there outdoor seating?", "a": "Yes, rooftop and garden seating."},
                    {"q": "Do you cater events?", "a": "Yes, we offer catering for 20+ guests."},
                ],
                "intro_message": (
                    "Welcome to Zamzama Grill House! We serve premium BBQ and grill items "
                    "in the heart of DHA Phase 6. Ask me about our menu, hours, or current deals."
                ),
                "pickup_available": True,
                "is_active": True,
                "completeness_score": 100,
            },
        )
        action = "Created" if created else "Exists"
        self.stdout.write(f"  VoiceBotConfig: {action}")

    # -----------------------------------------------------------------
    # 6. Sample reels
    # -----------------------------------------------------------------
    def _seed_reels(self, vendor: Any) -> None:
        from apps.reels.models import ModerationStatus, ReelStatus, VendorReel

        reels_data = [
            {
                "title": "Our Signature Seekh Kebab",
                "s3_key": "reels/zamzama-seekh-kebab.mp4",
                "thumbnail_s3_key": "thumbnails/zamzama-seekh-kebab.jpg",
                "duration_seconds": 28,
                "status": ReelStatus.ACTIVE,
                "moderation_status": ModerationStatus.APPROVED,
                "view_count": 342,
                "completion_count": 198,
                "display_order": 0,
            },
            {
                "title": "Friday Night Vibes at the Grill",
                "s3_key": "reels/zamzama-friday-night.mp4",
                "thumbnail_s3_key": "thumbnails/zamzama-friday-night.jpg",
                "duration_seconds": 45,
                "status": ReelStatus.ACTIVE,
                "moderation_status": ModerationStatus.APPROVED,
                "view_count": 187,
                "completion_count": 89,
                "display_order": 1,
            },
            {
                "title": "Behind the Scenes — Our Kitchen",
                "s3_key": "reels/zamzama-kitchen-bts.mp4",
                "thumbnail_s3_key": "thumbnails/zamzama-kitchen-bts.jpg",
                "duration_seconds": 60,
                "status": ReelStatus.PROCESSING,
                "moderation_status": ModerationStatus.PENDING,
                "view_count": 0,
                "completion_count": 0,
                "display_order": 2,
            },
        ]

        created_count = 0
        for r in reels_data:
            obj, created = VendorReel.objects.get_or_create(
                vendor=vendor,
                title=r["title"],
                defaults=r,
            )
            if created:
                created_count += 1

        self.stdout.write(f"  Reels: {created_count} created, {len(reels_data) - created_count} existed")

    # -----------------------------------------------------------------
    # 7. Analytics events (last 14 days)
    # -----------------------------------------------------------------
    def _seed_analytics(self, vendor: Any) -> None:
        from apps.analytics.models import AnalyticsEvent

        now = timezone.now()
        existing = AnalyticsEvent.objects.filter(vendor=vendor).count()
        if existing >= 50:
            self.stdout.write(f"  Analytics: {existing} events already exist, skipping")
            return

        total_created = 0
        for days_ago in range(14):
            day = now - timedelta(days=days_ago)
            views_today = random.randint(8, 45)
            taps_today = random.randint(2, int(views_today * 0.6))

            day_events = []
            for _ in range(views_today):
                day_events.append(AnalyticsEvent(
                    vendor=vendor,
                    event_type="VIEW",
                ))
            for _ in range(taps_today):
                day_events.append(AnalyticsEvent(
                    vendor=vendor,
                    event_type="PROFILE_TAP",
                ))

            created = AnalyticsEvent.objects.bulk_create(day_events)
            if created:
                target_date = day.replace(hour=12, minute=0, second=0, microsecond=0)
                AnalyticsEvent.objects.filter(pk__in=[e.pk for e in created]).update(
                    created_at=target_date
                )
            total_created += len(created)

        vendor.total_views = AnalyticsEvent.objects.filter(
            vendor=vendor, event_type="VIEW"
        ).count()
        vendor.total_profile_taps = AnalyticsEvent.objects.filter(
            vendor=vendor, event_type="PROFILE_TAP"
        ).count()
        vendor.save(update_fields=["total_views", "total_profile_taps", "updated_at"])

        self.stdout.write(f"  Analytics: {total_created} events created (14-day window)")
