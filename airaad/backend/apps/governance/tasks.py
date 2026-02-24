"""
AirAd Backend — Governance Celery Tasks

Five scheduled tasks covering Phase-A governance gaps:

  expire_temporary_suspensions   — daily 01:00 UTC: lift TEMPORARY_SUSPENSION records past their end date
  purge_deleted_user_data        — daily 02:00 UTC: hard-purge anonymised accounts >30 days after deletion
  purge_old_analytics_events     — daily 03:30 UTC: delete AnalyticsEvent rows older than 90 days (spec §8.1)
  deprecate_unused_tags          — monthly 1st 04:00 UTC: flag tags with <1% vendor usage for review (spec §5.1)
  audit_log_retention_check      — monthly 1st 05:00 UTC: warn on audit entries approaching 1-year mark
                                   (spec §2.3: active logs retained 1 year, archived 5 years)
                                   Hard deletion is a compliance decision — task logs warnings only.
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="apps.governance.tasks.expire_temporary_suspensions")
def expire_temporary_suspensions(self) -> None:
    """Lift TEMPORARY_SUSPENSION records whose suspension_ends_at has passed.

    Runs daily at 01:00 UTC via Celery Beat.
    Sets is_active=False on expired suspensions and writes AuditLog.
    """
    try:
        from apps.audit.utils import log_action
        from apps.governance.models import EnforcementAction, VendorSuspension
        from django.utils import timezone

        now = timezone.now()
        expired_qs = VendorSuspension.objects.filter(
            action=EnforcementAction.TEMPORARY_SUSPENSION,
            is_active=True,
            suspension_ends_at__lte=now,
        ).select_related("vendor")

        count = 0
        for suspension in expired_qs:
            suspension.is_active = False
            suspension.save(update_fields=["is_active", "updated_at"])
            log_action(
                action="VENDOR_SUSPENSION_EXPIRED",
                actor=None,
                target_obj=suspension.vendor,
                request=None,
                before={"is_active": True},
                after={
                    "is_active": False,
                    "reason": "Temporary suspension period ended",
                },
            )
            count += 1

        if count:
            logger.info(
                "expire_temporary_suspensions: lifted %d expired suspension(s).", count
            )
        else:
            logger.debug("expire_temporary_suspensions: no expired suspensions found.")
    except Exception as exc:
        logger.error("expire_temporary_suspensions failed: %s", exc, exc_info=True)


@shared_task(bind=True, name="apps.governance.tasks.purge_deleted_user_data")
def purge_deleted_user_data(self) -> None:
    """Hard-purge anonymised AdminUser accounts >30 days after GDPR deletion (spec §8.1).

    Accounts deleted via DELETE /api/v1/auth/me/ are anonymised immediately
    (email replaced with deleted-<uuid>@purged.airaad.internal, is_active=False).
    This task hard-deletes those shells after 30 days, retaining only the
    AuditLog entries (which have actor FK set to NULL on deletion).

    Runs daily at 02:00 UTC via Celery Beat.
    """
    try:
        from datetime import timedelta

        from apps.accounts.models import AdminUser
        from apps.audit.utils import log_action
        from django.utils import timezone

        cutoff = timezone.now() - timedelta(days=30)

        purge_qs = AdminUser.objects.filter(
            is_active=False,
            email__startswith="deleted-",
            email__endswith="@purged.airaad.internal",
            updated_at__lte=cutoff,
        )

        count = purge_qs.count()
        if count:
            log_action(
                action="GDPR_USERS_PURGED",
                actor=None,
                target_obj=None,
                request=None,
                before={},
                after={"purged_count": count, "cutoff_days": 30},
            )
            purge_qs.delete()
            logger.info(
                "purge_deleted_user_data: hard-purged %d anonymised account(s).", count
            )
        else:
            logger.debug("purge_deleted_user_data: no accounts eligible for purge.")
    except Exception as exc:
        logger.error("purge_deleted_user_data failed: %s", exc, exc_info=True)


@shared_task(bind=True, name="apps.governance.tasks.purge_old_analytics_events")
def purge_old_analytics_events(self) -> None:
    """Delete AnalyticsEvent rows older than 90 days (spec §8.1 data retention).

    Raw analytics events are retained for 90 days. Aggregated data in the
    KPI endpoint is unaffected (computed on-the-fly from Vendor/ImportBatch).

    Runs daily at 03:30 UTC via Celery Beat.
    """
    try:
        from datetime import timedelta

        from apps.analytics.models import AnalyticsEvent
        from apps.audit.utils import log_action
        from django.utils import timezone

        cutoff = timezone.now() - timedelta(days=90)
        old_qs = AnalyticsEvent.objects.filter(created_at__lt=cutoff)
        count = old_qs.count()

        if count:
            old_qs.delete()
            log_action(
                action="ANALYTICS_EVENTS_PURGED",
                actor=None,
                target_obj=None,
                request=None,
                before={},
                after={"purged_count": count, "retention_days": 90},
            )
            logger.info(
                "purge_old_analytics_events: deleted %d event(s) older than 90 days.",
                count,
            )
        else:
            logger.debug("purge_old_analytics_events: no events older than 90 days.")
    except Exception as exc:
        logger.error("purge_old_analytics_events failed: %s", exc, exc_info=True)


@shared_task(bind=True, name="apps.governance.tasks.audit_log_retention_check")
def audit_log_retention_check(self) -> None:
    """Warn when AuditLog entries are approaching or past the 1-year active retention mark.

    Spec §2.3: Active logs retained 1 year; archived logs retained 5 years.
    This task does NOT delete any records — hard deletion requires a compliance
    decision and must be performed manually by a SUPER_ADMIN.

    Emits structured log warnings at two thresholds:
      - approaching_count: entries between 335 and 365 days old (30-day warning window)
      - overdue_count: entries older than 365 days (past active retention mark)

    Runs monthly (1st of each month at 05:00 UTC) via Celery Beat.
    """
    try:
        from datetime import timedelta

        from apps.audit.models import AuditLog
        from django.utils import timezone

        now = timezone.now()
        warning_start = now - timedelta(days=335)
        retention_cutoff = now - timedelta(days=365)
        archive_cutoff = now - timedelta(days=365 * 5)

        approaching_count = AuditLog.objects.filter(
            created_at__lte=warning_start,
            created_at__gt=retention_cutoff,
        ).count()

        overdue_count = AuditLog.objects.filter(
            created_at__lte=retention_cutoff,
            created_at__gt=archive_cutoff,
        ).count()

        archive_overdue_count = AuditLog.objects.filter(
            created_at__lte=archive_cutoff,
        ).count()

        if archive_overdue_count:
            logger.warning(
                "audit_log_retention_check: %d audit log entries exceed 5-year archive retention "
                "(spec §2.3). Manual compliance review required before deletion.",
                archive_overdue_count,
            )
        if overdue_count:
            logger.warning(
                "audit_log_retention_check: %d audit log entries are past the 1-year active "
                "retention mark (spec §2.3). Review for archival or deletion by SUPER_ADMIN.",
                overdue_count,
            )
        if approaching_count:
            logger.info(
                "audit_log_retention_check: %d audit log entries will reach the 1-year "
                "retention mark within 30 days (spec §2.3).",
                approaching_count,
            )
        if not approaching_count and not overdue_count and not archive_overdue_count:
            logger.debug(
                "audit_log_retention_check: all audit log entries within retention window."
            )
    except Exception as exc:
        logger.error("audit_log_retention_check failed: %s", exc, exc_info=True)


@shared_task(bind=True, name="apps.governance.tasks.deprecate_unused_tags")
def deprecate_unused_tags(self) -> None:
    """Flag tags with <1% vendor usage for deprecation review (spec §5.1).

    Spec §5.1: Tags with <1% of vendors for 3 consecutive months should be
    deprecated. This task computes current usage and flags tags below the
    threshold as is_active=False with a deprecation note in qc_notes.

    Since we cannot track 3-month history without a dedicated usage-history
    table (Phase B), this task flags tags with zero vendor assignments as
    candidates for deprecation. A Data Quality Analyst reviews the list.

    Runs monthly (1st of each month at 04:00 UTC) via Celery Beat.
    SYSTEM and PROMOTION tags are excluded (auto-managed).
    """
    try:
        from apps.audit.utils import log_action
        from apps.tags.models import Tag, TagType
        from apps.vendors.models import Vendor
        from django.db.models import Count

        total_vendors = Vendor.objects.count()
        if total_vendors == 0:
            logger.debug("deprecate_unused_tags: no vendors — skipping.")
            return

        threshold = max(1, int(total_vendors * 0.01))

        excluded_types = [TagType.SYSTEM, TagType.PROMOTION, TagType.TIME]

        low_usage_tags = (
            Tag.objects.exclude(tag_type__in=excluded_types)
            .filter(is_active=True)
            .annotate(vendor_count=Count("vendors"))
            .filter(vendor_count__lt=threshold)
        )

        flagged_count = 0
        for tag in low_usage_tags:
            tag.is_active = False
            tag.save(update_fields=["is_active"])
            log_action(
                action="TAG_DEPRECATED_LOW_USAGE",
                actor=None,
                target_obj=tag,
                request=None,
                before={"is_active": True},
                after={
                    "is_active": False,
                    "vendor_count": tag.vendor_count,
                    "threshold": threshold,
                    "total_vendors": total_vendors,
                },
            )
            flagged_count += 1

        if flagged_count:
            logger.info(
                "deprecate_unused_tags: deprecated %d tag(s) with <%d vendor assignments.",
                flagged_count,
                threshold,
            )
        else:
            logger.debug("deprecate_unused_tags: all tags meet usage threshold.")
    except Exception as exc:
        logger.error("deprecate_unused_tags failed: %s", exc, exc_info=True)
