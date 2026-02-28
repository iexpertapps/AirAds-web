"""
AirAd Backend — Tag Celery Tasks

expire_promotion_tags (Layer 3 — spec §4.3):
    Deactivates PROMOTION tags whose expires_at has passed.
    Runs every 5 minutes via Celery Beat.

generate_time_context_tags (Layer 4 — spec §4.4, Phase B):
    Auto-assigns time-context tags (Breakfast, Lunch, EveningSnacks, Dinner,
    LateNightOpen, OpenNow) to vendors based on business hours and current time.
    Runs every 1 hour via Celery Beat.

NOTE: hourly_tag_assignment lives in apps.vendors.tasks (Phase B §3.4).
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)

_DAY_MAP = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday",
}

_TIME_CONTEXT_WINDOWS = {
    "time-breakfast": (6, 11),
    "time-lunch": (12, 15),
    "time-evening-snacks": (16, 19),
    "time-dinner": (19, 23),
    "time-late-night-open": (23, 6),
}


@shared_task(bind=True, name="apps.tags.tasks.expire_promotion_tags")
def expire_promotion_tags(self: Any) -> None:
    """Deactivate PROMOTION tags whose expires_at datetime has passed.

    Spec §4.3: Promotion tags are time-bound and expire when promotions end.
    Runs every 5 minutes via Celery Beat.

    Sets is_active=False on all PROMOTION tags where:
      - expires_at is not null
      - expires_at <= now()
      - is_active is still True

    Logs the count of deactivated tags. Never raises — failures are logged only.
    """
    try:
        from django.utils import timezone

        from apps.tags.models import Tag, TagType

        now = timezone.now()
        expired_qs = Tag.objects.filter(
            tag_type=TagType.PROMOTION,
            is_active=True,
            expires_at__lte=now,
        )
        count = expired_qs.count()
        if count:
            expired_qs.update(is_active=False)
            logger.info(
                "expire_promotion_tags: deactivated %d expired PROMOTION tag(s).",
                count,
            )
        else:
            logger.debug("expire_promotion_tags: no expired PROMOTION tags found.")
    except Exception as exc:
        logger.error("expire_promotion_tags failed: %s", exc, exc_info=True)


@shared_task(bind=True, name="apps.tags.tasks.generate_time_context_tags")
def generate_time_context_tags(self: Any) -> None:
    """Auto-assign Layer 4 time-context tags to vendors based on business hours.

    Spec §4.4 time tags:
    - Breakfast (6–11)
    - Lunch (12–15)
    - EveningSnacks (16–19)
    - Dinner (19–23)
    - LateNightOpen (23–6)
    - OpenNow (current time within business hours)

    Registered in Celery Beat (every 1 hour).
    For each vendor, checks business_hours JSON for the current day,
    determines which time windows apply, and assigns/removes tags.
    """
    try:
        from django.utils import timezone

        from apps.tags.models import Tag, TagType
        from apps.vendors.models import Vendor

        now = timezone.now()
        current_hour = now.hour
        current_day_key = _DAY_MAP.get(now.weekday(), "monday")

        time_tags: dict[str, Any] = {}
        for slug in list(_TIME_CONTEXT_WINDOWS.keys()) + ["time-open-now"]:
            tag = Tag.objects.filter(
                slug=slug, tag_type=TagType.TIME, is_active=True
            ).first()
            if tag:
                time_tags[slug] = tag

        if not time_tags:
            logger.debug("generate_time_context_tags: no TIME tags in DB — skipping.")
            return

        vendors = Vendor.objects.filter(is_deleted=False).only(
            "id", "business_hours"
        )

        assigned = 0
        removed = 0
        batch_size = 500

        for vendor in vendors[:batch_size]:
            hours = vendor.business_hours or {}
            day_hours = hours.get(current_day_key, {})
            is_closed = day_hours.get("is_closed", True)
            open_time = day_hours.get("open", "")
            close_time = day_hours.get("close", "")

            open_hour = _parse_hour(open_time)
            close_hour = _parse_hour(close_time)

            vendor_is_open = False
            if not is_closed and open_hour is not None and close_hour is not None:
                if open_hour <= close_hour:
                    vendor_is_open = open_hour <= current_hour < close_hour
                else:
                    vendor_is_open = current_hour >= open_hour or current_hour < close_hour

            open_now_tag = time_tags.get("time-open-now")
            if open_now_tag:
                if vendor_is_open:
                    vendor.tags.add(open_now_tag)
                    assigned += 1
                else:
                    vendor.tags.remove(open_now_tag)
                    removed += 1

            for slug, (start_h, end_h) in _TIME_CONTEXT_WINDOWS.items():
                tag = time_tags.get(slug)
                if not tag:
                    continue

                if start_h <= end_h:
                    in_window = start_h <= current_hour < end_h
                else:
                    in_window = current_hour >= start_h or current_hour < end_h

                if in_window and vendor_is_open:
                    vendor.tags.add(tag)
                    assigned += 1
                else:
                    vendor.tags.remove(tag)
                    removed += 1

        logger.info(
            "generate_time_context_tags complete",
            extra={
                "hour": current_hour,
                "day": current_day_key,
                "tags_assigned": assigned,
                "tags_removed": removed,
            },
        )
    except Exception as exc:
        logger.error("generate_time_context_tags failed: %s", exc, exc_info=True)


def _parse_hour(time_str: str) -> int | None:
    """Parse HH:MM string and return the hour as int, or None."""
    if not time_str or ":" not in time_str:
        return None
    try:
        return int(time_str.split(":")[0])
    except (ValueError, IndexError):
        return None
