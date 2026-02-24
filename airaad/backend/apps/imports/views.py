"""
AirAd Backend — Imports Views

Zero business logic — all delegated to imports/services.py (R4).
Every view uses RolePermission.for_roles() (R3).
CSV never passed over broker — only batch_id (R8).
"""

import logging

from apps.accounts.models import AdminRole
from apps.accounts.permissions import RolePermission
from core.exceptions import success_response
from core.pagination import StandardResultsPagination
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ImportBatch
from .serializers import CreateImportBatchSerializer, ImportBatchSerializer
from .services import create_import_batch, get_batch_or_404

logger = logging.getLogger(__name__)


class ImportBatchListCreateView(APIView):
    """List import batches or upload a new CSV."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.DATA_ENTRY,
            AdminRole.OPERATIONS_MANAGER,
        )
    ]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["Imports"],
        summary="List import batches",
        responses={200: ImportBatchSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Return paginated list of import batches for the current user.

        SUPER_ADMIN sees all batches; other roles see only their own.
        Optional query param: ?import_type=CSV|GOOGLE_PLACES|GOOGLE_PLACES_ENHANCED

        Args:
            request: Authenticated HTTP request.

        Returns:
            Paginated list of ImportBatch records.
        """
        if request.user.role == AdminRole.SUPER_ADMIN:
            qs = ImportBatch.objects.select_related("created_by", "area").order_by(
                "-created_at"
            )
        else:
            qs = (
                ImportBatch.objects.filter(created_by=request.user)
                .select_related("created_by", "area")
                .order_by("-created_at")
            )

        # Server-side import_type filter
        import_type = request.query_params.get("import_type")
        if import_type:
            qs = qs.filter(import_type=import_type)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            ImportBatchSerializer(page, many=True).data
        )

    @extend_schema(
        tags=["Imports"],
        summary="Upload CSV for import (SUPER_ADMIN, CITY_MANAGER, DATA_ENTRY)",
        request=CreateImportBatchSerializer,
        responses={
            201: ImportBatchSerializer,
            400: OpenApiResponse(description="Invalid file or validation error"),
        },
    )
    def post(self, request: Request) -> Response:
        """Upload a CSV file, store in S3, dispatch Celery task with batch_id only (R8).

        Args:
            request: Multipart HTTP request with CSV file.

        Returns:
            201 with ImportBatch data on success.
        """
        serializer = CreateImportBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]

        try:
            batch = create_import_batch(
                file=uploaded_file,
                filename=uploaded_file.name,
                actor=request.user,
                request=request._request,
            )
        except Exception as e:
            logger.error("Import batch creation failed", extra={"error": str(e)})
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            data=ImportBatchSerializer(batch).data,
            message="Import batch queued successfully",
            status_code=status.HTTP_201_CREATED,
        )


class ImportBatchDetailView(APIView):
    """Retrieve a single import batch by ID."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.DATA_ENTRY,
            AdminRole.OPERATIONS_MANAGER,
        )
    ]

    @extend_schema(
        tags=["Imports"],
        summary="Get import batch detail",
        responses={
            200: ImportBatchSerializer,
            404: OpenApiResponse(description="Not found"),
        },
    )
    def get(self, request: Request, pk: str) -> Response:
        """Return a single ImportBatch by ID.

        Args:
            request: Authenticated HTTP request.
            pk: ImportBatch UUID.

        Returns:
            200 with batch data, 404 if not found.
        """
        try:
            batch = get_batch_or_404(batch_id=pk, actor=request.user)
        except ImportBatch.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Import batch not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=ImportBatchSerializer(batch).data)
