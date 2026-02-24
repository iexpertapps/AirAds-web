"""
AirAd Backend — Vendors Views

Zero business logic — all delegated to vendors/services.py (R4).
Every view uses RolePermission.for_roles() (R3).
get_queryset() always filters is_deleted=False via ActiveVendorManager.
All views decorated with @extend_schema.
"""

import logging

from apps.accounts.models import AdminRole
from apps.accounts.permissions import RolePermission
from core.exceptions import success_response
from core.pagination import StandardResultsPagination
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Vendor
from .serializers import (
    AssignTagSerializer,
    CreateVendorSerializer,
    QCStatusUpdateSerializer,
    UpdateVendorSerializer,
    VendorListSerializer,
    VendorPhotoSerializer,
    VendorSerializer,
    VendorTagSerializer,
    VendorVisitSerializer,
)
from .services import (
    assign_vendor_tag,
    create_vendor,
    get_vendor_analytics_stub,
    get_vendor_photos,
    get_vendor_tags,
    get_vendor_visits,
    remove_vendor_tag,
    soft_delete_vendor,
    update_qc_status,
    update_vendor,
)

logger = logging.getLogger(__name__)


class VendorListCreateView(APIView):
    """List vendors (paginated) or create a new one."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.DATA_ENTRY,
            AdminRole.QA_REVIEWER,
            AdminRole.ANALYST,
        )
    ]

    @extend_schema(
        tags=["Vendors"],
        summary="List vendors (paginated)",
        parameters=[
            OpenApiParameter(
                name="city_id",
                description="Filter by city UUID",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="area_id",
                description="Filter by area UUID",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="qc_status",
                description="Filter by QC status",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="data_source",
                description="Filter by data source",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="tag_id",
                description="Filter by assigned tag UUID",
                required=False,
                type=str,
            ),
        ],
        responses={200: VendorListSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Return paginated list of non-deleted vendors with optional filters.

        Args:
            request: Authenticated HTTP request.

        Returns:
            Paginated vendor list.
        """
        qs = Vendor.objects.select_related("city", "area", "landmark").order_by(
            "-created_at"
        )

        city_id = request.query_params.get("city_id")
        if city_id:
            qs = qs.filter(city_id=city_id)

        area_id = request.query_params.get("area_id")
        if area_id:
            qs = qs.filter(area_id=area_id)

        qc_status = request.query_params.get("qc_status")
        if qc_status:
            qs = qs.filter(qc_status=qc_status)

        data_source = request.query_params.get("data_source")
        if data_source:
            qs = qs.filter(data_source=data_source)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(business_name__icontains=search)

        tag_id = request.query_params.get("tag_id")
        if tag_id:
            qs = qs.filter(tags__id=tag_id)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            VendorListSerializer(page, many=True).data
        )

    @extend_schema(
        tags=["Vendors"],
        summary="Create vendor (SUPER_ADMIN, CITY_MANAGER, DATA_ENTRY)",
        request=CreateVendorSerializer,
        responses={
            201: VendorSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request: Request) -> Response:
        """Create a new vendor. Phone is encrypted in services.py.

        Args:
            request: HTTP request with vendor creation data.

        Returns:
            201 with new vendor data on success.
        """
        serializer = CreateVendorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            vendor = create_vendor(
                business_name=d["business_name"],
                slug=d["slug"],
                city_id=str(d["city_id"]),
                area_id=str(d["area_id"]),
                gps_lon=d["gps_lon"],
                gps_lat=d["gps_lat"],
                actor=request.user,
                request=request._request,
                phone=d.get("phone", ""),
                description=d.get("description", ""),
                address_text=d.get("address_text", ""),
                landmark_id=str(d["landmark_id"]) if d.get("landmark_id") else None,
                business_hours=d.get("business_hours"),
                data_source=d.get("data_source", "MANUAL_ENTRY"),
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            data=VendorSerializer(vendor).data,
            message="Vendor created",
            status_code=status.HTTP_201_CREATED,
        )


class VendorDetailView(APIView):
    """Retrieve, update, or soft-delete a single vendor.

    GET  — SUPER_ADMIN, CITY_MANAGER, DATA_ENTRY, QA_REVIEWER, FIELD_AGENT
    PATCH — SUPER_ADMIN, CITY_MANAGER, DATA_ENTRY (write roles only)
    DELETE — SUPER_ADMIN, CITY_MANAGER (destructive roles only)
    """

    _read_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN,
        AdminRole.CITY_MANAGER,
        AdminRole.DATA_ENTRY,
        AdminRole.QA_REVIEWER,
        AdminRole.FIELD_AGENT,
    )
    _write_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN,
        AdminRole.CITY_MANAGER,
        AdminRole.DATA_ENTRY,
    )
    _delete_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN,
        AdminRole.CITY_MANAGER,
        AdminRole.OPERATIONS_MANAGER,
    )

    def get_permissions(self) -> list:
        """Return permission classes based on the HTTP method."""
        if self.request.method == "GET":
            return [self._read_roles()]
        if self.request.method == "DELETE":
            return [self._delete_roles()]
        return [self._write_roles()]

    def _get_vendor(self, pk: str) -> Vendor | None:
        """Fetch non-deleted vendor by PK.

        Args:
            pk: UUID string of the vendor.

        Returns:
            Vendor instance or None.
        """
        try:
            return Vendor.objects.select_related(
                "city", "area", "landmark", "qc_reviewed_by"
            ).get(id=pk)
        except Vendor.DoesNotExist:
            return None

    @extend_schema(
        tags=["Vendors"], summary="Get vendor detail", responses={200: VendorSerializer}
    )
    def get(self, request: Request, pk: str) -> Response:
        """Return a single vendor by ID. Phone is decrypted in serializer.

        Args:
            request: Authenticated HTTP request.
            pk: Vendor UUID.

        Returns:
            200 with vendor data, 404 if not found.
        """
        vendor = self._get_vendor(pk)
        if vendor is None:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Vendor not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=VendorSerializer(vendor).data)

    @extend_schema(
        tags=["Vendors"],
        summary="Update vendor (SUPER_ADMIN, CITY_MANAGER, DATA_ENTRY)",
        request=UpdateVendorSerializer,
        responses={200: VendorSerializer},
    )
    def patch(self, request: Request, pk: str) -> Response:
        """Partially update a vendor. Phone re-encrypted in services.py.

        Args:
            request: HTTP request with update data.
            pk: Vendor UUID.

        Returns:
            200 with updated vendor data.
        """
        vendor = self._get_vendor(pk)
        if vendor is None:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Vendor not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UpdateVendorSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            vendor = update_vendor(
                vendor=vendor,
                updates=serializer.validated_data,
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=VendorSerializer(vendor).data)

    @extend_schema(
        tags=["Vendors"],
        summary="Soft-delete vendor (SUPER_ADMIN, CITY_MANAGER)",
        responses={
            204: OpenApiResponse(description="Soft-deleted — record preserved in DB")
        },
    )
    def delete(self, request: Request, pk: str) -> Response:
        """Soft-delete a vendor — sets is_deleted=True, never hard-deletes (R6).

        Args:
            request: Authenticated HTTP request.
            pk: Vendor UUID.

        Returns:
            204 on success, 404 if not found.
        """
        vendor = self._get_vendor(pk)
        if vendor is None:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Vendor not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        soft_delete_vendor(vendor=vendor, actor=request.user, request=request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VendorPhotosView(APIView):
    """GET /api/v1/vendors/<vendor_pk>/photos/ — list photos for a vendor."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.DATA_ENTRY,
            AdminRole.QA_REVIEWER,
            AdminRole.FIELD_AGENT,
            AdminRole.ANALYST,
        )
    ]

    @extend_schema(
        tags=["Vendors"],
        summary="List vendor photos (all authenticated roles)",
        responses={200: VendorPhotoSerializer(many=True)},
    )
    def get(self, request: Request, vendor_pk: str) -> Response:
        """Return presigned-URL photo list for a vendor.

        Args:
            request: Authenticated HTTP request.
            vendor_pk: Vendor UUID.

        Returns:
            200 with list of photo objects.
        """
        try:
            Vendor.objects.get(id=vendor_pk)
        except Vendor.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Vendor not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        photos = get_vendor_photos(vendor_pk)
        return success_response(data=photos)


class VendorVisitsView(APIView):
    """GET /api/v1/vendors/<vendor_pk>/visits/ — list field visits for a vendor."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.DATA_ENTRY,
            AdminRole.QA_REVIEWER,
            AdminRole.FIELD_AGENT,
            AdminRole.ANALYST,
        )
    ]

    @extend_schema(
        tags=["Vendors"],
        summary="List vendor field visits (all authenticated roles)",
        responses={200: VendorVisitSerializer(many=True)},
    )
    def get(self, request: Request, vendor_pk: str) -> Response:
        """Return field visits for a vendor.

        Args:
            request: Authenticated HTTP request.
            vendor_pk: Vendor UUID.

        Returns:
            200 with list of visit objects.
        """
        try:
            Vendor.objects.get(id=vendor_pk)
        except Vendor.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Vendor not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        visits = get_vendor_visits(vendor_pk)
        return success_response(data=VendorVisitSerializer(visits, many=True).data)


