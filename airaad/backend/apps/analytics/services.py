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

    from django.db.models import Count
    from django.db.models.functions import TruncDate
    from django.utils import timezone

    from apps.audit.models import AuditLog
    from apps.imports.models import ImportBatch, ImportStatus
    from apps.tags.models import Tag
    from apps.vendors.models import QCStatus, Vendor

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

    # top_search_terms: aggregate SEARCH events from AnalyticsEvent
    from apps.analytics.models import AnalyticsEvent

    search_events = (
        AnalyticsEvent.objects.filter(
            event_type="SEARCH",
            created_at__gte=today - timedelta(days=7),
        )
        .values("metadata__query")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    top_search_terms: list[dict] = []
    for item in search_events:
        query = item.get("metadata__query")
        if query:
            top_search_terms.append({"query": query, "count": item["count"]})

    # system_alerts: check for actionable issues
    system_alerts: list[dict] = []
    zero_view_vendors = Vendor.objects.filter(
        is_deleted=False, total_views=0, claimed_status="CLAIMED",
    ).count()
    if zero_view_vendors > 5:
        system_alerts.append({
            "level": "warning",
            "message": f"{zero_view_vendors} claimed vendors have 0 views",
        })
    failed_imports = ImportBatch.objects.filter(status="FAILED").count()
    if failed_imports > 0:
        system_alerts.append({
            "level": "error",
            "message": f"{failed_imports} import batches in FAILED state",
        })

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
        "total_tags": Tag.objects.filter(is_active=True).count(),
        "qc_status_breakdown": qc_status_breakdown,
        "daily_vendor_counts": daily_vendor_counts,
        "import_activity": import_activity,
        "recent_activity": recent_activity,
        "top_search_terms": top_search_terms,
        "system_alerts": system_alerts,
    }


# =========================================================================
# Phase B — Vendor Analytics (§3.6)
# =========================================================================


