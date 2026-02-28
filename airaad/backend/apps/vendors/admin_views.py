"""
AirAd Backend — Admin Vendor Management Views (Phase B §3.7)

Zero business logic — all delegated to admin_services.py.
Every view uses RolePermission.for_roles() (R3).
"""

import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import AdminRole
from apps.accounts.permissions import RolePermission
from core.exceptions import success_response

from .admin_services import (
    approve_claim,
    approve_location,
    bulk_assign_tags,
    get_moderation_queue,
    launch_city,
    reject_claim,
    reject_location,
    suspend_vendor,
    verify_vendor,
)

logger = logging.getLogger(__name__)


class _ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)


class _BulkTagSerializer(serializers.Serializer):
    vendor_ids = serializers.ListField(child=serializers.UUIDField())
    tag_ids = serializers.ListField(child=serializers.UUIDField())


class AdminVerifyVendorView(APIView):
    """POST /api/v1/admin/vendors/{id}/verify/ — mark vendor as admin-verified."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.CONTENT_MODERATOR,
        )
    ]

    @extend_schema(
        tags=["Admin Management"],
        summary="Verify a vendor (admin badge)",
        responses={200: OpenApiResponse(description="Vendor verified")},
    )
    def post(self, request: Request, vendor_id: str) -> Response:
        """Mark a vendor as admin-verified.

        Args:
            request: Authenticated admin HTTP request.
            vendor_id: UUID of the vendor.

        Returns:
            200 with verification status.
        """
        try:
            result = verify_vendor(
                vendor_id=vendor_id,
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="Vendor verified successfully")


class AdminSuspendVendorView(APIView):
    """PATCH /api/v1/admin/vendors/{id}/suspend/ — suspend a vendor."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.CONTENT_MODERATOR,
        )
    ]

    @extend_schema(
        tags=["Admin Management"],
        summary="Suspend a vendor",
        request=_ReasonSerializer,
        responses={200: OpenApiResponse(description="Vendor suspended")},
    )
    def patch(self, request: Request, vendor_id: str) -> Response:
        """Suspend a vendor with a reason.

        Args:
            request: Authenticated admin HTTP request with reason.
            vendor_id: UUID of the vendor.

        Returns:
            200 with suspension status.
        """
        serializer = _ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = suspend_vendor(
                vendor_id=vendor_id,
                reason=serializer.validated_data["reason"],
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="Vendor suspended")


class AdminApproveClaimView(APIView):
    """POST /api/v1/admin/vendors/{id}/approve-claim/ — approve a vendor claim."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
        )
    ]

    @extend_schema(
        tags=["Admin Management"],
        summary="Approve a vendor ownership claim",
        responses={200: OpenApiResponse(description="Claim approved")},
    )
    def post(self, request: Request, vendor_id: str) -> Response:
        """Approve a pending vendor claim.

        Args:
            request: Authenticated admin HTTP request.
            vendor_id: UUID of the vendor.

        Returns:
            200 with claim approval status.
        """
        try:
            result = approve_claim(
                vendor_id=vendor_id,
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="Claim approved")


class AdminRejectClaimView(APIView):
    """POST /api/v1/admin/vendors/{id}/reject-claim/ — reject a vendor claim."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
        )
    ]

    @extend_schema(
        tags=["Admin Management"],
        summary="Reject a vendor ownership claim",
        request=_ReasonSerializer,
        responses={200: OpenApiResponse(description="Claim rejected")},
    )
    def post(self, request: Request, vendor_id: str) -> Response:
        """Reject a pending vendor claim with a reason.

        Args:
            request: Authenticated admin HTTP request with reason.
            vendor_id: UUID of the vendor.

        Returns:
            200 with claim rejection status.
        """
        serializer = _ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = reject_claim(
                vendor_id=vendor_id,
                reason=serializer.validated_data["reason"],
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="Claim rejected")


class AdminApproveLocationView(APIView):
    """POST /api/v1/admin/vendors/{id}/approve-location/ — approve location change."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.QA_REVIEWER,
        )
    ]

    @extend_schema(
        tags=["Admin Management"],
        summary="Approve a vendor location change",
        responses={200: OpenApiResponse(description="Location approved")},
    )
    def post(self, request: Request, vendor_id: str) -> Response:
        """Approve a pending vendor location change.

        Args:
            request: Authenticated admin HTTP request.
            vendor_id: UUID of the vendor.

        Returns:
            200 with location approval status.
        """
        try:
            result = approve_location(
                vendor_id=vendor_id,
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="Location approved")


class AdminRejectLocationView(APIView):
    """POST /api/v1/admin/vendors/{id}/reject-location/ — reject location change."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.QA_REVIEWER,
        )
    ]

    @extend_schema(
        tags=["Admin Management"],
        summary="Reject a vendor location change",
        request=_ReasonSerializer,
        responses={200: OpenApiResponse(description="Location rejected")},
    )
    def post(self, request: Request, vendor_id: str) -> Response:
        """Reject a vendor location change with a reason.

        Args:
            request: Authenticated admin HTTP request with reason.
            vendor_id: UUID of the vendor.

        Returns:
            200 with location rejection status.
        """
        serializer = _ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = reject_location(
                vendor_id=vendor_id,
                reason=serializer.validated_data["reason"],
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="Location rejected")