class VendorTagsView(APIView):
    """GET/POST /api/v1/vendors/<vendor_pk>/tags/ — list or assign tags."""

    _read_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN,
        AdminRole.CITY_MANAGER,
        AdminRole.DATA_ENTRY,
        AdminRole.QA_REVIEWER,
        AdminRole.FIELD_AGENT,
        AdminRole.ANALYST,
    )
    _write_roles = RolePermission.for_roles(
        AdminRole.SUPER_ADMIN,
        AdminRole.DATA_ENTRY,
        AdminRole.DATA_QUALITY_ANALYST,
    )

    def get_permissions(self) -> list:
        if self.request.method == "GET":
            return [self._read_roles()]
        return [self._write_roles()]

    @extend_schema(
        tags=["Vendors"],
        summary="List vendor tags (all authenticated roles)",
        responses={200: VendorTagSerializer(many=True)},
    )
    def get(self, request: Request, vendor_pk: str) -> Response:
        """Return tags assigned to a vendor.

        Args:
            request: Authenticated HTTP request.
            vendor_pk: Vendor UUID.

        Returns:
            200 with list of tag objects.
        """
        try:
            tags = get_vendor_tags(vendor_pk)
        except Vendor.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Vendor not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=VendorTagSerializer(tags, many=True).data)

    @extend_schema(
        tags=["Vendors"],
        summary="Assign tag to vendor (DATA_MANAGER, SUPER_ADMIN)",
        request=AssignTagSerializer,
        responses={200: VendorTagSerializer},
    )
    def post(self, request: Request, vendor_pk: str) -> Response:
        """Assign a tag to a vendor.

        Args:
            request: HTTP request with tag_id in body.
            vendor_pk: Vendor UUID.

        Returns:
            200 with the assigned tag data.
        """
        serializer = AssignTagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            tag = assign_vendor_tag(
                vendor_pk=vendor_pk,
                tag_id=str(serializer.validated_data["tag_id"]),
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=VendorTagSerializer(tag).data)