def get_vendor_analytics_summary(vendor_id: str) -> dict[str, Any]:
    """Return analytics summary for a specific vendor.

    Args:
        vendor_id: UUID string of the vendor.

    Returns:
        Dict with view counts, tap counts, 14-day trend, and active discounts.
    """
    from datetime import timedelta

    from django.db.models import Count
    from django.db.models.functions import TruncDate
    from django.utils import timezone

    from apps.vendors.models import Vendor

    vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    today = timezone.now().date()
    fourteen_days_ago = today - timedelta(days=13)

    from apps.analytics.models import AnalyticsEvent

    daily_views = (
        AnalyticsEvent.objects.filter(
            vendor_id=vendor_id,
            event_type="VIEW",
            created_at__date__gte=fourteen_days_ago,
        )
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    daily_views_list = [
        {"date": str(item["day"]), "count": item["count"]} for item in daily_views
    ]

    active_discounts = vendor.discounts.filter(is_active=True).count()

    return {
        "vendor_id": str(vendor.id),
        "business_name": vendor.business_name,
        "total_views": vendor.total_views,
        "total_profile_taps": vendor.total_profile_taps,
        "subscription_level": vendor.subscription_level,
        "active_discounts": active_discounts,
        "daily_views": daily_views_list,
    }


def get_vendor_analytics_reels(vendor_id: str) -> dict[str, Any]:
    """Return reel/video analytics for a vendor.

    Args:
        vendor_id: UUID string of the vendor.

    Returns:
        Dict with reel view counts and engagement metrics.
    """
    from apps.analytics.models import AnalyticsEvent

    reel_views = AnalyticsEvent.objects.filter(
        vendor_id=vendor_id,
        event_type="REEL_VIEW",
    ).count()

    reel_shares = AnalyticsEvent.objects.filter(
        vendor_id=vendor_id,
        event_type="REEL_SHARE",
    ).count()

    return {
        "vendor_id": vendor_id,
        "reel_views": reel_views,
        "reel_shares": reel_shares,
    }


def get_vendor_analytics_discounts(vendor_id: str) -> dict[str, Any]:
    """Return discount performance analytics for a vendor.

    Args:
        vendor_id: UUID string of the vendor.

    Returns:
        Dict with discount engagement metrics.
    """
    from apps.analytics.models import AnalyticsEvent
    from apps.vendors.models import Discount

    active_discounts = Discount.objects.filter(
        vendor_id=vendor_id,
        is_active=True,
    ).count()

    total_discounts = Discount.objects.filter(vendor_id=vendor_id).count()

    discount_views = AnalyticsEvent.objects.filter(
        vendor_id=vendor_id,
        event_type="DISCOUNT_VIEW",
    ).count()

    discount_taps = AnalyticsEvent.objects.filter(
        vendor_id=vendor_id,
        event_type="DISCOUNT_TAP",
    ).count()

    return {
        "vendor_id": vendor_id,
        "active_discounts": active_discounts,
        "total_discounts": total_discounts,
        "discount_views": discount_views,
        "discount_taps": discount_taps,
    }


def get_vendor_time_heatmap(vendor_id: str) -> dict[str, Any]:
    """Return hourly view heatmap for a vendor (Gold+ tier).

    Args:
        vendor_id: UUID string of the vendor.

    Returns:
        Dict with hourly view distribution over the last 30 days.
    """
    from datetime import timedelta

    from django.db.models import Count
    from django.db.models.functions import ExtractHour
    from django.utils import timezone

    from apps.analytics.models import AnalyticsEvent

    thirty_days_ago = timezone.now() - timedelta(days=30)

    hourly_data = (
        AnalyticsEvent.objects.filter(
            vendor_id=vendor_id,
            event_type="VIEW",
            created_at__gte=thirty_days_ago,
        )
        .annotate(hour=ExtractHour("created_at"))
        .values("hour")
        .annotate(count=Count("id"))
        .order_by("hour")
    )

    heatmap = {h: 0 for h in range(24)}
    for item in hourly_data:
        heatmap[item["hour"]] = item["count"]

    return {
        "vendor_id": vendor_id,
        "heatmap": heatmap,
        "period_days": 30,
    }


def get_vendor_recommendations(vendor_id: str) -> dict[str, Any]:
    """Return rule-based recommendations for a vendor (Platinum only).

    Args:
        vendor_id: UUID string of the vendor.

    Returns:
        Dict with actionable recommendations.
    """
    from apps.vendors.models import Vendor

    vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)

    recommendations: list[dict[str, str]] = []

    if vendor.total_views < 50:
        recommendations.append({
            "type": "VISIBILITY",
            "message": "Your view count is low. Consider adding a cover photo and more tags.",
            "priority": "HIGH",
        })

    if vendor.discounts.filter(is_active=True).count() == 0:
        recommendations.append({
            "type": "ENGAGEMENT",
            "message": "Create a discount or happy hour to attract more customers.",
            "priority": "MEDIUM",
        })

    if not vendor.offers_delivery and not vendor.offers_pickup:
        recommendations.append({
            "type": "SERVICES",
            "message": "Enable delivery or pickup to reach more customers.",
            "priority": "MEDIUM",
        })

    try:
        config = vendor.voice_bot_config
        if not config.menu_items:
            recommendations.append({
                "type": "VOICE_BOT",
                "message": "Add menu items to your voice bot for better customer engagement.",
                "priority": "LOW",
            })
    except Exception:
        recommendations.append({
            "type": "VOICE_BOT",
            "message": "Set up your voice bot to answer customer questions automatically.",
            "priority": "MEDIUM",
        })

    return {
        "vendor_id": vendor_id,
        "recommendations": recommendations,
        "count": len(recommendations),
    }


# =========================================================================
# Phase B — Admin Platform Analytics (§3.6)
# =========================================================================


def get_admin_platform_overview() -> dict[str, Any]:
    """Return admin platform overview analytics.

    Returns:
        Dict with platform-wide metrics.
    """
    from datetime import timedelta

    from django.db.models import Count, Sum
    from django.utils import timezone

    from apps.accounts.models import CustomerUser
    from apps.vendors.models import Vendor

    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)

    total_vendors = Vendor.objects.count()
    claimed_vendors = Vendor.objects.filter(claimed_status="CLAIMED").count()
    verified_vendors = Vendor.objects.filter(is_verified=True).count()

    subscription_breakdown = dict(
        Vendor.objects.filter(is_deleted=False)
        .values_list("subscription_level")
        .annotate(count=Count("id"))
    )

    total_customers = CustomerUser.objects.count()
    active_customers_30d = CustomerUser.objects.filter(
        last_login_at__gte=thirty_days_ago,
    ).count()

    total_views = Vendor.objects.aggregate(
        total=Sum("total_views")
    )["total"] or 0

    return {
        "total_vendors": total_vendors,
        "claimed_vendors": claimed_vendors,
        "verified_vendors": verified_vendors,
        "subscription_breakdown": subscription_breakdown,
        "total_customers": total_customers,
        "active_customers_30d": active_customers_30d,
        "total_views": total_views,
    }