class AdminLaunchCityView(APIView):
    """POST /api/v1/admin/geo/cities/{id}/launch/ — launch a city."""

    permission_classes = [
        RolePermission.for_roles(AdminRole.SUPER_ADMIN)
    ]

    @extend_schema(
        tags=["Admin Management"],
        summary="Launch a city (activate it)",
        responses={200: OpenApiResponse(description="City launched")},
    )
    def post(self, request: Request, city_id: str) -> Response:
        """Mark a city as active/launched.

        Args:
            request: Authenticated admin HTTP request.
            city_id: UUID of the city.

        Returns:
            200 with city launch status.
        """
        try:
            result = launch_city(
                city_id=city_id,
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="City launched successfully")


class AdminBulkAssignTagsView(APIView):
    """POST /api/v1/admin/tags/bulk-assign/ — bulk assign tags to vendors."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CITY_MANAGER,
            AdminRole.CONTENT_MODERATOR,
        )
    ]

    @extend_schema(
        tags=["Admin Management"],
        summary="Bulk assign tags to multiple vendors",
        request=_BulkTagSerializer,
        responses={200: OpenApiResponse(description="Tags assigned")},
    )
    def post(self, request: Request) -> Response:
        """Bulk assign tags to multiple vendors.

        Args:
            request: Authenticated admin HTTP request with vendor_ids and tag_ids.

        Returns:
            200 with assignment summary.
        """
        serializer = _BulkTagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = bulk_assign_tags(
                vendor_ids=[str(v) for v in serializer.validated_data["vendor_ids"]],
                tag_ids=[str(t) for t in serializer.validated_data["tag_ids"]],
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="Tags assigned successfully")


# =========================================================================
# Phase B — Admin Moderation Views (§B-12)
# =========================================================================


class _ModerationNoteSerializer(serializers.Serializer):
    notes = serializers.CharField(max_length=2000, required=False, default="")


class AdminModerateReelApproveView(APIView):
    """POST /api/v1/admin/moderation/reels/{reel_id}/approve/ — approve a reel."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CONTENT_MODERATOR,
        )
    ]

    @extend_schema(
        tags=["Admin Moderation"],
        summary="Approve a pending reel",
        request=_ModerationNoteSerializer,
        responses={200: OpenApiResponse(description="Reel approved")},
    )
    def post(self, request: Request, reel_id: str) -> Response:
        """Approve a reel for public display."""
        from apps.reels.models import VendorReel
        from apps.reels.services import moderate_reel

        ser = _ModerationNoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            reel = moderate_reel(
                reel_id=reel_id,
                status="APPROVED",
                notes=ser.validated_data.get("notes", ""),
                admin_user=request.user,
                request=request._request,
            )
        except VendorReel.DoesNotExist:
            return Response(
                {"success": False, "data": None, "message": "Reel not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            data={"reel_id": str(reel.pk), "moderation_status": reel.moderation_status},
            message="Reel approved",
        )


class AdminModerateReelRejectView(APIView):
    """POST /api/v1/admin/moderation/reels/{reel_id}/reject/ — reject a reel."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CONTENT_MODERATOR,
        )
    ]

    @extend_schema(
        tags=["Admin Moderation"],
        summary="Reject a pending reel",
        request=_ModerationNoteSerializer,
        responses={200: OpenApiResponse(description="Reel rejected")},
    )
    def post(self, request: Request, reel_id: str) -> Response:
        """Reject a reel with notes."""
        from apps.reels.models import VendorReel
        from apps.reels.services import moderate_reel

        ser = _ModerationNoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            reel = moderate_reel(
                reel_id=reel_id,
                status="REJECTED",
                notes=ser.validated_data.get("notes", ""),
                admin_user=request.user,
                request=request._request,
            )
        except VendorReel.DoesNotExist:
            return Response(
                {"success": False, "data": None, "message": "Reel not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            data={"reel_id": str(reel.pk), "moderation_status": reel.moderation_status},
            message="Reel rejected",
        )


class AdminRemoveDiscountView(APIView):
    """POST /api/v1/admin/moderation/discounts/{discount_id}/remove/ — remove discount."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CONTENT_MODERATOR,
        )
    ]

    @extend_schema(
        tags=["Admin Moderation"],
        summary="Remove a fraudulent/violating discount",
        request=_ModerationNoteSerializer,
        responses={200: OpenApiResponse(description="Discount removed")},
    )
    def post(self, request: Request, discount_id: str) -> Response:
        """Remove a discount (admin moderation)."""
        from apps.vendors.discount_services import admin_remove_discount
        from apps.vendors.models import Discount

        ser = _ModerationNoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            admin_remove_discount(
                discount_id=discount_id,
                notes=ser.validated_data.get("notes", ""),
                admin_user=request.user,
                request=request._request,
            )
        except Discount.DoesNotExist:
            return Response(
                {"success": False, "data": None, "message": "Discount not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(
            data={"discount_id": discount_id, "status": "removed"},
            message="Discount removed",
        )


class AdminModerationQueueView(APIView):
    """GET /api/v1/admin/moderation/queue/ — combined moderation queue."""

    permission_classes = [
        RolePermission.for_roles(
            AdminRole.SUPER_ADMIN,
            AdminRole.CONTENT_MODERATOR,
            AdminRole.CITY_MANAGER,
        )
    ]

    @extend_schema(
        tags=["Admin Moderation"],
        summary="Combined moderation queue (reels + claims)",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request) -> Response:
        """Return combined moderation queue."""
        data = get_moderation_queue()
        return success_response(data=data)
