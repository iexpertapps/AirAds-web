"""
AirAd Backend — Stripe Payment Models (Phase C §8)

StripeCustomer: Links a Vendor to a Stripe Customer ID.
StripeEvent: Idempotency log for webhook events — skip if already processed.
VendorSubscription: Tracks the active Stripe subscription for a vendor.
"""

import uuid

from django.db import models


class StripeCustomer(models.Model):
    """Links an AirAd Vendor to a Stripe Customer.

    One-to-one relationship — each vendor has at most one Stripe customer.

    Attributes:
        id: UUID primary key.
        vendor: OneToOne FK to Vendor.
        stripe_customer_id: Stripe's cus_xxx identifier (unique).
        created_at: Auto-set on creation.
        updated_at: Auto-set on save.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.OneToOneField(
        "vendors.Vendor",
        on_delete=models.CASCADE,
        related_name="stripe_customer",
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Stripe Customer ID (cus_xxx).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stripe Customer"
        verbose_name_plural = "Stripe Customers"

    def __str__(self) -> str:
        return f"{self.stripe_customer_id} → Vendor {self.vendor_id}"


class SubscriptionStatus(models.TextChoices):
    """Stripe subscription lifecycle states."""

    ACTIVE = "ACTIVE", "Active"
    PAST_DUE = "PAST_DUE", "Past Due"
    CANCELED = "CANCELED", "Canceled"
    INCOMPLETE = "INCOMPLETE", "Incomplete"
    TRIALING = "TRIALING", "Trialing"
    UNPAID = "UNPAID", "Unpaid"


class VendorSubscription(models.Model):
    """Tracks the active Stripe subscription for a vendor.

    Attributes:
        id: UUID primary key.
        vendor: OneToOne FK to Vendor.
        stripe_subscription_id: Stripe's sub_xxx identifier (unique).
        stripe_price_id: Stripe Price ID for the current plan.
        status: Current subscription status.
        current_period_start: Start of current billing period.
        current_period_end: End of current billing period.
        cancel_at_period_end: Whether subscription cancels at period end.
        canceled_at: When cancellation was requested.
        created_at: Auto-set on creation.
        updated_at: Auto-set on save.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.OneToOneField(
        "vendors.Vendor",
        on_delete=models.CASCADE,
        related_name="vendor_subscription",
    )
    package = models.ForeignKey(
        "subscriptions.SubscriptionPackage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vendor_subscriptions",
        help_text="FK to SubscriptionPackage for the current tier.",
    )
    stripe_subscription_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Stripe Subscription ID (sub_xxx).",
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Stripe Customer ID (cus_xxx) — denormalised for quick lookup.",
    )
    stripe_price_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Stripe Price ID for the current plan.",
    )
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.INCOMPLETE,
        db_index=True,
    )
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vendor Subscription"
        verbose_name_plural = "Vendor Subscriptions"

    def __str__(self) -> str:
        return f"{self.stripe_subscription_id} ({self.status}) → Vendor {self.vendor_id}"


class StripeEvent(models.Model):
    """Idempotency log for Stripe webhook events.

    Every webhook checks this table — skip if stripe_event_id already exists.
    Prevents double-processing of events.

    Attributes:
        id: UUID primary key.
        stripe_event_id: Stripe's evt_xxx identifier (unique).
        event_type: Stripe event type string (e.g. "invoice.paid").
        data: Full event JSON payload.
        processed: Whether the event was successfully processed.
        error_message: Error message if processing failed.
        created_at: Auto-set on creation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stripe_event_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Stripe Event ID (evt_xxx) — idempotency key.",
    )
    event_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Stripe event type (e.g. checkout.session.completed).",
    )
    data = models.JSONField(
        default=dict,
        help_text="Full Stripe event payload.",
    )
    processed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if event was successfully processed.",
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if processing failed.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stripe Event"
        verbose_name_plural = "Stripe Events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "processed"], name="stripe_evt_type_proc_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.stripe_event_id} ({self.event_type}) processed={self.processed}"
