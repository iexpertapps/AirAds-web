"""
AirAd Backend — Vendor Portal Views (Phase C)

Zero business logic — all delegated to vendor_portal/services.py.
Vendor portal endpoints use `/api/v1/vendor-portal/` prefix.
"""

import logging

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.accounts.authentication import CustomerUserJWTAuthentication
from core.exceptions import success_response

from . import services

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Throttles
# ---------------------------------------------------------------------------

class VendorOTPThrottle(AnonRateThrottle):
    """Rate limiter for vendor OTP endpoints — 5 requests per minute per IP."""

    rate = "5/min"


# ---------------------------------------------------------------------------
# Serializers (input validation only)
# ---------------------------------------------------------------------------

class _SendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)


class _VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    otp = serializers.CharField(max_length=6, min_length=4)


class _UpdateProfileSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(max_length=2000, required=False)
    address_text = serializers.CharField(max_length=500, required=False)


class _UpdateServicesSerializer(serializers.Serializer):
    offers_delivery = serializers.BooleanField(required=False)
    offers_pickup = serializers.BooleanField(required=False)


class _LocationChangeSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    reason = serializers.CharField(max_length=500, required=False, default="")


class _UploadConfirmSerializer(serializers.Serializer):
    object_key = serializers.CharField(max_length=500)


# ---------------------------------------------------------------------------
# C-1: Vendor Portal Authentication
# ---------------------------------------------------------------------------

class VendorPortalSendOTPView(APIView):
    """POST /api/v1/vendor-portal/auth/send-otp/"""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [VendorOTPThrottle]

    @extend_schema(
        tags=["Vendor Portal Auth"],
        summary="Send OTP to vendor phone number",
        request=_SendOTPSerializer,
        responses={200: OpenApiResponse(description="OTP sent")},
    )
    def post(self, request: Request) -> Response:
        ser = _SendOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            result = services.vendor_send_otp(
                phone=ser.validated_data["phone"],
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="OTP sent")


class VendorPortalVerifyOTPView(APIView):
    """POST /api/v1/vendor-portal/auth/verify-otp/"""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [VendorOTPThrottle]

    @extend_schema(
        tags=["Vendor Portal Auth"],
        summary="Verify OTP and login vendor",
        request=_VerifyOTPSerializer,
        responses={200: OpenApiResponse(description="Login successful")},
    )
    def post(self, request: Request) -> Response:
        ser = _VerifyOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            result = services.vendor_verify_otp(
                phone=ser.validated_data["phone"],
                otp_code=ser.validated_data["otp"],
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="Login successful")


class VendorPortalRefreshView(APIView):
    """POST /api/v1/vendor-portal/auth/refresh/"""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Vendor Portal Auth"],
        summary="Refresh JWT access token",
        responses={200: OpenApiResponse(description="Token refreshed")},
    )
    def post(self, request: Request) -> Response:
        from rest_framework_simplejwt.exceptions import TokenError
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"success": False, "data": None, "message": "Refresh token required", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            return success_response(
                data={"access": str(token.access_token)},
                message="Token refreshed",
            )
        except TokenError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class VendorPortalLogoutView(APIView):
    """POST /api/v1/vendor-portal/auth/logout/"""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Portal Auth"],
        summary="Logout vendor (blacklist refresh token)",
        responses={200: OpenApiResponse(description="Logged out")},
    )
    def post(self, request: Request) -> Response:
        from rest_framework_simplejwt.exceptions import TokenError
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass
        return success_response(data=None, message="Logged out")


