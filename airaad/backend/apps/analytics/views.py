"""
AirAd Backend — Analytics Views

Zero business logic — all delegated to analytics/services.py (R4).
Every view uses RolePermission.for_roles() (R3).
Analytics recording is fire-and-forget — API response never waits for write.

Phase B adds:
- Vendor analytics endpoints (summary, reels, discounts, time-heatmap, recommendations)
- Admin platform analytics (platform-overview, area-heatmap, search-terms)
- Admin KPI endpoints (acquisition, engagement, monetization)
"""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.accounts.authentication import CustomerUserJWTAuthentication
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import AdminRole
from apps.accounts.permissions import RolePermission
from core.exceptions import success_response

from .services import (
    get_admin_area_heatmap,
    get_admin_kpi_acquisition,
    get_admin_kpi_engagement,
    get_admin_kpi_monetization,
    get_admin_platform_health_kpis,
    get_admin_platform_overview,
    get_admin_search_terms,
    get_admin_subscription_distribution,
    get_admin_vendor_activity,
    get_platform_kpis,
    get_vendor_analytics_discounts,
    get_vendor_analytics_reels,
    get_vendor_analytics_summary,
    get_vendor_competitors,
    get_vendor_daily_analytics,
    get_vendor_recommendations,
    get_vendor_time_heatmap,
)

logger = logging.getLogger(__name__)


class PlatformKPIView(APIView):
    """Return basic platform KPI counts. SUPER_ADMIN, CITY_MANAGER and ANALYST only."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.ANALYST,
            AdminRole.OPERATIONS_MANAGER,
            AdminRole.ANALYTICS_OBSERVER,
            AdminRole.DATA_QUALITY_ANALYST,
        )
    ]

    @extend_schema(
        tags=["Analytics"],
        summary="Platform KPI summary (SUPER_ADMIN, CITY_MANAGER, ANALYST)",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request) -> Response:
        """Return vendor counts and import batch totals.

        Args:
            request: Authenticated HTTP request.

        Returns:
            200 with KPI dict.
        """
        return success_response(data=get_platform_kpis())


# =========================================================================
# Phase B — Vendor Analytics Views (§3.6)
# =========================================================================


class VendorAnalyticsSummaryView(APIView):
    """GET /api/v1/vendors/{id}/analytics/summary/ — vendor analytics summary."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Analytics"],
        summary="Vendor analytics summary (owner or admin)",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request, vendor_id: str) -> Response:
        """Return analytics summary for a vendor.

        Args:
            request: Authenticated HTTP request.
            vendor_id: UUID of the vendor.

        Returns:
            200 with analytics summary.
        """
        try:
            data = get_vendor_analytics_summary(vendor_id)
        except Exception as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=data)


class VendorAnalyticsReelsView(APIView):
    """GET /api/v1/vendors/{id}/analytics/reels/ — reel analytics."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Analytics"],
        summary="Vendor reel analytics",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request, vendor_id: str) -> Response:
        """Return reel/video analytics for a vendor.

        Args:
            request: Authenticated HTTP request.
            vendor_id: UUID of the vendor.

        Returns:
            200 with reel analytics.
        """
        data = get_vendor_analytics_reels(vendor_id)
        return success_response(data=data)


class VendorAnalyticsDiscountsView(APIView):
    """GET /api/v1/vendors/{id}/analytics/discounts/ — discount analytics."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Analytics"],
        summary="Vendor discount performance analytics",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request, vendor_id: str) -> Response:
        """Return discount performance analytics for a vendor.

        Args:
            request: Authenticated HTTP request.
            vendor_id: UUID of the vendor.

        Returns:
            200 with discount analytics.
        """
        data = get_vendor_analytics_discounts(vendor_id)
        return success_response(data=data)


