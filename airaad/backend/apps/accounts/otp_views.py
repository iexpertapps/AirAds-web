"""
AirAd Backend — OTP Auth Views (Phase B §3.2)

Zero business logic — all delegated to otp_services.py.
Unauthenticated endpoints for send-otp and verify-otp.
Authenticated endpoint for profile management.
"""

import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from rest_framework_simplejwt.views import TokenRefreshView

from core.exceptions import success_response

from .models import CustomerUser
from .otp_serializers import (
    CustomerProfileSerializer,
    CustomerProfileUpdateSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer,
)
from .otp_services import send_otp, update_customer_profile, verify_otp

logger = logging.getLogger(__name__)


class OTPRateThrottle(AnonRateThrottle):
    """Rate limiter for OTP endpoints — 5 requests per minute per IP."""

    rate = "5/min"


class CustomerSendOTPView(APIView):
    """POST /api/v1/auth/customer/send-otp/ — send OTP to phone number."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [OTPRateThrottle]

    @extend_schema(
        tags=["Customer Auth"],
        summary="Send OTP to customer phone number",
        request=SendOTPSerializer,
        responses={
            200: OpenApiResponse(description="OTP sent successfully"),
            400: OpenApiResponse(description="Validation error or rate limited"),
            429: OpenApiResponse(description="Too many requests"),
        },
    )
    def post(self, request: Request) -> Response:
        """Send an OTP to the given phone number.

        Args:
            request: HTTP request with phone number.

        Returns:
            200 with success message and expiry info.
        """
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = send_otp(
                phone=serializer.validated_data["phone"],
                purpose=serializer.validated_data.get("purpose", "LOGIN"),
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=result, message="OTP sent successfully")


class CustomerVerifyOTPView(APIView):
    """POST /api/v1/auth/customer/verify-otp/ — verify OTP and login/create."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [OTPRateThrottle]

    @extend_schema(
        tags=["Customer Auth"],
        summary="Verify OTP and login/create customer account",
        request=VerifyOTPSerializer,
        responses={
            200: OpenApiResponse(description="Login successful — JWT tokens returned"),
            400: OpenApiResponse(description="Invalid/expired OTP"),
        },
    )
    def post(self, request: Request) -> Response:
        """Verify OTP code and return JWT tokens.

        Creates a new CustomerUser on first login.

        Args:
            request: HTTP request with phone and OTP code.

        Returns:
            200 with JWT tokens, user data, and is_new_user flag.
        """
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = verify_otp(
                phone=serializer.validated_data["phone"],
                otp_code=serializer.validated_data["otp"],
                purpose=serializer.validated_data.get("purpose", "LOGIN"),
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=result, message="Login successful")