class VendorPortalMeView(APIView):
    """GET /api/v1/vendor-portal/auth/me/"""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Portal Auth"],
        summary="Get current vendor user info",
        responses={200: OpenApiResponse(description="Current user + vendor")},
    )
    def get(self, request: Request) -> Response:
        user_id = str(request.user.id) if request.user else None
        if not user_id:
            return Response(
                {"success": False, "data": None, "message": "Not authenticated", "errors": {}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            result = services.vendor_get_me(customer_id=user_id)
        except Exception as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="OK")


# ---------------------------------------------------------------------------
# Helper: extract vendor_id from authenticated request
# ---------------------------------------------------------------------------

def _get_vendor_id(request: Request) -> str | None:
    """Extract vendor_id from the JWT claims or find via owner lookup."""
    user_id = str(request.user.id) if request.user else None
    if not user_id:
        return None

    from apps.accounts.models import CustomerUser
    from apps.vendors.models import ClaimedStatus, Vendor

    vendor = Vendor.objects.filter(
        owner_id=user_id,
        claimed_status=ClaimedStatus.CLAIMED,
        is_deleted=False,
    ).first()
    return str(vendor.id) if vendor else None


# ---------------------------------------------------------------------------
# C-2: Vendor Portal Profile APIs
# ---------------------------------------------------------------------------

class VendorPortalProfileView(APIView):
    """GET/PATCH /api/v1/vendor-portal/profile/"""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Portal Profile"],
        summary="Get full vendor profile",
        responses={200: OpenApiResponse(description="Full vendor profile")},
    )
    def get(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return Response(
                {"success": False, "data": None, "message": "No claimed vendor found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        result = services.get_vendor_profile(vendor_id)
        return success_response(data=result, message="OK")

    @extend_schema(
        tags=["Vendor Portal Profile"],
        summary="Update vendor business info",
        request=_UpdateProfileSerializer,
        responses={200: OpenApiResponse(description="Profile updated")},
    )
    def patch(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return Response(
                {"success": False, "data": None, "message": "No claimed vendor found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        ser = _UpdateProfileSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            result = services.update_vendor_profile(
                vendor_id=vendor_id,
                updates=ser.validated_data,
                actor_id=str(request.user.id),
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="Profile updated")


class VendorPortalHoursView(APIView):
    """PATCH /api/v1/vendor-portal/profile/hours/"""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Portal Profile"],
        summary="Update business hours",
        responses={200: OpenApiResponse(description="Hours updated")},
    )
    def patch(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return Response(
                {"success": False, "data": None, "message": "No claimed vendor found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            result = services.update_business_hours(
                vendor_id=vendor_id,
                hours=request.data,
                request=request._request,
            )
        except Exception as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="Business hours updated")


class VendorPortalServicesView(APIView):
    """PATCH /api/v1/vendor-portal/profile/services/"""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Portal Profile"],
        summary="Update delivery/pickup flags",
        request=_UpdateServicesSerializer,
        responses={200: OpenApiResponse(description="Services updated")},
    )
    def patch(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return Response(
                {"success": False, "data": None, "message": "No claimed vendor found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        ser = _UpdateServicesSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = services.update_services(
            vendor_id=vendor_id,
            offers_delivery=ser.validated_data.get("offers_delivery"),
            offers_pickup=ser.validated_data.get("offers_pickup"),
            request=request._request,
        )
        return success_response(data=result, message="Services updated")


class VendorPortalLogoUploadView(APIView):
    """POST /api/v1/vendor-portal/profile/logo/"""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Portal Profile"],
        summary="Get presigned URL for logo upload",
        responses={200: OpenApiResponse(description="Upload URL generated")},
    )
    def post(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return Response(
                {"success": False, "data": None, "message": "No claimed vendor found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            result = services.generate_upload_url(vendor_id, "logo")
        except Exception as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="Upload URL generated")

    @extend_schema(
        tags=["Vendor Portal Profile"],
        summary="Confirm logo upload",
        request=_UploadConfirmSerializer,
        responses={200: OpenApiResponse(description="Logo saved")},
    )
    def put(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return Response(
                {"success": False, "data": None, "message": "No claimed vendor found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        ser = _UploadConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = services.confirm_upload(
            vendor_id=vendor_id,
            upload_type="logo",
            object_key=ser.validated_data["object_key"],
            request=request._request,
        )
        return success_response(data=result, message="Logo saved")


class VendorPortalCoverUploadView(APIView):
    """POST /api/v1/vendor-portal/profile/cover/"""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Portal Profile"],
        summary="Get presigned URL for cover photo upload",
        responses={200: OpenApiResponse(description="Upload URL generated")},
    )
    def post(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return Response(
                {"success": False, "data": None, "message": "No claimed vendor found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            result = services.generate_upload_url(vendor_id, "cover")
        except Exception as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="Upload URL generated")

    @extend_schema(
        tags=["Vendor Portal Profile"],
        summary="Confirm cover photo upload",
        request=_UploadConfirmSerializer,
        responses={200: OpenApiResponse(description="Cover photo saved")},
    )
    def put(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return Response(
                {"success": False, "data": None, "message": "No claimed vendor found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        ser = _UploadConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = services.confirm_upload(
            vendor_id=vendor_id,
            upload_type="cover",
            object_key=ser.validated_data["object_key"],
            request=request._request,
        )
        return success_response(data=result, message="Cover photo saved")


class VendorPortalLocationChangeView(APIView):
    """POST /api/v1/vendor-portal/profile/request-location-change/"""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Portal Profile"],
        summary="Submit GPS location change request",
        request=_LocationChangeSerializer,
        responses={200: OpenApiResponse(description="Location change submitted")},
    )
    def post(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return Response(
                {"success": False, "data": None, "message": "No claimed vendor found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        ser = _LocationChangeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            result = services.request_location_change(
                vendor_id=vendor_id,
                new_lat=ser.validated_data["latitude"],
                new_lng=ser.validated_data["longitude"],
                reason=ser.validated_data.get("reason", ""),
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=result, message="Location change submitted")


class VendorPortalCompletenessView(APIView):
    """GET /api/v1/vendor-portal/profile/completeness/"""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Portal Profile"],
        summary="Get profile completeness score",
        responses={200: OpenApiResponse(description="Completeness score")},
    )
    def get(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return Response(
                {"success": False, "data": None, "message": "No claimed vendor found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        result = services.get_profile_completeness(vendor_id)
        return success_response(data=result, message="OK")


# ---------------------------------------------------------------------------
# C-3: Vendor Portal Dashboard API
# ---------------------------------------------------------------------------

class VendorPortalDashboardView(APIView):
    """GET /api/v1/vendor-portal/dashboard/"""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Portal Dashboard"],
        summary="Get aggregated vendor dashboard data",
        responses={200: OpenApiResponse(description="Dashboard data")},
    )
    def get(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return Response(
                {"success": False, "data": None, "message": "No claimed vendor found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        result = services.get_vendor_dashboard(vendor_id)
        return success_response(data=result, message="OK")


# ---------------------------------------------------------------------------
# C-4: Landing Page Data API (Public)
# ---------------------------------------------------------------------------

class VendorPortalLandingStatsView(APIView):
    """GET /api/v1/vendor-portal/landing/stats/"""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Vendor Portal Landing"],
        summary="Get public landing page statistics",
        responses={200: OpenApiResponse(description="Landing page stats")},
    )
    def get(self, request: Request) -> Response:
        result = services.get_landing_page_stats()
        return success_response(data=result, message="OK")


# ---------------------------------------------------------------------------
# B-3: Activation Stage (§3.2)
# ---------------------------------------------------------------------------

class VendorPortalActivationStageView(APIView):
    """GET /api/v1/vendor-portal/activation-stage/ — current stage + next unlock criteria."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Portal"],
        summary="Get vendor activation stage and criteria",
        responses={200: OpenApiResponse(description="Activation stage info")},
    )
    def get(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return Response(
                {"success": False, "data": None, "message": "No claimed vendor found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        result = services.get_activation_stage(vendor_id)
        return success_response(data=result, message="OK")
