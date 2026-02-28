"""
AirAd Backend — Vendor Model (R2, R6)

phone_number_encrypted: BinaryField — AES-256-GCM encrypted at rest (R2).
is_deleted: Soft delete only — delete() overridden, never super().delete() (R6).
Default manager filters is_deleted=False automatically.
gps_point: PointField — GiST index via migrations.RunSQL (NOT models.Index).
business_hours: JSONField — validated via BusinessHoursSchema in vendors/services.py.
qc_reviewed_by: FK to AdminUser — NOT a raw UUID field.
"""

import uuid

from django.contrib.gis.db import models as gis_models
from django.db import models


class QCStatus(models.TextChoices):
    """Quality control review status for a vendor record."""

    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    NEEDS_REVIEW = "NEEDS_REVIEW", "Needs Review"
    FLAGGED = "FLAGGED", "Flagged"


class DataSource(models.TextChoices):
    """Origin of the vendor record."""

    CSV_IMPORT = "CSV_IMPORT", "CSV Import"
    GOOGLE_PLACES = "GOOGLE_PLACES", "Google Places"
    MANUAL_ENTRY = "MANUAL_ENTRY", "Manual Entry"
    FIELD_AGENT = "FIELD_AGENT", "Field Agent"


class ClaimedStatus(models.TextChoices):
    """Vendor claim status — tracks the lifecycle of ownership verification."""

    UNCLAIMED = "UNCLAIMED", "Unclaimed"
    CLAIM_PENDING = "CLAIM_PENDING", "Claim Pending"
    CLAIMED = "CLAIMED", "Claimed"
    CLAIM_REJECTED = "CLAIM_REJECTED", "Claim Rejected"


class ActivationStage(models.TextChoices):
    """Progressive Activation Strategy — 5 stages.

    CLAIM → ENGAGEMENT → MONETIZATION → GROWTH → RETENTION.
    """

    CLAIM = "CLAIM", "Claim"
    ENGAGEMENT = "ENGAGEMENT", "Engagement"
    MONETIZATION = "MONETIZATION", "Monetization"
    GROWTH = "GROWTH", "Growth"
    RETENTION = "RETENTION", "Retention"


class DiscountType(models.TextChoices):
    """Types of discounts offered by vendors."""

    PERCENTAGE = "PERCENTAGE", "Percentage Off"
    FIXED_AMOUNT = "FIXED_AMOUNT", "Fixed Amount Off"
    BUY_ONE_GET_ONE = "BUY_ONE_GET_ONE", "Buy One Get One"
    HAPPY_HOUR = "HAPPY_HOUR", "Happy Hour"
    FLASH_DEAL = "FLASH_DEAL", "Flash Deal"
    ITEM_SPECIFIC = "ITEM_SPECIFIC", "Item Specific"


class ActiveVendorManager(models.Manager):
    """Default manager — automatically filters out soft-deleted vendors.

    Any queryset from Vendor.objects will exclude is_deleted=True records.
    Use Vendor.all_objects for unfiltered access (admin/QA use only).
    """

    def get_queryset(self) -> models.QuerySet:
        """Return only non-deleted vendors.

        Returns:
            QuerySet filtered to is_deleted=False.
        """
        return super().get_queryset().filter(is_deleted=False)


