"""
AirAd Backend — Analytics Service Layer (R4)

Analytics recording is fire-and-forget via Celery — API response never waits.
Phase A: stub KPI aggregations. Phase B: full AnalyticsEvent model + partitioning.
Every mutation calls log_action() (R5).
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def record_vendor_view(
    vendor_id: str,
    actor_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Dispatch a vendor view analytics event asynchronously via Celery.

    The API response never waits for this write. Task failure is logged
    but never propagated to the caller (fire-and-forget).

    Args:
        vendor_id: UUID string of the viewed Vendor.
        actor_id: UUID string of the actor, or None for anonymous access.
        metadata: Optional context dict (ip_address, user_agent, request_id).
    """
    from apps.analytics.tasks import record_vendor_view_task

    record_vendor_view_task.delay(
        vendor_id=vendor_id,
        actor_id=actor_id,
        metadata=metadata or {},
    )


def get_platform_kpis() -> dict[str, Any]:
    """Return platform KPI counts and trend data for the admin dashboard.

    Phase A: simple DB counts + 14-day trend + recent activity feed.
    Phase B: aggregated AnalyticsEvent queries.

    Returns:
        Dict with scalar KPIs, qc_status_breakdown, daily_vendor_counts,
        import_activity, recent_activity, and vendors_approved_today.
    """
    from datetime import timedelta

    from apps.audit.models import AuditLog
    from apps.imports.models import ImportBatch, ImportStatus
    from apps.vendors.models import QCStatus, Vendor
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    from django.utils import timezone

    today = timezone.now().date()

    total = Vendor.objects.count()

    # QC breakdown for pie chart
    qc_breakdown_qs = Vendor.objects.values("qc_status").annotate(count=Count("id"))
    qc_status_breakdown = {item["qc_status"]: item["count"] for item in qc_breakdown_qs}

    # 14-day vendor creation trend for line chart
    fourteen_days_ago = today - timedelta(days=13)
    daily_counts_qs = (
        Vendor.objects.filter(created_at__date__gte=fourteen_days_ago)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    daily_vendor_counts = [
        {"date": str(item["day"]), "count": item["count"]} for item in daily_counts_qs
    ]

    # 7-day import activity for bar chart
    seven_days_ago = today - timedelta(days=6)
    import_activity_qs = (
        ImportBatch.objects.filter(created_at__date__gte=seven_days_ago)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )
    import_activity = [
        {"date": str(item["day"]), "total": item["total"]}
        for item in import_activity_qs
    ]

    # Recent activity feed — last 10 AuditLog entries
    recent_logs = AuditLog.objects.order_by("-created_at")[:10]
    recent_activity = [
        {
            "action": log.action,
            "actor": log.actor_label,
            "target_type": log.target_type,
            "created_at": log.created_at.isoformat(),
        }
        for log in recent_logs
    ]

    # Vendors approved today
    vendors_approved_today = Vendor.objects.filter(
        qc_status=QCStatus.APPROVED,
        qc_reviewed_at__date=today,
    ).count()

    # Imports currently in PROCESSING state
    imports_processing = ImportBatch.objects.filter(
        status=ImportStatus.PROCESSING
    ).count()

    # Vendors pending QA review
    vendors_pending_qa = Vendor.objects.filter(qc_status=QCStatus.NEEDS_REVIEW).count()

    # top_search_terms: Phase A stub — AnalyticsEvent search queries not yet aggregated (Phase B)
    top_search_terms: list[dict] = []

    # system_alerts: Phase A stub — alert engine not yet implemented (Phase B)
    system_alerts: list[dict] = []

    return {
        "total_vendors": total,
        "vendor_count": total,
        "approved_vendors": Vendor.objects.filter(qc_status=QCStatus.APPROVED).count(),
        "pending_vendors": Vendor.objects.filter(qc_status=QCStatus.PENDING).count(),
        "vendors_pending_qa": vendors_pending_qa,
        "vendors_approved_today": vendors_approved_today,
        "imports_processing": imports_processing,
        "import_batch_count": ImportBatch.objects.count(),
        "total_areas": Vendor.objects.values("area_id").distinct().count(),
        "total_tags": 0,
        "qc_status_breakdown": qc_status_breakdown,
        "daily_vendor_counts": daily_vendor_counts,
        "import_activity": import_activity,
        "recent_activity": recent_activity,
        "top_search_terms": top_search_terms,
        "system_alerts": system_alerts,
    }
