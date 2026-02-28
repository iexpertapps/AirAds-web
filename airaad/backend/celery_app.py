"""
AirAd Backend — Celery Application
All Beat schedules registered in code via setup_periodic_tasks() — never in DB (R10).
task_failure signal handler uses structured logging — never print().
"""

import logging
import os
from typing import Any

from celery import Celery
from celery.signals import task_failure

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Celery app instance
# ---------------------------------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("airaad")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


# ---------------------------------------------------------------------------
# Beat schedules — all registered in code, never stored in DB (R10)
# Registered after all apps are finalized to ensure task names are resolvable.
# ---------------------------------------------------------------------------
@app.on_after_finalize.connect
def setup_periodic_tasks(sender: Celery, **kwargs: Any) -> None:
    """Register all Celery Beat periodic schedules in code.

    Phase A: 9 tasks (QA scans, tag expiry, governance).
    Phase B: 8 tasks (discounts, subscriptions, tags, flash deals, happy hours,
    voicebot freshness, vendor churn, monthly reports).
    Beat replicas must be exactly 1 (R10).

    Args:
        sender: The Celery app instance.
        **kwargs: Additional signal keyword arguments.
    """
    from celery.schedules import crontab

    # Phase A — GPS drift scan: every Sunday at 02:00 UTC
    sender.add_periodic_task(
        crontab(hour=2, minute=0, day_of_week="sunday"),
        app.signature("apps.qa.tasks.weekly_gps_drift_scan"),
        name="weekly_gps_drift_scan",
    )

    # Phase A — Duplicate vendor scan: daily at 03:00 UTC
    sender.add_periodic_task(
        crontab(hour=3, minute=0),
        app.signature("apps.qa.tasks.daily_duplicate_scan"),
        name="daily_duplicate_scan",
    )

    # Phase A — Layer 3: expire PROMOTION tags whose expires_at has passed (spec §4.3)
    sender.add_periodic_task(
        crontab(minute="*/5"),
        app.signature("apps.tags.tasks.expire_promotion_tags"),
        name="expire_promotion_tags",
    )

    # Governance — lift expired TEMPORARY_SUSPENSION records (spec §8.2)
    sender.add_periodic_task(
        crontab(hour=1, minute=0),
        app.signature("apps.governance.tasks.expire_temporary_suspensions"),
        name="expire_temporary_suspensions",
    )

    # Governance — hard-purge anonymised accounts >30 days after GDPR deletion (spec §8.1)
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        app.signature("apps.governance.tasks.purge_deleted_user_data"),
        name="purge_deleted_user_data",
    )

    # Governance — delete AnalyticsEvent rows older than 90 days (spec §8.1)
    sender.add_periodic_task(
        crontab(hour=3, minute=30),
        app.signature("apps.governance.tasks.purge_old_analytics_events"),
        name="purge_old_analytics_events",
    )

    # Governance — flag tags with <1% vendor usage for deprecation review (spec §5.1)
    sender.add_periodic_task(
        crontab(hour=4, minute=0, day_of_month=1),
        app.signature("apps.governance.tasks.deprecate_unused_tags"),
        name="deprecate_unused_tags",
    )

    # Governance — audit log retention warning: approaching/past 1-year mark (spec §2.3)
    sender.add_periodic_task(
        crontab(hour=5, minute=0, day_of_month=1),
        app.signature("apps.governance.tasks.audit_log_retention_check"),
        name="audit_log_retention_check",
    )

    # Phase B scaffold — Layer 4: time-context tag auto-generation (spec §4.4, TASK-B07)
    sender.add_periodic_task(
        crontab(minute=0),
        app.signature("apps.tags.tasks.generate_time_context_tags"),
        name="generate_time_context_tags",
    )

    # -----------------------------------------------------------------------
    # Phase B tasks — all implemented, no guards needed
    # -----------------------------------------------------------------------

    # Phase B — Discount scheduler: every 1 minute (§3.4)
    sender.add_periodic_task(
        60.0,
        app.signature("apps.vendors.tasks.discount_scheduler"),
        name="discount_scheduler",
    )

    # Phase B — Subscription expiry check: daily at midnight UTC (§3.4)
    sender.add_periodic_task(
        crontab(hour=0, minute=0),
        app.signature("apps.subscriptions.tasks.subscription_expiry_check"),
        name="subscription_expiry_check",
    )

    # Phase B — Hourly tag auto-assignment: every 1 hour (§3.4)
    sender.add_periodic_task(
        crontab(minute=0),
        app.signature("apps.vendors.tasks.hourly_tag_assignment"),
        name="hourly_tag_assignment",
    )

    # Phase B — Flash deal trigger: every 5 minutes (§3.4)
    sender.add_periodic_task(
        crontab(minute="*/5"),
        app.signature("apps.vendors.tasks.flash_deal_trigger"),
        name="flash_deal_trigger",
    )

    # Phase B — Auto happy hour trigger: every 15 minutes (§3.4)
    sender.add_periodic_task(
        crontab(minute="*/15"),
        app.signature("apps.vendors.tasks.auto_happy_hour_trigger"),
        name="auto_happy_hour_trigger",
    )

    # Phase B — Voice bot freshness check: daily at 06:00 UTC
    sender.add_periodic_task(
        crontab(hour=6, minute=0),
        app.signature("apps.subscriptions.tasks.voicebot_freshness_check"),
        name="voicebot_freshness_check",
    )

    # Phase B — Vendor churn check: daily at 07:00 UTC
    sender.add_periodic_task(
        crontab(hour=7, minute=0),
        app.signature("apps.subscriptions.tasks.vendor_churn_check"),
        name="vendor_churn_check",
    )

    # Phase B — Vendor monthly report: 1st of month at 06:00 UTC
    sender.add_periodic_task(
        crontab(hour=6, minute=0, day_of_month=1),
        app.signature("apps.subscriptions.tasks.vendor_monthly_report"),
        name="vendor_monthly_report",
    )

    # Phase B — Vendor activation check: daily at 02:00 UTC (§3.2)
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        app.signature("apps.vendors.tasks.vendor_activation_check"),
        name="vendor_activation_check",
    )


# ---------------------------------------------------------------------------
# task_failure signal — structured logging, never print()
# ---------------------------------------------------------------------------
@task_failure.connect
def on_task_failure(
    sender: Any,
    task_id: str,
    exception: Exception,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    traceback: Any,
    einfo: Any,
    **signal_kwargs: Any,
) -> None:
    """Handle Celery task failure with structured logging.

    Logs task name, task_id, and exception message. Never raises — signal
    handlers must not propagate exceptions back to the worker.

    Args:
        sender: The task class that failed.
        task_id: Unique ID of the failed task execution.
        exception: The exception instance that caused the failure.
        args: Positional arguments the task was called with.
        kwargs: Keyword arguments the task was called with.
        traceback: Traceback object.
        einfo: ExceptionInfo object from billiard.
        **signal_kwargs: Additional signal keyword arguments.
    """
    logger.error(
        "Task failed",
        extra={
            "task": sender.name,
            "task_id": task_id,
            "exception": str(exception),
            "exception_type": type(exception).__name__,
        },
    )
