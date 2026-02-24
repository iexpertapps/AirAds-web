"""
AirAd Backend — Field Ops Views

Zero business logic — all delegated to field_ops/services.py (R4).
Every view uses RolePermission.for_roles() (R3).
FieldPhoto.s3_key is never exposed directly — presigned URL returned instead.
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

from .models import FieldPhoto, FieldVisit
from .serializers import (
    CreateFieldVisitSerializer,
    FieldPhotoSerializer,
    FieldVisitSerializer,
    UploadFieldPhotoSerializer,
)
from .services import create_field_visit, upload_field_photo

logger = logging.getLogger(__name__)


class FieldVisitListCreateView(APIView):
    """List field visits or create a new one."""

    _read_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN,
        AdminRole.CITY_MANAGER,
        AdminRole.FIELD_AGENT,
        AdminRole.QA_REVIEWER,
        AdminRole.DATA_ENTRY,
    )
    _write_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN,
        AdminRole.CITY_MANAGER,
        AdminRole.FIELD_AGENT,
    )

    def get_permissions(self) -> list:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [self._read_roles()]
        return [self._write_roles()]

    @extend_schema(
        tags=["Field Ops"],
        summary="List field visits",
        responses={200: FieldVisitSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Return paginated list of field visits.

        FIELD_AGENT sees only their own visits. Other roles see all.

        Args:
            request: Authenticated HTTP request.

        Returns:
            Paginated list of FieldVisit records.
        """
        qs = FieldVisit.objects.select_related("vendor", "agent").order_by(
            "-visited_at"
        )

        if request.user.role == AdminRole.FIELD_AGENT:
            qs = qs.filter(agent=request.user)

        vendor_id = request.query_params.get("vendor_id")
        if vendor_id:
            qs = qs.filter(vendor_id=vendor_id)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            FieldVisitSerializer(page, many=True).data
        )

    @extend_schema(
        tags=["Field Ops"],
        summary="Create field visit (SUPER_ADMIN, CITY_MANAGER, FIELD_AGENT)",
        request=CreateFieldVisitSerializer,
        responses={201: FieldVisitSerializer},
    )
    def post(self, request: Request) -> Response:
        """Record a new field visit. Agent is set to the requesting user.

        Args:
            request: HTTP request with visit data.

        Returns:
            201 with FieldVisit data on success.
        """
        serializer = CreateFieldVisitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            visit = create_field_visit(
                vendor_id=str(d["vendor_id"]),
                agent=request.user,
                request=request._request,
                visited_at=d.get("visited_at"),
                visit_notes=d.get("visit_notes", ""),
                gps_lon=d.get("longitude"),
                gps_lat=d.get("latitude"),
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            data=FieldVisitSerializer(visit).data,
            message="Field visit recorded",
            status_code=status.HTTP_201_CREATED,
        )


class FieldVisitDetailView(APIView):
    """Retrieve a single field visit."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.FIELD_AGENT,
            AdminRole.QA_REVIEWER,
        )
    ]

    @extend_schema(
        tags=["Field Ops"],
        summary="Get field visit detail",
        responses={200: FieldVisitSerializer},
    )
    def get(self, request: Request, pk: str) -> Response:
        """Return a single FieldVisit by ID.

        Args:
            request: Authenticated HTTP request.
            pk: FieldVisit UUID.

        Returns:
            200 with visit data, 404 if not found.
        """
        try:
            visit = FieldVisit.objects.select_related("vendor", "agent").get(id=pk)
        except FieldVisit.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Field visit not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=FieldVisitSerializer(visit).data)


class FieldPhotoUploadView(APIView):
    """Upload a photo for a field visit."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.FIELD_AGENT,
        )
    ]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["Field Ops"],
        summary="Upload field photo (SUPER_ADMIN, FIELD_AGENT)",
        request=UploadFieldPhotoSerializer,
        responses={
            201: FieldPhotoSerializer,
            404: OpenApiResponse(description="Field visit not found"),
        },
    )
    def post(self, request: Request, visit_pk: str) -> Response:
        """Upload a photo for a field visit. Stores S3 key only — returns presigned URL.

        Args:
            request: Multipart HTTP request with photo file.
            visit_pk: FieldVisit UUID.

        Returns:
            201 with FieldPhoto data including presigned URL.
        """
        try:
            visit = FieldVisit.objects.get(id=visit_pk)
        except FieldVisit.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Field visit not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UploadFieldPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            photo = upload_field_photo(
                visit=visit,
                file=serializer.validated_data["file"],
                actor=request.user,
                request=request._request,
                caption=serializer.validated_data.get("caption", ""),
            )
        except Exception as e:
            logger.error(
                "Photo upload failed", extra={"visit_id": visit_pk, "error": str(e)}
            )
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            data=FieldPhotoSerializer(photo).data,
            message="Photo uploaded successfully",
            status_code=status.HTTP_201_CREATED,
        )


class FieldPhotoListView(APIView):
    """List photos for a field visit."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.FIELD_AGENT,
            AdminRole.QA_REVIEWER,
        )
    ]

    @extend_schema(
        tags=["Field Ops"],
        summary="List photos for a field visit",
        responses={200: FieldPhotoSerializer(many=True)},
    )
    def get(self, request: Request, visit_pk: str) -> Response:
        """Return all active photos for a field visit.

        Args:
            request: Authenticated HTTP request.
            visit_pk: FieldVisit UUID.

        Returns:
            200 with list of FieldPhoto records including presigned URLs.
        """
        try:
            visit = FieldVisit.objects.get(id=visit_pk)
        except FieldVisit.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Field visit not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        photos = FieldPhoto.objects.filter(field_visit=visit, is_active=True).order_by(
            "-uploaded_at"
        )
        return success_response(data=FieldPhotoSerializer(photos, many=True).data)