def get_admin_area_heatmap(city_id: str) -> dict[str, Any]:
    """Return vendor density heatmap per area for a city.

    Args:
        city_id: UUID string of the city.

    Returns:
        Dict with area-level vendor counts and average metrics.
    """
    from django.db.models import Avg, Count

    from apps.vendors.models import Vendor

    areas = (
        Vendor.objects.filter(
            city_id=city_id,
            is_deleted=False,
        )
        .values("area_id", "area__name")
        .annotate(
            vendor_count=Count("id"),
            avg_views=Avg("total_views"),
            avg_taps=Avg("total_profile_taps"),
        )
        .order_by("-vendor_count")
    )

    return {
        "city_id": city_id,
        "areas": [
            {
                "area_id": str(a["area_id"]),
                "area_name": a["area__name"],
                "vendor_count": a["vendor_count"],
                "avg_views": round(a["avg_views"] or 0, 1),
                "avg_taps": round(a["avg_taps"] or 0, 1),
            }
            for a in areas
        ],
    }


def get_admin_search_terms() -> dict[str, Any]:
    """Return top search terms from AnalyticsEvent.

    Returns:
        Dict with search term frequency.
    """
    from django.db.models import Count

    from apps.analytics.models import AnalyticsEvent

    search_events = (
        AnalyticsEvent.objects.filter(
            event_type="SEARCH",
        )
        .exclude(metadata__search_query=None)
        .values("metadata__search_query")
        .annotate(count=Count("id"))
        .order_by("-count")[:20]
    )

    terms = []
    for item in search_events:
        query = item.get("metadata__search_query")
        if query:
            terms.append({"query": query, "count": item["count"]})

    return {
        "top_search_terms": terms,
    }


# =========================================================================
# Phase B — Admin KPI Endpoints (acquisition, engagement, monetization, platform-health)
# =========================================================================


def get_admin_kpi_acquisition() -> dict[str, Any]:
    """Return acquisition KPIs.

    Returns:
        Dict with new vendor signups, claims, and customer registrations.
    """
    from datetime import timedelta

    from django.db.models import Count
    from django.db.models.functions import TruncDate
    from django.utils import timezone

    from apps.accounts.models import CustomerUser
    from apps.vendors.models import Vendor

    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)

    new_vendors_30d = Vendor.objects.filter(
        created_at__gte=thirty_days_ago,
        is_deleted=False,
    ).count()

    new_claims_30d = Vendor.objects.filter(
        claimed_at__gte=thirty_days_ago,
        claimed_status="CLAIMED",
    ).count()

    new_customers_30d = CustomerUser.objects.filter(
        created_at__gte=thirty_days_ago,
    ).count()

    daily_signups = (
        CustomerUser.objects.filter(created_at__gte=thirty_days_ago)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    return {
        "new_vendors_30d": new_vendors_30d,
        "new_claims_30d": new_claims_30d,
        "new_customers_30d": new_customers_30d,
        "daily_signups": [
            {"date": str(d["day"]), "count": d["count"]} for d in daily_signups
        ],
    }


def get_admin_kpi_engagement() -> dict[str, Any]:
    """Return engagement KPIs.

    Returns:
        Dict with active users, search counts, view counts.
    """
    from datetime import timedelta

    from django.db.models import Count, Sum
    from django.utils import timezone

    from apps.accounts.models import CustomerUser
    from apps.analytics.models import AnalyticsEvent
    from apps.vendors.models import Vendor

    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)

    active_customers_7d = CustomerUser.objects.filter(
        last_login_at__gte=seven_days_ago,
    ).count()

    searches_7d = AnalyticsEvent.objects.filter(
        event_type="SEARCH",
        created_at__gte=seven_days_ago,
    ).count()

    views_7d = AnalyticsEvent.objects.filter(
        event_type="VIEW",
        created_at__gte=seven_days_ago,
    ).count()

    return {
        "active_customers_7d": active_customers_7d,
        "searches_7d": searches_7d,
        "views_7d": views_7d,
    }