class VendorAnalyticsTimeHeatmapView(APIView):
    """GET /api/v1/vendors/{id}/analytics/time-heatmap/ — Gold+ only."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Analytics"],
        summary="Vendor time heatmap (Gold+ tier)",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request, vendor_id: str) -> Response:
        """Return hourly view heatmap for a vendor.

        Requires Gold+ subscription tier via vendor_has_feature gate.

        Args:
            request: Authenticated HTTP request.
            vendor_id: UUID of the vendor.

        Returns:
            200 with hourly heatmap data, or 403 if tier insufficient.
        """
        from apps.vendors.models import Vendor
        from core.utils import vendor_has_feature

        try:
            vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
        except Vendor.DoesNotExist:
            return Response(
                {"success": False, "data": None, "message": "Vendor not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not vendor_has_feature(vendor, "TIME_HEATMAP"):
            return Response(
                {"success": False, "data": None, "message": "Time heatmap requires Gold+ subscription", "errors": {}},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = get_vendor_time_heatmap(vendor_id)
        return success_response(data=data)


class VendorAnalyticsRecommendationsView(APIView):
    """GET /api/v1/vendors/{id}/analytics/recommendations/ — Platinum only."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Analytics"],
        summary="Vendor recommendations (Platinum only, rule-based)",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request, vendor_id: str) -> Response:
        """Return rule-based recommendations for a vendor.

        Requires Platinum subscription tier.

        Args:
            request: Authenticated HTTP request.
            vendor_id: UUID of the vendor.

        Returns:
            200 with recommendations, or 403 if tier insufficient.
        """
        from apps.vendors.models import Vendor
        from core.utils import vendor_has_feature

        try:
            vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
        except Vendor.DoesNotExist:
            return Response(
                {"success": False, "data": None, "message": "Vendor not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not vendor_has_feature(vendor, "PREDICTIVE_RECOMMENDATIONS"):
            return Response(
                {"success": False, "data": None, "message": "Recommendations require Platinum subscription", "errors": {}},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = get_vendor_recommendations(vendor_id)
        return success_response(data=data)


# =========================================================================
# Phase B — Admin Analytics Views (§3.6)
# =========================================================================


class AdminPlatformOverviewView(APIView):
    """GET /api/v1/admin/analytics/platform-overview/ — admin platform overview."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.ANALYST,
            AdminRole.ANALYTICS_OBSERVER,
        )
    ]

    @extend_schema(
        tags=["Admin Analytics"],
        summary="Admin platform overview analytics",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request) -> Response:
        """Return platform-wide analytics overview.

        Args:
            request: Authenticated admin HTTP request.

        Returns:
            200 with platform overview data.
        """
        return success_response(data=get_admin_platform_overview())


class AdminAreaHeatmapView(APIView):
    """GET /api/v1/admin/analytics/area-heatmap/{city_id}/ — area heatmap."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.ANALYST,
            AdminRole.ANALYTICS_OBSERVER,
        )
    ]

    @extend_schema(
        tags=["Admin Analytics"],
        summary="Admin area heatmap for a city",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request, city_id: str) -> Response:
        """Return vendor density heatmap per area for a city.

        Args:
            request: Authenticated admin HTTP request.
            city_id: UUID of the city.

        Returns:
            200 with area heatmap data.
        """
        return success_response(data=get_admin_area_heatmap(city_id))


class AdminSearchTermsView(APIView):
    """GET /api/v1/admin/analytics/search-terms/ — top search terms."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.ANALYST,
            AdminRole.ANALYTICS_OBSERVER,
        )
    ]

    @extend_schema(
        tags=["Admin Analytics"],
        summary="Top search terms",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request) -> Response:
        """Return top search terms from analytics events.

        Args:
            request: Authenticated admin HTTP request.

        Returns:
            200 with top search terms.
        """
        return success_response(data=get_admin_search_terms())


class AdminKPIAcquisitionView(APIView):
    """GET /api/v1/admin/analytics/kpi/acquisition/ — acquisition KPIs."""

    permission_classes = [
        RolePermission.for_roles(AdminRole.SUPER_ADMIN, AdminRole.ANALYST)
    ]

    @extend_schema(
        tags=["Admin Analytics"],
        summary="Acquisition KPIs",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request) -> Response:
        """Return acquisition KPIs."""
        return success_response(data=get_admin_kpi_acquisition())


class AdminKPIEngagementView(APIView):
    """GET /api/v1/admin/analytics/kpi/engagement/ — engagement KPIs."""

    permission_classes = [
        RolePermission.for_roles(AdminRole.SUPER_ADMIN, AdminRole.ANALYST)
    ]

    @extend_schema(
        tags=["Admin Analytics"],
        summary="Engagement KPIs",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request) -> Response:
        """Return engagement KPIs."""
        return success_response(data=get_admin_kpi_engagement())


class AdminKPIMonetizationView(APIView):
    """GET /api/v1/admin/analytics/kpi/monetization/ — monetization KPIs."""

    permission_classes = [
        RolePermission.for_roles(AdminRole.SUPER_ADMIN, AdminRole.ANALYST)
    ]

    @extend_schema(
        tags=["Admin Analytics"],
        summary="Monetization KPIs",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request) -> Response:
        """Return monetization KPIs."""
        return success_response(data=get_admin_kpi_monetization())


# =========================================================================
# Phase B — Vendor Daily Analytics (§B-11)
# =========================================================================


class VendorAnalyticsDailyView(APIView):
    """GET /api/v1/analytics/vendors/{id}/daily/ — daily breakdown (Gold+ tier-gated)."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Analytics"],
        summary="Vendor daily analytics breakdown (Gold+ tier)",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request, vendor_id: str) -> Response:
        """Return daily breakdown of views/taps/nav clicks for a vendor.

        Requires Gold+ subscription tier.
        """
        from apps.vendors.models import Vendor
        from core.utils import vendor_has_feature

        try:
            vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
        except Vendor.DoesNotExist:
            return Response(
                {"success": False, "data": None, "message": "Vendor not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not vendor_has_feature(vendor, "HOURLY_ANALYTICS"):
            return Response(
                {"success": False, "data": None, "message": "Daily analytics requires Gold+ subscription", "errors": {}},
                status=status.HTTP_403_FORBIDDEN,
            )

        days = int(request.query_params.get("days", 14))
        data = get_vendor_daily_analytics(vendor_id, days=min(days, 90))
        return success_response(data=data)


class VendorAnalyticsCompetitorsView(APIView):
    """GET /api/v1/analytics/vendors/{id}/competitors/ — area benchmarking (Platinum only)."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Analytics"],
        summary="Vendor competitor benchmarking (Platinum only)",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request, vendor_id: str) -> Response:
        """Return area-level benchmarking for a vendor.

        Requires Platinum subscription tier.
        """
        from apps.vendors.models import Vendor
        from core.utils import vendor_has_feature

        try:
            vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
        except Vendor.DoesNotExist:
            return Response(
                {"success": False, "data": None, "message": "Vendor not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not vendor_has_feature(vendor, "COMPETITOR_BENCHMARKING"):
            return Response(
                {"success": False, "data": None, "message": "Competitor benchmarking requires Platinum subscription", "errors": {}},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = get_vendor_competitors(vendor_id)
        return success_response(data=data)


# =========================================================================
# Phase B — Admin Analytics Extensions (§B-11)
# =========================================================================


class AdminVendorActivityView(APIView):
    """GET /api/v1/admin/analytics/vendor-activity/ — vendor activity stats."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN, AdminRole.ANALYST, AdminRole.ANALYTICS_OBSERVER
        )
    ]

    @extend_schema(
        tags=["Admin Analytics"],
        summary="Admin vendor activity statistics",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request) -> Response:
        """Return aggregate vendor activity statistics."""
        return success_response(data=get_admin_vendor_activity())


class AdminSubscriptionDistributionView(APIView):
    """GET /api/v1/admin/analytics/subscription-distribution/ — tier distribution."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN, AdminRole.ANALYST, AdminRole.ANALYTICS_OBSERVER
        )
    ]

    @extend_schema(
        tags=["Admin Analytics"],
        summary="Admin subscription tier distribution",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request) -> Response:
        """Return subscription tier distribution."""
        return success_response(data=get_admin_subscription_distribution())


class AdminKPIPlatformHealthView(APIView):
    """GET /api/v1/admin/analytics/kpi/platform-health/ — platform health KPIs."""

    permission_classes = [
        RolePermission.for_roles(AdminRole.SUPER_ADMIN, AdminRole.ANALYST)
    ]

    @extend_schema(
        tags=["Admin Analytics"],
        summary="Platform health KPIs",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request) -> Response:
        """Return platform health KPIs."""
        return success_response(data=get_admin_platform_health_kpis())
