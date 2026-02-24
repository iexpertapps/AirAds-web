"""
AirAd Backend — QA Views

Zero business logic — all delegated to qa/services.py (R4).
Every view uses RolePermission.for_roles() (R3).
GPS drift and duplicate detection triggered via Celery tasks (A-S6).
"""

import logging

from apps.accounts.models import AdminRole
from apps.accounts.permissions import RolePermission
from core.exceptions import success_response
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class QADashboardView(APIView):
    """Return vendors flagged as NEEDS_REVIEW. QA_REVIEWER and above."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.QA_REVIEWER,
        )
    ]

    @extend_schema(
        tags=["QA"],
        summary="List vendors flagged NEEDS_REVIEW (SUPER_ADMIN, CITY_MANAGER, QA_REVIEWER)",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request) -> Response:
        """Return count and IDs of vendors with qc_status=NEEDS_REVIEW.

        Args:
            request: Authenticated HTTP request.

        Returns:
            200 with flagged vendor summary.
        """
        from apps.vendors.models import QCStatus, Vendor

        flagged = (
            Vendor.objects.filter(qc_status=QCStatus.NEEDS_REVIEW)
            .values("id", "business_name", "qc_notes", "updated_at")
            .order_by("-updated_at")
        )
        return success_response(
            data={
                "count": flagged.count(),
                "vendors": list(flagged[:100]),
            }
        )
