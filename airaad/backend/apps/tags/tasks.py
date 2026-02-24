"""
AirAd — apps/tags/tasks.py

Two tasks:

expire_promotion_tags (Layer 3 — spec §4.3):
    Deactivates PROMOTION tags whose expires_at has passed.
    Runs every 5 minutes via Celery Beat.
    Functional implementation — not a stub.

generate_time_context_tags (Layer 4 — spec §4.4):
    Auto-assigns time-context tags (Breakfast, Lunch, EveningSnacks, Dinner,
    LateNightOpen, OpenNow) to vendors based on business hours and current time.
    Registered in Celery Beat (every 1 hour).
    Phase B scaffold — no-op stub until Phase B (TASK-B07).
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="apps.tags.tasks.expire_promotion_tags")
def expire_promotion_tags(self) -> None:
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
        from apps.tags.models import Tag, TagType
        from django.utils import timezone

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
def generate_time_context_tags(self) -> None:
    """Auto-assign Layer 4 time-context tags to vendors based on business hours.

    Spec §4.4 time tags: Breakfast (6–11), Lunch (12–15), EveningSnacks (16–19),
    Dinner (19–23), LateNightOpen (23+), OpenNow (current time within hours).

    Registered in Celery Beat (every 1 hour).
    Phase B scaffold — full implementation deferred to Phase B (TASK-B07).
    """
    logger.debug("generate_time_context_tags: Phase B scaffold — no-op until TASK-B07.")


@shared_task(bind=True, name="apps.tags.tasks.hourly_tag_assignment")
def hourly_tag_assignment(self) -> None:
    """Auto-assign tags to vendors based on business profile signals.

    Registered in celery_app.py Beat schedule (every 1 hour).
    Full implementation deferred to Phase B — TASK-B07.
    """
    logger.debug("hourly_tag_assignment: Phase B stub — no-op.")
