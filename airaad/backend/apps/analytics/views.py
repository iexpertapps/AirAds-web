"""
AirAd Backend — Analytics Views

Zero business logic — all delegated to analytics/services.py (R4).
Every view uses RolePermission.for_roles() (R3).
Analytics recording is fire-and-forget — API response never waits for write.
"""

import logging

from apps.accounts.models import AdminRole
from apps.accounts.permissions import RolePermission
from core.exceptions import success_response
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import get_platform_kpis

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