class VendorTagDetailView(APIView):
    """DELETE /api/v1/vendors/<vendor_pk>/tags/<tag_pk>/ — remove a tag."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.DATA_ENTRY,
        )
    ]

    @extend_schema(
        tags=["Vendors"],
        summary="Remove tag from vendor (DATA_MANAGER, SUPER_ADMIN)",
        responses={204: None},
    )
    def delete(self, request: Request, vendor_pk: str, tag_pk: str) -> Response:
        """Remove a tag from a vendor.

        Args:
            request: Authenticated HTTP request.
            vendor_pk: Vendor UUID.
            tag_pk: Tag UUID.

        Returns:
            204 on success.
        """
        try:
            remove_vendor_tag(
                vendor_pk=vendor_pk,
                tag_pk=tag_pk,
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class VendorAnalyticsView(APIView):
    """GET /api/v1/vendors/<vendor_pk>/analytics/ — Phase A stub."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.DATA_ENTRY,
            AdminRole.QA_REVIEWER,
        )
    ]

    @extend_schema(
        tags=["Vendors"],
        summary="Vendor analytics stub — Phase A zeros (DATA_MANAGER, QC_REVIEWER, SUPER_ADMIN)",
    )
    def get(self, request: Request, vendor_pk: str) -> Response:
        """Return Phase A analytics stub for a vendor.

        Args:
            request: Authenticated HTTP request.
            vendor_pk: Vendor UUID.

        Returns:
            200 with zero-value analytics dict.
        """
        try:
            Vendor.objects.get(id=vendor_pk)
        except Vendor.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Vendor not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=get_vendor_analytics_stub(vendor_pk))


class VendorQCStatusView(APIView):
    """Update the QC status of a vendor. QA_REVIEWER and above only."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.QA_REVIEWER,
        )
    ]

    @extend_schema(
        tags=["Vendors"],
        summary="Update vendor QC status (SUPER_ADMIN, CITY_MANAGER, QA_REVIEWER)",
        request=QCStatusUpdateSerializer,
        responses={200: VendorSerializer},
    )
    def patch(self, request: Request, pk: str) -> Response:
        """Update QC status and reviewer notes.

        Args:
            request: HTTP request with qc_status and optional qc_notes.
            pk: Vendor UUID.

        Returns:
            200 with updated vendor data.
        """
        try:
            vendor = Vendor.objects.get(id=pk)
        except Vendor.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "message": "Vendor not found",
                    "errors": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = QCStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            vendor = update_qc_status(
                vendor=vendor,
                new_status=serializer.validated_data["qc_status"],
                reviewer=request.user,
                request=request._request,
                notes=serializer.validated_data.get("qc_notes", ""),
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=VendorSerializer(vendor).data)