class Vendor(models.Model):
    """A vendor (business) in the AirAd platform.

    Core data collection model for Phase A. Extended with owner, subscription,
    and media fields in Phase B via a new migration.

    Phone numbers are stored AES-256-GCM encrypted in phone_number_encrypted
    (BinaryField). Plaintext is never stored. Encrypt/decrypt happens in
    vendors/services.py — never in serializers or views.

    Soft delete: delete() sets is_deleted=True and calls save(). Records are
    never hard-deleted. Default manager (objects) filters is_deleted=False.
    Use all_objects for unfiltered access.

    gps_point uses a PostGIS PointField. GiST index is added via
    migrations.RunSQL — not models.Index.

    business_hours is a JSONField validated against BusinessHoursSchema
    on every write in vendors/services.py.

    Attributes:
        id: UUID primary key.
        business_name: Trading name of the business.
        slug: URL-safe identifier — unique.
        description: Optional long-form description.
        gps_point: PostGIS PointField (SRID=4326). GiST index via RunSQL.
        address_text: Human-readable address string.
        city: FK to geo.City.
        area: FK to geo.Area.
        landmark: FK to geo.Landmark (nullable).
        phone_number_encrypted: AES-256-GCM encrypted phone (BinaryField, R2).
        business_hours: JSONField validated by BusinessHoursSchema.
        qc_status: QCStatus TextChoices.
        qc_reviewed_by: FK to AdminUser (nullable) — NOT a raw UUID.
        qc_reviewed_at: Datetime of last QC review.
        qc_notes: Reviewer notes.
        data_source: DataSource TextChoices.
        tags: M2M to tags.Tag.
        is_deleted: Soft delete flag (R6). Default manager filters this out.
        created_at: Auto-set on creation.
        updated_at: Auto-updated on every save.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business_name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=280, unique=True, db_index=True)
    description = models.TextField(blank=True)

    # GPS — PostGIS PointField. GiST index via migrations.RunSQL (NOT models.Index).
    gps_point = gis_models.PointField(
        srid=4326,
        help_text="GPS location. GiST index added via RunSQL migration.",
    )
    gps_baseline = gis_models.PointField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Original GPS location from data source for change detection.",
    )
    address_text = models.CharField(max_length=500, blank=True)

    # Geo hierarchy
    city = models.ForeignKey(
        "geo.City",
        on_delete=models.PROTECT,
        related_name="vendors",
    )
    area = models.ForeignKey(
        "geo.Area",
        on_delete=models.PROTECT,
        related_name="vendors",
    )
    landmark = models.ForeignKey(
        "geo.Landmark",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vendors",
    )

    # Phone — AES-256-GCM encrypted BinaryField (R2). NEVER plaintext.
    phone_number_encrypted = models.BinaryField(
        blank=True,
        help_text="AES-256-GCM encrypted phone number. Encrypt/decrypt in services.py only.",
    )

    # Business hours — validated via BusinessHoursSchema on every write in services.py
    business_hours = models.JSONField(
        default=dict,  # callable — NEVER default={}
        blank=True,
        help_text="7-day hours dict. Validated by BusinessHoursSchema in services.py.",
    )

    # QC workflow
    qc_status = models.CharField(
        max_length=20,
        choices=QCStatus.choices,
        default=QCStatus.PENDING,
        db_index=True,
    )
    qc_reviewed_by = models.ForeignKey(
        "accounts.AdminUser",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="qc_reviewed_vendors",
        help_text="FK to AdminUser — NOT a raw UUID field.",
    )
    qc_reviewed_at = models.DateTimeField(null=True, blank=True)
    qc_notes = models.TextField(blank=True)

    # Data provenance
    data_source = models.CharField(
        max_length=20,
        choices=DataSource.choices,
        default=DataSource.MANUAL_ENTRY,
        db_index=True,
    )

    # Tags M2M
    tags = models.ManyToManyField(
        "tags.Tag",
        blank=True,
        related_name="vendors",
    )

    # Claim status — tracks ownership verification lifecycle (Phase B claim flow)
    claimed_status = models.CharField(
        max_length=20,
        choices=ClaimedStatus.choices,
        default=ClaimedStatus.UNCLAIMED,
        db_index=True,
        help_text="Claim lifecycle: UNCLAIMED → CLAIM_PENDING → CLAIMED/CLAIM_REJECTED.",
    )
    claimed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when claim was approved.",
    )

    # Owner — FK to Customer (Phase B). Nullable until claimed.
    owner = models.ForeignKey(
        "accounts.CustomerUser",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_vendors",
        help_text="Customer who has claimed ownership of this vendor. Phase B.",
    )

    # Storefront photo — S3 object key ONLY (never a public URL)
    storefront_photo_key = models.CharField(
        max_length=500,
        blank=True,
        help_text="S3 object key for the primary storefront photo. Generate presigned URL on read.",
    )

    # Phase B media fields — S3 keys only, presigned URLs generated on read
    logo_key = models.CharField(
        max_length=500,
        blank=True,
        help_text="S3 object key for vendor logo.",
    )
    cover_photo_key = models.CharField(
        max_length=500,
        blank=True,
        help_text="S3 object key for vendor cover photo.",
    )

    # Phase B operational flags
    offers_delivery = models.BooleanField(default=False)
    offers_pickup = models.BooleanField(default=False)
    is_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Admin-verified vendor (badge in UI).",
    )
    location_pending_review = models.BooleanField(
        default=False,
        help_text="True when vendor has submitted a location change awaiting admin approval.",
    )

    # Phase B subscription
    subscription_level = models.CharField(
        max_length=10,
        choices=[
            ("SILVER", "Silver"),
            ("GOLD", "Gold"),
            ("DIAMOND", "Diamond"),
            ("PLATINUM", "Platinum"),
        ],
        default="SILVER",
        db_index=True,
        help_text="Current subscription tier. Defaults to SILVER (free).",
    )
    subscription_valid_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Subscription expiry date. Null means no active paid subscription.",
    )

    # Phase B counters (updated by analytics Celery tasks)
    total_views = models.PositiveIntegerField(
        default=0,
        help_text="Lifetime view count — updated by analytics tasks.",
    )
    total_profile_taps = models.PositiveIntegerField(
        default=0,
        help_text="Lifetime profile tap count — updated by analytics tasks.",
    )
    total_navigation_clicks = models.PositiveIntegerField(
        default=0,
        help_text="Lifetime navigation click count — updated by analytics tasks.",
    )

    # Progressive Activation Strategy (§3.2)
    activation_stage = models.CharField(
        max_length=15,
        choices=ActivationStage.choices,
        default=ActivationStage.CLAIM,
        db_index=True,
        help_text="Current stage in the Progressive Activation Strategy.",
    )
    activation_stage_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last activation stage transition.",
    )

    # Google Places integration
    google_place_id = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        help_text="Google Places place_id — used for upsert deduplication on re-import",
    )
    website_url = models.URLField(
        blank=True, default="", help_text="Business website from Google Places"
    )

    # Soft delete (R6) — default manager filters this out automatically
    is_deleted = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Default manager — filters is_deleted=False automatically (R6)
    objects = ActiveVendorManager()

    # Unfiltered manager — for admin/QA/migration use only
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"
        ordering = ["-created_at"]
        indexes = [
            # Composite indexes per plan spec
            models.Index(
                fields=["qc_status", "is_deleted"], name="vendor_qc_deleted_idx"
            ),
            models.Index(fields=["area", "is_deleted"], name="vendor_area_deleted_idx"),
            models.Index(fields=["data_source"], name="vendor_data_source_idx"),
            # Phase B indexes
            models.Index(
                fields=["subscription_level", "is_deleted"],
                name="vendor_sub_deleted_idx",
            ),
            models.Index(
                fields=["is_verified", "is_deleted"],
                name="vendor_verified_deleted_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.business_name} ({self.qc_status})"

    def delete(self, using: str | None = None, keep_parents: bool = False) -> tuple:
        """Soft delete — sets is_deleted=True and saves. Never hard-deletes (R6).

        Args:
            using: Database alias (ignored — soft delete only).
            keep_parents: Ignored — soft delete only.

        Returns:
            Tuple of (1, {"vendors.Vendor": 1}) to mimic Django's delete() return.
        """
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated_at"])
        return 1, {f"{self._meta.app_label}.{self._meta.object_name}": 1}


class Discount(models.Model):
    """A discount or promotion offered by a vendor (Phase B §3.1).

    Supports percentage, fixed amount, BOGO, happy hour, and flash deal types.
    Time-bounded via start_time/end_time. Recurring discounts supported via
    recurrence_days JSONField.

    Activation/deactivation is managed by the discount_scheduler Celery task
    (every 1 minute) — not by the API consumer.

    Attributes:
        id: UUID primary key.
        vendor: FK to Vendor.
        title: Short display title (e.g. "20% Off Lunch").
        discount_type: DiscountType TextChoices.
        value: Numeric value (percentage or fixed amount).
        applies_to: What the discount applies to (e.g. "ALL", "DINE_IN", "DELIVERY").
        item_description: Optional item-level description.
        start_time: When the discount becomes active.
        end_time: When the discount expires.
        is_recurring: Whether the discount repeats on specified days.
        recurrence_days: JSONField list of ISO day numbers (1=MON..7=SUN).
        is_active: Current activation state — managed by discount_scheduler.
        min_order_value: Minimum order value for the discount to apply.
        created_at: Auto-set on creation.
        updated_at: Auto-updated on every save.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="discounts",
    )
    title = models.CharField(max_length=255)
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
    )
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Percentage (e.g. 20.00) or fixed amount in PKR.",
    )
    applies_to = models.CharField(
        max_length=50,
        default="ALL",
        help_text="What the discount applies to: ALL, DINE_IN, DELIVERY, PICKUP, SPECIFIC_ITEM.",
    )
    item_description = models.TextField(
        blank=True,
        help_text="Optional description of specific items the discount applies to.",
    )

    start_time = models.DateTimeField(
        help_text="When the discount becomes active.",
    )
    end_time = models.DateTimeField(
        help_text="When the discount expires.",
    )

    is_recurring = models.BooleanField(
        default=False,
        help_text="Whether the discount repeats on specified days.",
    )
    recurrence_days = models.JSONField(
        default=list,
        blank=True,
        help_text="ISO day numbers (1=MON..7=SUN) for recurring discounts.",
    )

    is_active = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Managed by discount_scheduler Celery task — not by API consumer.",
    )
    min_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Minimum order value for the discount to apply (PKR).",
    )

    # Delivery-related (§B-6)
    delivery_radius_m = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Delivery radius in metres for free-delivery campaigns.",
    )
    free_delivery_distance_m = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Distance in metres within which delivery is free.",
    )

    # AR display
    ar_badge_text = models.CharField(
        max_length=50,
        blank=True,
        help_text="Short badge text for AR overlay, e.g. '20% OFF', 'Happy Hour'.",
    )

    # Campaign performance counters
    views_during_campaign = models.PositiveIntegerField(
        default=0,
        help_text="View count during this campaign — updated by analytics tasks.",
    )
    taps_during_campaign = models.PositiveIntegerField(
        default=0,
        help_text="Tap count during this campaign — updated by analytics tasks.",
    )
    navigation_clicks_during_campaign = models.PositiveIntegerField(
        default=0,
        help_text="Navigation click count during this campaign — updated by analytics tasks.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Discount"
        verbose_name_plural = "Discounts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["vendor", "is_active"],
                name="discount_vendor_active_idx",
            ),
            models.Index(
                fields=["start_time", "end_time"],
                name="discount_time_range_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.discount_type}) — {self.vendor.business_name}"

    @property
    def is_currently_active(self) -> bool:
        """Check if the discount is currently within its active time window.

        Returns:
            True if now is between start_time and end_time and is_active is True.
        """
        from django.utils import timezone

        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time


class VoiceBotConfig(models.Model):
    """Voice bot configuration for a vendor (Phase B §3.1, one-to-one with Vendor).

    Stores menu items, opening hours summary, delivery info, discount summary,
    and custom QA pairs for the rule-based voice bot system.

    discount_summary is auto-updated by the TagAutoAssigner when discounts change.

    Attributes:
        id: UUID primary key.
        vendor: One-to-one FK to Vendor.
        menu_items: JSONField list of menu item dicts.
        opening_hours_summary: Human-readable text summary of business hours.
        delivery_info: Delivery/pickup information text.
        discount_summary: Auto-updated summary of active discounts.
        custom_qa_pairs: JSONField list of {question, answer} dicts.
        last_updated_at: Tracks when vendor last updated their voice bot data.
        created_at: Auto-set on creation.
        updated_at: Auto-updated on every save.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    vendor = models.OneToOneField(
        Vendor,
        on_delete=models.CASCADE,
        related_name="voice_bot_config",
    )

    menu_items = models.JSONField(
        default=list,
        blank=True,
        help_text="List of menu item dicts: [{name, price, description, is_available}].",
    )
    opening_hours_summary = models.TextField(
        blank=True,
        help_text="Human-readable summary of business hours for voice responses.",
    )
    delivery_info = models.JSONField(
        default=dict,
        blank=True,
        help_text="Delivery info dict: {radius_km, free_within_km, charges}.",
    )
    discount_summary = models.TextField(
        blank=True,
        help_text="Auto-updated summary of active discounts for voice responses.",
    )
    custom_qa_pairs = models.JSONField(
        default=list,
        blank=True,
        help_text="List of custom QA dicts: [{question, answer}].",
    )
    intro_message = models.TextField(
        blank=True,
        help_text="Custom greeting/intro message for the voice bot.",
    )
    pickup_available = models.BooleanField(
        default=False,
        help_text="Whether this vendor offers pickup — used in voice responses.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the voice bot is enabled for this vendor.",
    )
    completeness_score = models.PositiveIntegerField(
        default=0,
        help_text="Auto-calculated 0-100 score of voice bot data completeness.",
    )

    last_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the vendor last updated their voice bot data.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Voice Bot Config"
        verbose_name_plural = "Voice Bot Configs"

    def __str__(self) -> str:
        return f"VoiceBotConfig — {self.vendor.business_name}"
