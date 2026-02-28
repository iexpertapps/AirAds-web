"""
AirAd Backend — AnalyticsEvent Model (spec §7.1)

Captures discovery events for Phase B analytics and NLP training improvement.
Phase A: model + migration only — no writes yet (fire-and-forget task logs to logger).
Phase B: record_vendor_view_task writes real rows here.

Privacy requirements (spec §7.2):
  - actor_id is nullable — anonymous events stored without user identity
  - gps_lat/gps_lon stored as floats (not linked to user identity — anonymised)
  - Data retention enforced externally (90-day raw, indefinite aggregated)
"""

import uuid

from django.db import models


class EventType(models.TextChoices):
    """Discovery event types per spec §7.1 + Phase B extensions."""

    # Phase A events
    AR_VIEW_OPENED = "AR_VIEW_OPENED", "AR View Opened"
    VENDOR_MARKER_TAPPED = "VENDOR_MARKER_TAPPED", "Vendor Marker Tapped"
    VOICE_QUERY_MADE = "VOICE_QUERY_MADE", "Voice Query Made"
    NAVIGATION_STARTED = "NAVIGATION_STARTED", "Navigation Started"
    REEL_VIEWED = "REEL_VIEWED", "Reel Viewed"
    PROMOTION_CLICKED = "PROMOTION_CLICKED", "Promotion Clicked"
    VENDOR_VIEW = "VENDOR_VIEW", "Vendor View"

    # Phase B events (§3.6 analytics)
    VIEW = "VIEW", "View"
    SEARCH = "SEARCH", "Search"
    REEL_VIEW = "REEL_VIEW", "Reel View"
    REEL_SHARE = "REEL_SHARE", "Reel Share"
    DISCOUNT_VIEW = "DISCOUNT_VIEW", "Discount View"
    DISCOUNT_TAP = "DISCOUNT_TAP", "Discount Tap"
    PROFILE_TAP = "PROFILE_TAP", "Profile Tap"


class AnalyticsEvent(models.Model):
    """A single user interaction event for analytics and NLP training.

    Spec §7.1: captures AR views, vendor taps, voice queries, navigation,
    reel views, and promotion clicks.

    Privacy (spec §7.2):
      - actor_id is nullable (anonymous events have no user identity)
      - GPS stored as anonymised floats — not linked to actor_id
      - Raw events retained 90 days; aggregated data indefinitely

    Attributes:
        id: UUID primary key.
        event_type: One of EventType values.
        vendor: FK to Vendor (nullable — some events are not vendor-specific).
        actor_id: UUID of the acting user (nullable — anonymous events).
        gps_lat: Anonymised latitude at time of event (nullable).
        gps_lon: Anonymised longitude at time of event (nullable).
        area: FK to geo.Area (nullable — for area-level analytics).
        metadata: JSON blob for event-specific data (distance, tags, query text, etc.).
        created_at: Timestamp of the event. Indexed for time-range queries.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
        db_index=True,
    )

    # Target vendor — nullable (e.g. AR_VIEW_OPENED has no specific vendor)
    vendor = models.ForeignKey(
        "vendors.Vendor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="analytics_events",
    )

    # Actor — nullable for anonymous events (spec §7.2: no personal identifier)
    actor_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the acting user. Null for anonymous events (spec §7.2).",
    )

    # Anonymised GPS — floats only, not linked to actor_id (spec §7.2)
    gps_lat = models.FloatField(
        null=True,
        blank=True,
        help_text="Anonymised latitude. Not linked to actor_id (spec §7.2).",
    )
    gps_lon = models.FloatField(
        null=True,
        blank=True,
        help_text="Anonymised longitude. Not linked to actor_id (spec §7.2).",
    )

    # Area context — for area-level usage pattern analysis (spec §7.1)
    area = models.ForeignKey(
        "geo.Area",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="analytics_events",
    )

    # Event-specific payload (distance, tags, query text, watch_duration, etc.)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Event-specific context: distance, tags, query_text, watch_duration, etc.",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Analytics Event"
        verbose_name_plural = "Analytics Events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["event_type", "created_at"], name="analytics_type_created_idx"
            ),
            models.Index(
                fields=["vendor", "event_type"], name="analytics_vendor_type_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} @ {self.created_at}"
