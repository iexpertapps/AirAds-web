"""
AirAd Backend — Notification Models (Phase B §B-10)

NotificationTemplate stores reusable message templates with placeholders.
NotificationLog tracks every notification dispatch for audit and retry.
"""

import uuid

from django.db import models


class NotificationType(models.TextChoices):
    """Category of notification."""

    CLAIM_STATUS = "CLAIM_STATUS", "Claim Status"
    SUBSCRIPTION = "SUBSCRIPTION", "Subscription"
    PROMOTION = "PROMOTION", "Promotion"
    SYSTEM = "SYSTEM", "System"
    CHURN_PREVENTION = "CHURN_PREVENTION", "Churn Prevention"
    MODERATION = "MODERATION", "Moderation"


class NotificationChannel(models.TextChoices):
    """Delivery channel for a notification."""

    PUSH = "PUSH", "Push"
    EMAIL = "EMAIL", "Email"
    SMS = "SMS", "SMS"


class NotificationStatus(models.TextChoices):
    """Delivery status of a notification."""

    PENDING = "PENDING", "Pending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"


class RecipientType(models.TextChoices):
    """Type of notification recipient."""

    VENDOR = "VENDOR", "Vendor"
    CUSTOMER = "CUSTOMER", "Customer"


class NotificationTemplate(models.Model):
    """Reusable notification template with placeholder support (Phase B §B-10).

    Templates use Python str.format() style placeholders:
      title_template: "Your claim for {vendor_name} has been {status}"
      body_template:  "Hi {full_name}, your vendor claim ..."

    Attributes:
        id: UUID primary key.
        slug: Unique slug for programmatic lookup (e.g. "claim_approved").
        title_template: Title with {placeholder} variables.
        body_template: Body with {placeholder} variables.
        notification_type: Category of notification.
        is_active: Whether this template is in use.
        created_at: Auto-set on creation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    slug = models.SlugField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique slug for programmatic lookup, e.g. 'claim_approved'.",
    )
    title_template = models.CharField(
        max_length=500,
        help_text="Title with {placeholder} variables.",
    )
    body_template = models.TextField(
        help_text="Body with {placeholder} variables.",
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification Template"
        verbose_name_plural = "Notification Templates"
        ordering = ["slug"]

    def __str__(self) -> str:
        return f"{self.slug} ({self.notification_type})"


class NotificationLog(models.Model):
    """Tracks every notification dispatch for audit, retry, and analytics (Phase B §B-10).

    Attributes:
        id: UUID primary key.
        recipient_type: VENDOR or CUSTOMER.
        recipient_id: UUID of the recipient (CustomerUser or Vendor owner).
        template: FK to NotificationTemplate (nullable for ad-hoc messages).
        title: Rendered notification title.
        body: Rendered notification body.
        data_payload: Extra JSON payload for push notifications.
        channel: Delivery channel (PUSH, EMAIL, SMS).
        status: Delivery status.
        sent_at: Timestamp of successful delivery.
        error_message: Error details on failure.
        created_at: Auto-set on creation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    recipient_type = models.CharField(
        max_length=10,
        choices=RecipientType.choices,
        db_index=True,
    )
    recipient_id = models.UUIDField(
        db_index=True,
        help_text="UUID of the recipient (CustomerUser.id or Vendor.owner.id).",
    )

    template = models.ForeignKey(
        NotificationTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="logs",
    )

    title = models.CharField(max_length=500)
    body = models.TextField()
    data_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra JSON payload for push notification data field.",
    )

    channel = models.CharField(
        max_length=5,
        choices=NotificationChannel.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=10,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(
        blank=True,
        help_text="Error details on delivery failure.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification Log"
        verbose_name_plural = "Notification Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["recipient_type", "recipient_id"],
                name="notif_recipient_idx",
            ),
            models.Index(
                fields=["status", "channel"],
                name="notif_status_channel_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.channel} → {self.recipient_type}:{self.recipient_id} ({self.status})"
