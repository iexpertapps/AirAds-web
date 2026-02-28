"""
AirAd Backend — Seed Subscription Packages (§B-4)

Creates or updates the 4 subscription tiers: SILVER, GOLD, DIAMOND, PLATINUM.
Run: python manage.py seed_subscriptions
Idempotent — safe to run multiple times.
"""

from django.core.management.base import BaseCommand

from apps.subscriptions.models import SubscriptionPackage


TIERS = [
    {
        "level": "SILVER",
        "name": "Silver — Visibility",
        "price_monthly": 0,
        "price_monthly_usd": None,
        "stripe_price_id": "",
        "max_videos": 1,
        "daily_happy_hours_allowed": 0,
        "max_delivery_configs": 0,
        "has_voice_bot": False,
        "voice_bot_type": "NONE",
        "has_predictive_reports": False,
        "sponsored_placement_level": "NONE",
        "campaign_scheduling_level": "NONE",
        "voice_search_priority": "NONE",
        "visibility_boost_weight": 1.0,
        "badge_type": "CLAIMED",
        "support_level": "COMMUNITY",
        "analytics_level": "BASIC",
        "display_order": 1,
    },
    {
        "level": "GOLD",
        "name": "Gold — Control",
        "price_monthly": 3000,
        "price_monthly_usd": 10.00,
        "stripe_price_id": "",
        "max_videos": 3,
        "daily_happy_hours_allowed": 1,
        "max_delivery_configs": 1,
        "has_voice_bot": True,
        "voice_bot_type": "BASIC",
        "has_predictive_reports": False,
        "sponsored_placement_level": "LIMITED_TIME",
        "campaign_scheduling_level": "BASIC",
        "voice_search_priority": "LOW",
        "visibility_boost_weight": 1.2,
        "badge_type": "VERIFIED",
        "support_level": "EMAIL_48H",
        "analytics_level": "STANDARD",
        "display_order": 2,
    },
    {
        "level": "DIAMOND",
        "name": "Diamond — Automation",
        "price_monthly": 7000,
        "price_monthly_usd": 25.00,
        "stripe_price_id": "",
        "max_videos": 6,
        "daily_happy_hours_allowed": 3,
        "max_delivery_configs": 3,
        "has_voice_bot": True,
        "voice_bot_type": "DYNAMIC",
        "has_predictive_reports": False,
        "sponsored_placement_level": "AREA_BOOST",
        "campaign_scheduling_level": "ADVANCED",
        "voice_search_priority": "MEDIUM",
        "visibility_boost_weight": 1.5,
        "badge_type": "PREMIUM",
        "support_level": "PRIORITY_24H",
        "analytics_level": "ADVANCED",
        "display_order": 3,
    },
    {
        "level": "PLATINUM",
        "name": "Platinum — Dominance",
        "price_monthly": 15000,
        "price_monthly_usd": 50.00,
        "stripe_price_id": "",
        "max_videos": 999,
        "daily_happy_hours_allowed": 99,
        "max_delivery_configs": -1,
        "has_voice_bot": True,
        "voice_bot_type": "ADVANCED",
        "has_predictive_reports": True,
        "sponsored_placement_level": "AREA_EXCLUSIVE",
        "campaign_scheduling_level": "SMART_AUTOMATION",
        "voice_search_priority": "HIGHEST",
        "visibility_boost_weight": 2.0,
        "badge_type": "ELITE",
        "support_level": "DEDICATED",
        "analytics_level": "PREDICTIVE",
        "display_order": 4,
    },
]


class Command(BaseCommand):
    help = "Seed the 4 subscription tiers (SILVER/GOLD/DIAMOND/PLATINUM). Idempotent."

    def handle(self, *args, **options):
        for tier in TIERS:
            obj, created = SubscriptionPackage.objects.update_or_create(
                level=tier["level"],
                defaults=tier,
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {obj.name} (level={obj.level})")

        self.stdout.write(self.style.SUCCESS("Subscription packages seeded successfully."))