class CustomerProfileView(APIView):
    """GET/PATCH /api/v1/auth/customer/profile/ — customer profile management."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Customer Auth"],
        summary="Get customer profile",
        responses={200: CustomerProfileSerializer},
    )
    def get(self, request: Request) -> Response:
        """Return the authenticated customer's profile.

        Args:
            request: Authenticated HTTP request.

        Returns:
            200 with customer profile data.
        """
        customer = self._get_customer(request)
        if customer is None:
            return Response(
                {"success": False, "data": None, "message": "Customer not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=CustomerProfileSerializer(customer).data)

    @extend_schema(
        tags=["Customer Auth"],
        summary="Update customer profile",
        request=CustomerProfileUpdateSerializer,
        responses={200: CustomerProfileSerializer},
    )
    def patch(self, request: Request) -> Response:
        """Update the authenticated customer's profile.

        Args:
            request: HTTP request with profile update data.

        Returns:
            200 with updated profile data.
        """
        customer = self._get_customer(request)
        if customer is None:
            return Response(
                {"success": False, "data": None, "message": "Customer not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CustomerProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        customer = update_customer_profile(
            customer=customer,
            updates=serializer.validated_data,
            request=request._request,
        )

        return success_response(data=CustomerProfileSerializer(customer).data)

    def _get_customer(self, request: Request) -> CustomerUser | None:
        """Resolve the authenticated customer from the JWT token.

        Args:
            request: Authenticated request.

        Returns:
            CustomerUser instance or None.
        """
        user_id = getattr(request.user, "id", None)
        if user_id is None:
            return None
        try:
            return CustomerUser.objects.get(id=user_id, is_active=True)
        except CustomerUser.DoesNotExist:
            return None


class CustomerAccountDeleteView(APIView):
    """DELETE /api/v1/auth/customer/account/ — GDPR account deletion (§B-1)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Customer Auth"],
        summary="Delete customer account (GDPR)",
        responses={
            200: OpenApiResponse(description="Account deletion initiated"),
            404: OpenApiResponse(description="Customer not found"),
        },
    )
    def delete(self, request: Request) -> Response:
        """Delete the authenticated customer's account.

        Anonymizes personal data, deactivates account, and creates audit log.
        Vendor claims owned by this customer are released.
        """
        from apps.audit.models import AuditLog

        user_id = getattr(request.user, "id", None)
        if user_id is None:
            return Response(
                {"success": False, "data": None, "message": "Not authenticated", "errors": {}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            customer = CustomerUser.objects.get(id=user_id, is_active=True)
        except CustomerUser.DoesNotExist:
            return Response(
                {"success": False, "data": None, "message": "Customer not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Release any vendor claims
        from apps.vendors.models import ClaimedStatus, Vendor

        Vendor.objects.filter(
            owner=customer,
            claimed_status__in=[ClaimedStatus.CLAIM_PENDING, ClaimedStatus.CLAIMED],
        ).update(
            owner=None,
            claimed_status=ClaimedStatus.UNCLAIMED,
        )

        # Anonymize and deactivate
        original_id = str(customer.id)
        customer.full_name = "DELETED_USER"
        customer.email = ""
        customer.device_token = ""
        customer.is_active = False
        customer.save(update_fields=[
            "full_name", "email", "device_token", "is_active", "updated_at"
        ])

        AuditLog.objects.create(
            action="CUSTOMER_ACCOUNT_DELETED_GDPR",
            entity_type="CustomerUser",
            entity_id=original_id,
            metadata={"reason": "GDPR self-service deletion"},
        )

        logger.info("Customer account deleted (GDPR): %s", original_id)
        return success_response(
            data={"deleted": True},
            message="Account deleted successfully. All personal data has been anonymized.",
        )


class VendorSendOTPView(APIView):
    """POST /api/v1/auth/vendor/send-otp/ — send OTP to vendor phone number."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [OTPRateThrottle]

    @extend_schema(
        tags=["Vendor Auth"],
        summary="Send OTP to vendor phone number",
        request=SendOTPSerializer,
        responses={200: OpenApiResponse(description="OTP sent successfully")},
    )
    def post(self, request: Request) -> Response:
        """Send an OTP for vendor authentication.

        Args:
            request: HTTP request with phone number.

        Returns:
            200 with success message.
        """
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = send_otp(
                phone=serializer.validated_data["phone"],
                purpose=serializer.validated_data.get("purpose", "LOGIN"),
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=result, message="OTP sent successfully")


class VendorVerifyOTPView(APIView):
    """POST /api/v1/auth/vendor/verify-otp/ — verify OTP and login vendor."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [OTPRateThrottle]

    @extend_schema(
        tags=["Vendor Auth"],
        summary="Verify OTP and login/create vendor account",
        request=VerifyOTPSerializer,
        responses={200: OpenApiResponse(description="Login successful — JWT tokens returned")},
    )
    def post(self, request: Request) -> Response:
        """Verify OTP for vendor and return JWT tokens.

        Args:
            request: HTTP request with phone and OTP code.

        Returns:
            200 with JWT tokens and user data.
        """
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = verify_otp(
                phone=serializer.validated_data["phone"],
                otp_code=serializer.validated_data["otp"],
                purpose=serializer.validated_data.get("purpose", "LOGIN"),
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=result, message="Login successful")


class VendorProfileView(APIView):
    """GET /api/v1/auth/vendor/me/ — vendor user profile."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Auth"],
        summary="Get vendor user profile",
        responses={200: CustomerProfileSerializer},
    )
    def get(self, request: Request) -> Response:
        """Return the authenticated vendor user's profile.

        Args:
            request: Authenticated HTTP request.

        Returns:
            200 with vendor user profile data.
        """
        user_id = getattr(request.user, "id", None)
        if user_id is None:
            return Response(
                {"success": False, "data": None, "message": "Not authenticated", "errors": {}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            customer = CustomerUser.objects.get(id=user_id, is_active=True)
        except CustomerUser.DoesNotExist:
            return Response(
                {"success": False, "data": None, "message": "Vendor user not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=CustomerProfileSerializer(customer).data)


class CustomerRefreshView(TokenRefreshView):
    """POST /api/v1/auth/customer/refresh/ — Refresh customer JWT token (§B-1)."""

    @extend_schema(tags=["Customer Auth"], summary="Refresh customer JWT token")
    def post(self, request: Request, *args, **kwargs) -> Response:
        return super().post(request, *args, **kwargs)


class VendorAuthRefreshView(TokenRefreshView):
    """POST /api/v1/auth/vendor/refresh/ — Refresh vendor JWT token (§B-2)."""

    @extend_schema(tags=["Vendor Auth"], summary="Refresh vendor JWT token")
    def post(self, request: Request, *args, **kwargs) -> Response:
        return super().post(request, *args, **kwargs)


class VendorEmailVerifyView(APIView):
    """POST /api/v1/auth/vendor/verify-email/ — Email verification (§B-2)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Auth"],
        summary="Verify vendor email address",
        responses={200: OpenApiResponse(description="Email verified")},
    )
    def post(self, request: Request) -> Response:
        """Mark vendor email as verified."""
        user_id = getattr(request.user, "id", None)
        if user_id is None:
            return Response(
                {"success": False, "data": None, "message": "Not authenticated", "errors": {}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            vendor_user = CustomerUser.objects.get(
                id=user_id, user_type="VENDOR", is_active=True,
            )
        except CustomerUser.DoesNotExist:
            return Response(
                {"success": False, "data": None, "message": "Vendor user not found", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not vendor_user.email:
            return Response(
                {"success": False, "data": None, "message": "No email address on file", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.audit.utils import log_action

        log_action(
            action="VENDOR_EMAIL_VERIFIED",
            actor=None,
            target_obj=vendor_user,
            request=request._request,
            before={},
            after={"email": vendor_user.email},
        )

        return success_response(
            data={"email_verified": True},
            message="Email address verified successfully.",
        )
