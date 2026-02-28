"""
AirAd Backend — Analytics URL Configuration
Mounted at: /api/v1/analytics/

Phase A: Platform KPIs for admin dashboard.
Phase B: Vendor analytics + Admin analytics (§3.6).
"""

from django.urls import path

from .views import (
    AdminAreaHeatmapView,
    AdminKPIAcquisitionView,
    AdminKPIEngagementView,
    AdminKPIMonetizationView,
    AdminKPIPlatformHealthView,
    AdminPlatformOverviewView,
    AdminSearchTermsView,
    AdminSubscriptionDistributionView,
    AdminVendorActivityView,
    PlatformKPIView,
    VendorAnalyticsCompetitorsView,
    VendorAnalyticsDailyView,
    VendorAnalyticsDiscountsView,
    VendorAnalyticsRecommendationsView,
    VendorAnalyticsReelsView,
    VendorAnalyticsSummaryView,
    VendorAnalyticsTimeHeatmapView,
)

urlpatterns = [
    # --- Phase A ---
    path("kpis/", PlatformKPIView.as_view(), name="analytics-kpis"),
    # --- Phase B — Vendor Analytics (§3.6) ---
    path(
        "vendors/<str:vendor_id>/summary/",
        VendorAnalyticsSummaryView.as_view(),
        name="vendor-analytics-summary",
    ),
    path(
        "vendors/<str:vendor_id>/reels/",
        VendorAnalyticsReelsView.as_view(),
        name="vendor-analytics-reels",
    ),
    path(
        "vendors/<str:vendor_id>/discounts/",
        VendorAnalyticsDiscountsView.as_view(),
        name="vendor-analytics-discounts",
    ),
    path(
        "vendors/<str:vendor_id>/time-heatmap/",
        VendorAnalyticsTimeHeatmapView.as_view(),
        name="vendor-analytics-time-heatmap",
    ),
    path(
        "vendors/<str:vendor_id>/recommendations/",
        VendorAnalyticsRecommendationsView.as_view(),
        name="vendor-analytics-recommendations",
    ),
    # --- Phase B — Admin Analytics (§3.6) ---
    path(
        "admin/platform-overview/",
        AdminPlatformOverviewView.as_view(),
        name="admin-analytics-platform-overview",
    ),
    path(
        "admin/area-heatmap/<str:city_id>/",
        AdminAreaHeatmapView.as_view(),
        name="admin-analytics-area-heatmap",
    ),
    path(
        "admin/search-terms/",
        AdminSearchTermsView.as_view(),
        name="admin-analytics-search-terms",
    ),
    path(
        "admin/kpi/acquisition/",
        AdminKPIAcquisitionView.as_view(),
        name="admin-kpi-acquisition",
    ),
    path(
        "admin/kpi/engagement/",
        AdminKPIEngagementView.as_view(),
        name="admin-kpi-engagement",
    ),
    path(
        "admin/kpi/monetization/",
        AdminKPIMonetizationView.as_view(),
        name="admin-kpi-monetization",
    ),
    # --- Phase B — Vendor Daily & Competitors (§B-11) ---
    path(
        "vendors/<str:vendor_id>/daily/",
        VendorAnalyticsDailyView.as_view(),
        name="vendor-analytics-daily",
    ),
    path(
        "vendors/<str:vendor_id>/competitors/",
        VendorAnalyticsCompetitorsView.as_view(),
        name="vendor-analytics-competitors",
    ),
    # --- Phase B — Admin Extensions (§B-11) ---
    path(
        "admin/vendor-activity/",
        AdminVendorActivityView.as_view(),
        name="admin-analytics-vendor-activity",
    ),
    path(
        "admin/subscription-distribution/",
        AdminSubscriptionDistributionView.as_view(),
        name="admin-analytics-subscription-distribution",
    ),
    path(
        "admin/kpi/platform-health/",
        AdminKPIPlatformHealthView.as_view(),
        name="admin-kpi-platform-health",
    ),
]
