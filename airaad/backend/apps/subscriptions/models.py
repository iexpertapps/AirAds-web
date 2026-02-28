"""
AirAd Backend — Subscription Models (Phase B §3.1, §3.5)

SubscriptionPackage defines the 4 tier levels (SILVER/GOLD/DIAMOND/PLATINUM)
with feature flags, limits, and pricing. Seeded via management command — not migration.

visibility_boost_weight is used by RankingService (§3.3) in the discovery scoring formula.
vendor_has_feature() in core/utils.py is the ONLY gate mechanism (§3.5).
"""

import uuid

from django.db import models


class SubscriptionLevel(models.TextChoices):
    """Subscription tier levels — Value Ladder.

    Visibility (Silver) → Control (Gold) → Automation (Diamond) → Dominance (Platinum).
    """

    SILVER = "SILVER", "Silver"
    GOLD = "GOLD", "Gold"
    DIAMOND = "DIAMOND", "Diamond"
    PLATINUM = "PLATINUM", "Platinum"


class SubscriptionPackage(models.Model):
    """A subscription tier defining features, limits, and pricing.

    Seeded via management command — never created via API or migration.
    vendor_has_feature() in core/utils.py reads these fields to gate features.

    Attributes:
        id: UUID primary key.
        level: SubscriptionLevel (unique — one row per tier).
        name: Human-readable tier name.
        price_monthly: Monthly price in PKR (Decimal for precision).
        max_videos: Maximum reel/video uploads allowed.
        daily_happy_hours_allowed: Max happy hours per day (0 = none).
        has_voice_bot: Whether voice bot feature is available.
        has_predictive_reports: Whether predictive recommendation reports are available.
        sponsored_placement_level: Sponsored placement capability level.
        campaign_scheduling_level: Campaign scheduling capability level.
        voice_search_priority: Priority level in voice search results.
        visibility_boost_weight: Multiplier for ranking formula (§3.3).
            SILVER=1.0, GOLD=1.2, DIAMOND=1.5, PLATINUM=2.0.
        is_active: Whether this tier is currently offered.
        created_at: Auto-set on creation.
        updated_at: Auto-updated on every save.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    level = models.CharField(
        max_length=10,
        choices=SubscriptionLevel.choices,
        unique=True,
        db_index=True,
    )
    name = models.CharField(max_length=50)
    price_monthly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monthly price in PKR.",
    )

    # Feature limits
    max_videos = models.PositiveIntegerField(
        default=1,
        help_text="Maximum reel/video uploads. Silver=1, Gold=3, Diamond=6, Platinum=unlimited(999).",
    )
    daily_happy_hours_allowed = models.PositiveIntegerField(
        default=0,
        help_text="Max happy hours per day. Silver=0, Gold=1, Diamond=3, Platinum=unlimited(99).",
    )

    # Feature flags
    has_voice_bot = models.BooleanField(
        default=False,
        help_text="Silver=False, Gold=True(basic), Diamond=True(dynamic), Platinum=True(advanced).",
    )
    has_predictive_reports = models.BooleanField(
        default=False,
        help_text="Platinum only.",
    )

    # Granular capability levels
    sponsored_placement_level = models.CharField(
        max_length=20,
        choices=[
            ("NONE", "None"),
            ("LIMITED_TIME", "Limited Time"),
            ("AREA_BOOST", "Area Boost"),
            ("AREA_EXCLUSIVE", "Area Exclusive"),
        ],
        default="NONE",
        help_text="Silver=NONE, Gold=LIMITED_TIME, Diamond=AREA_BOOST, Platinum=AREA_EXCLUSIVE.",
    )
    campaign_scheduling_level = models.CharField(
        max_length=20,
        choices=[
            ("NONE", "None"),
            ("BASIC", "Basic"),
            ("ADVANCED", "Advanced"),
            ("SMART_AUTOMATION", "Smart Automation"),
        ],
        default="NONE",
        help_text="Silver=NONE, Gold=BASIC, Diamond=ADVANCED, Platinum=SMART_AUTOMATION.",
    )
    voice_search_priority = models.CharField(
        max_length=10,
        choices=[
            ("NONE", "None"),
            ("LOW", "Low"),
            ("MEDIUM", "Medium"),
            ("HIGHEST", "Highest"),
        ],
        default="NONE",
        help_text="Silver=NONE, Gold=LOW, Diamond=MEDIUM, Platinum=HIGHEST.",
    )

    # Ranking formula weight (§3.3)
    visibility_boost_weight = models.FloatField(
        default=1.0,
        help_text="Ranking multiplier. Silver=1.0, Gold=1.2, Diamond=1.5, Platinum=2.0.",
    )

    # Pricing & Stripe linkage
    price_monthly_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Monthly price in USD (for Stripe checkout). Null for free tier.",
    )
    stripe_price_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Stripe Price ID for this tier (e.g. price_xxx). Blank for free tier.",
    )

    # Delivery config limit
    max_delivery_configs = models.IntegerField(
        default=0,
        help_text="Max delivery configurations. 0=none, -1=unlimited. Silver=0, Gold=1, Diamond=3, Platinum=-1.",
    )

    # Granular capability levels
    voice_bot_type = models.CharField(
        max_length=10,
        choices=[
            ("NONE", "None"),
            ("BASIC", "Basic"),
            ("DYNAMIC", "Dynamic"),
            ("ADVANCED", "Advanced"),
        ],
        default="NONE",
        help_text="Silver=NONE, Gold=BASIC, Diamond=DYNAMIC, Platinum=ADVANCED.",
    )
    badge_type = models.CharField(
        max_length=10,
        choices=[
            ("CLAIMED", "Claimed"),
            ("VERIFIED", "Verified"),
            ("PREMIUM", "Premium"),
            ("ELITE", "Elite"),
        ],
        default="CLAIMED",
        help_text="Silver=CLAIMED, Gold=VERIFIED, Diamond=PREMIUM, Platinum=ELITE.",
    )
    support_level = models.CharField(
        max_length=15,
        choices=[
            ("COMMUNITY", "Community"),
            ("EMAIL_48H", "Email 48h"),
            ("PRIORITY_24H", "Priority 24h"),
            ("DEDICATED", "Dedicated"),
        ],
        default="COMMUNITY",
        help_text="Silver=COMMUNITY, Gold=EMAIL_48H, Diamond=PRIORITY_24H, Platinum=DEDICATED.",
    )
    analytics_level = models.CharField(
        max_length=12,
        choices=[
            ("BASIC", "Basic"),
            ("STANDARD", "Standard"),
            ("ADVANCED", "Advanced"),
            ("PREDICTIVE", "Predictive"),
        ],
        default="BASIC",
        help_text="Silver=BASIC, Gold=STANDARD, Diamond=ADVANCED, Platinum=PREDICTIVE.",
    )

    display_order = models.PositiveIntegerField(
        default=0,
        help_text="UI display order. Lower number = shown first.",
    )

    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Subscription Package"
        verbose_name_plural = "Subscription Packages"
        ordering = ["price_monthly"]

    def __str__(self) -> str:
        return f"{self.name} ({self.level}) — PKR {self.price_monthly}/mo"
