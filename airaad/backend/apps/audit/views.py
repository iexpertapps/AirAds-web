"""
AirAd Backend — Audit Views

Read-only AuditLog list. SUPER_ADMIN and ANALYST roles only.
Zero business logic — all filtering delegated to queryset.
"""

import logging

from apps.accounts.models import AdminRole
from apps.accounts.permissions import RolePermission
from core.pagination import StandardResultsPagination
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import ListAPIView

from .models import AuditLog
from .serializers import AuditLogSerializer

logger = logging.getLogger(__name__)


class AuditLogListView(ListAPIView):
    """Read-only list of AuditLog entries. SUPER_ADMIN and ANALYST only.

    Supports filtering by action, actor email, target_type, and date range
    via query parameters.
    """

    serializer_class = AuditLogSerializer
    pagination_class = StandardResultsPagination
    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.ANALYST,
            AdminRole.OPERATIONS_MANAGER,
        )
    ]

    @extend_schema(
        tags=["Audit"],
        summary="List audit log entries (SUPER_ADMIN, ANALYST)",
        parameters=[
            OpenApiParameter(
                name="action",
                description="Filter by action code",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="target_type",
                description="Filter by target model name",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="actor_label",
                description="Filter by actor email",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="date_from",
                description="Filter entries on or after this date (YYYY-MM-DD)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="date_to",
                description="Filter entries on or before this date (YYYY-MM-DD)",
                required=False,
                type=str,
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        """List audit log entries with optional filters.

        Args:
            request: Authenticated HTTP request.

        Returns:
            Paginated list of AuditLog entries.
        """
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        """Return filtered AuditLog queryset.

        Returns:
            QuerySet filtered by any provided query parameters.
        """
        qs = AuditLog.objects.select_related("actor").all()

        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)

        target_type = self.request.query_params.get("target_type")
        if target_type:
            qs = qs.filter(target_type=target_type)

        actor_label = self.request.query_params.get("actor_label")
        if actor_label:
            qs = qs.filter(actor_label__icontains=actor_label)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return qs