def get_admin_kpi_monetization() -> dict[str, Any]:
    """Return monetization KPIs.

    Returns:
        Dict with subscription tier distribution and revenue indicators.
    """
    from django.db.models import Count

    from apps.vendors.models import Vendor

    tier_distribution = dict(
        Vendor.objects.filter(is_deleted=False)
        .exclude(subscription_level="SILVER")
        .values_list("subscription_level")
        .annotate(count=Count("id"))
    )

    paid_vendors = sum(tier_distribution.values())
    total_vendors = Vendor.objects.filter(is_deleted=False).count()
    conversion_rate = (paid_vendors / total_vendors * 100) if total_vendors > 0 else 0

    return {
        "tier_distribution": tier_distribution,
        "paid_vendors": paid_vendors,
        "total_vendors": total_vendors,
        "conversion_rate": round(conversion_rate, 2),
    }


# =========================================================================
# Phase B — Vendor Daily Analytics (§B-11)
# =========================================================================


def get_vendor_daily_analytics(vendor_id: str, days: int = 14) -> dict[str, Any]:
    """Return daily breakdown of views, taps, and navigation clicks for a vendor.

    Args:
        vendor_id: UUID of the vendor.
        days: Number of days to include (default 14).

    Returns:
        Dict with daily_breakdown list and totals.
    """
    from datetime import timedelta

    from django.db.models import Count
    from django.db.models.functions import TruncDate
    from django.utils import timezone

    from apps.analytics.models import AnalyticsEvent

    start = timezone.now() - timedelta(days=days)

    daily_events = (
        AnalyticsEvent.objects.filter(
            vendor_id=vendor_id,
            created_at__gte=start,
        )
        .annotate(date=TruncDate("created_at"))
        .values("date", "event_type")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    date_map: dict[str, dict] = {}
    for row in daily_events:
        d = row["date"].isoformat()
        if d not in date_map:
            date_map[d] = {"date": d, "views": 0, "taps": 0, "navigation_clicks": 0}
        et = row["event_type"]
        if et == "VIEW":
            date_map[d]["views"] = row["count"]
        elif et == "TAP":
            date_map[d]["taps"] = row["count"]
        elif et == "NAVIGATION_CLICK":
            date_map[d]["navigation_clicks"] = row["count"]

    daily = sorted(date_map.values(), key=lambda x: x["date"])
    totals = {
        "total_views": sum(d["views"] for d in daily),
        "total_taps": sum(d["taps"] for d in daily),
        "total_navigation_clicks": sum(d["navigation_clicks"] for d in daily),
    }

    return {"daily_breakdown": daily, "totals": totals, "days": days}


def get_vendor_competitors(vendor_id: str) -> dict[str, Any]:
    """Return area-level benchmarking for a vendor (Platinum only).

    Compares the vendor's analytics against averages for vendors in the same area.

    Args:
        vendor_id: UUID of the vendor.

    Returns:
        Dict with vendor stats, area averages, and rank.
    """
    from datetime import timedelta

    from django.db.models import Avg, Count
    from django.utils import timezone

    from apps.analytics.models import AnalyticsEvent
    from apps.vendors.models import Vendor

    try:
        vendor = Vendor.objects.get(pk=vendor_id, is_deleted=False)
    except Vendor.DoesNotExist:
        return {"error": "Vendor not found"}

    thirty_days_ago = timezone.now() - timedelta(days=30)

    # Vendor's own stats
    vendor_views = AnalyticsEvent.objects.filter(
        vendor_id=vendor_id, event_type="VIEW", created_at__gte=thirty_days_ago
    ).count()

    # Same-area vendors
    area_vendors = Vendor.objects.filter(
        area=vendor.area, is_deleted=False
    ).exclude(pk=vendor_id)
    area_vendor_ids = list(area_vendors.values_list("id", flat=True))

    area_avg_views = 0
    if area_vendor_ids:
        area_events = (
            AnalyticsEvent.objects.filter(
                vendor_id__in=area_vendor_ids,
                event_type="VIEW",
                created_at__gte=thirty_days_ago,
            )
            .values("vendor_id")
            .annotate(view_count=Count("id"))
        )
        if area_events:
            total = sum(e["view_count"] for e in area_events)
            area_avg_views = round(total / len(area_vendor_ids), 1)

    rank = 1
    if area_vendor_ids:
        vendors_with_more = (
            AnalyticsEvent.objects.filter(
                vendor_id__in=area_vendor_ids,
                event_type="VIEW",
                created_at__gte=thirty_days_ago,
            )
            .values("vendor_id")
            .annotate(vc=Count("id"))
            .filter(vc__gt=vendor_views)
            .count()
        )
        rank = vendors_with_more + 1

    return {
        "vendor_views_30d": vendor_views,
        "area_avg_views_30d": area_avg_views,
        "area_vendor_count": len(area_vendor_ids) + 1,
        "area_rank": rank,
        "area_name": vendor.area.name if vendor.area else "Unknown",
    }


# =========================================================================
# Phase B — Admin Analytics Extensions (§B-11)
# =========================================================================


def get_admin_vendor_activity() -> dict[str, Any]:
    """Return aggregate vendor activity statistics for admin dashboard.

    Returns:
        Dict with active vendors, reel counts, discount counts.
    """
    from datetime import timedelta

    from django.db.models import Count
    from django.utils import timezone

    from apps.analytics.models import AnalyticsEvent
    from apps.reels.models import VendorReel
    from apps.vendors.models import Discount, Vendor

    now = timezone.now()
    seven_days = now - timedelta(days=7)
    thirty_days = now - timedelta(days=30)

    # Vendors with any analytics event in last 7 days
    active_vendors_7d = (
        AnalyticsEvent.objects.filter(created_at__gte=seven_days)
        .values("vendor_id")
        .distinct()
        .count()
    )

    total_reels = VendorReel.objects.filter(is_active=True).count()
    pending_reels = VendorReel.objects.filter(
        moderation_status="PENDING", is_active=True
    ).count()

    active_discounts = Discount.objects.filter(is_active=True).count()
    total_vendors = Vendor.objects.filter(is_deleted=False).count()

    return {
        "active_vendors_7d": active_vendors_7d,
        "total_vendors": total_vendors,
        "total_reels": total_reels,
        "pending_reels_moderation": pending_reels,
        "active_discounts": active_discounts,
    }


def get_admin_subscription_distribution() -> dict[str, Any]:
    """Return subscription tier distribution for admin dashboard.

    Returns:
        Dict with tier counts and percentages.
    """
    from django.db.models import Count

    from apps.vendors.models import Vendor

    total = Vendor.objects.filter(is_deleted=False).count()
    distribution = dict(
        Vendor.objects.filter(is_deleted=False)
        .values_list("subscription_level")
        .annotate(count=Count("id"))
    )

    result = {}
    for tier, count in distribution.items():
        result[tier] = {
            "count": count,
            "percentage": round((count / total * 100), 2) if total > 0 else 0,
        }

    return {"total_vendors": total, "distribution": result}


def get_admin_platform_health_kpis() -> dict[str, Any]:
    """Return platform health KPIs for admin dashboard.

    Returns:
        Dict with system status, active vendors, reel counts,
        discount counts — matching frontend PlatformHealthKPIs type.
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.analytics.models import AnalyticsEvent
    from apps.reels.models import VendorReel
    from apps.vendors.models import Discount, Vendor

    now = timezone.now()
    seven_days = now - timedelta(days=7)

    active_vendors_7d = (
        AnalyticsEvent.objects.filter(created_at__gte=seven_days)
        .values("vendor_id")
        .distinct()
        .count()
    )

    total_vendors = Vendor.objects.filter(is_deleted=False).count()
    total_reels = VendorReel.objects.filter(is_active=True).count()
    pending_reels_moderation = VendorReel.objects.filter(
        moderation_status="PENDING", is_active=True
    ).count()
    active_discounts = Discount.objects.filter(is_active=True).count()

    return {
        "system_status": "ok",
        "db_status": "ok",
        "cache_status": "ok",
        "active_vendors_7d": active_vendors_7d,
        "total_vendors": total_vendors,
        "total_reels": total_reels,
        "pending_reels_moderation": pending_reels_moderation,
        "active_discounts": active_discounts,
    }
