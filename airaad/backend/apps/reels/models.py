"""
AirAd Backend — Reel Models (Phase B §B-9)

VendorReel stores short-form video content uploaded by vendors.
Tier-based upload limits enforced in services.py via vendor_has_feature().
Moderation workflow: PENDING → APPROVED / REJECTED by admin.
"""

import uuid

from django.db import models


class ReelStatus(models.TextChoices):
    """Processing lifecycle status for a reel."""

    PROCESSING = "PROCESSING", "Processing"
    ACTIVE = "ACTIVE", "Active"
    REJECTED = "REJECTED", "Rejected"
    ARCHIVED = "ARCHIVED", "Archived"


class ModerationStatus(models.TextChoices):
    """Admin moderation status for a reel."""

    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class VendorReel(models.Model):
    """A short-form video/reel uploaded by a vendor (Phase B §B-9).

    Upload limits are enforced per subscription tier via SubscriptionPackage.max_videos.
    Moderation is required before public display.
    S3 keys only — presigned URLs generated on read.

    Attributes:
        id: UUID primary key.
        vendor: FK to Vendor.
        title: Short display title.
        s3_key: S3 object key for the video file.
        thumbnail_s3_key: S3 object key for the thumbnail image.
        duration_seconds: Video duration in seconds.
        status: Processing lifecycle status.
        view_count: Total view count — updated by analytics tasks.
        completion_count: Full-watch completion count.
        display_order: Vendor-controlled ordering.
        is_active: Soft-active flag.
        moderation_status: Admin moderation state.
        moderation_notes: Admin notes on rejection/approval.
        created_at: Auto-set on creation.
        updated_at: Auto-updated on every save.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    vendor = models.ForeignKey(
        "vendors.Vendor",
        on_delete=models.CASCADE,
        related_name="reels",
    )
    title = models.CharField(max_length=255)

    # S3 keys — NEVER public URLs. Generate presigned URLs on read.
    s3_key = models.CharField(
        max_length=500,
        help_text="S3 object key for the reel video file.",
    )
    thumbnail_s3_key = models.CharField(
        max_length=500,
        blank=True,
        help_text="S3 object key for the reel thumbnail image.",
    )

    duration_seconds = models.PositiveIntegerField(
        help_text="Video duration in seconds.",
    )

    status = models.CharField(
        max_length=12,
        choices=ReelStatus.choices,
        default=ReelStatus.PROCESSING,
        db_index=True,
    )

    # Engagement counters — updated by analytics tasks
    view_count = models.PositiveIntegerField(default=0)
    completion_count = models.PositiveIntegerField(default=0)

    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Vendor-controlled display order. Lower = shown first.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    # Moderation workflow
    moderation_status = models.CharField(
        max_length=10,
        choices=ModerationStatus.choices,
        default=ModerationStatus.PENDING,
        db_index=True,
    )
    moderation_notes = models.TextField(
        blank=True,
        help_text="Admin notes on moderation decision.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vendor Reel"
        verbose_name_plural = "Vendor Reels"
        ordering = ["display_order", "-created_at"]
        indexes = [
            models.Index(
                fields=["vendor", "is_active"],
                name="reel_vendor_active_idx",
            ),
            models.Index(
                fields=["moderation_status", "is_active"],
                name="reel_moderation_active_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.vendor.business_name} ({self.status})"
