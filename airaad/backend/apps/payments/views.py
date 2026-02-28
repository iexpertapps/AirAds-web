"""
AirAd Backend — Stripe Payment Views (Phase C §8)

Zero business logic — all delegated to payments/services.py.
Webhook endpoint is unauthenticated (Stripe signs with HMAC).
All other endpoints require vendor portal authentication.
"""

import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import CustomerUserJWTAuthentication
from core.exceptions import success_response

from . import services

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Serializers (input validation only)
# ---------------------------------------------------------------------------

class _CreateCheckoutSerializer(serializers.Serializer):
    level = serializers.ChoiceField(choices=["GOLD", "DIAMOND", "PLATINUM"])
    success_url = serializers.URLField()
    cancel_url = serializers.URLField()


class _CreatePortalSerializer(serializers.Serializer):
    return_url = serializers.URLField()


# ---------------------------------------------------------------------------
# Helper: extract vendor_id from authenticated request
# ---------------------------------------------------------------------------

def _get_vendor_id(request: Request) -> str | None:
    """Extract vendor_id from the authenticated user's owned vendor."""
    user_id = str(request.user.id) if request.user else None
    if not user_id:
        return None

    from apps.vendors.models import ClaimedStatus, Vendor

    vendor = Vendor.objects.filter(
        owner_id=user_id,
        claimed_status=ClaimedStatus.CLAIMED,
        is_deleted=False,
    ).first()
    return str(vendor.id) if vendor else None


def _no_vendor_response() -> Response:
    return Response(
        {"success": False, "data": None, "message": "No claimed vendor found", "errors": {}},
        status=status.HTTP_404_NOT_FOUND,
    )


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class CreateCheckoutView(APIView):
    """POST /api/v1/payments/create-checkout/

    Creates a Stripe Checkout Session for the vendor to subscribe.
    """

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Payments"],
        summary="Create Stripe Checkout Session for subscription",
        request=_CreateCheckoutSerializer,
        responses={
            200: OpenApiResponse(description="Checkout session created"),
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return _no_vendor_response()

        ser = _CreateCheckoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            result = services.create_checkout_session(
                vendor_id=vendor_id,
                level=ser.validated_data["level"],
                success_url=ser.validated_data["success_url"],
                cancel_url=ser.validated_data["cancel_url"],
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=result, message="Checkout session created")


class CreatePortalSessionView(APIView):
    """POST /api/v1/payments/create-portal-session/

    Creates a Stripe Customer Portal session for billing management.
    """

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Payments"],
        summary="Create Stripe Customer Portal session",
        request=_CreatePortalSerializer,
        responses={200: OpenApiResponse(description="Portal session created")},
    )
    def post(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return _no_vendor_response()

        ser = _CreatePortalSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            result = services.create_portal_session(
                vendor_id=vendor_id,
                return_url=ser.validated_data["return_url"],
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=result, message="Portal session created")


class StripeWebhookView(APIView):
    """POST /api/v1/payments/webhook/

    Stripe webhook receiver. No auth — verified via Stripe HMAC signature.
    Uses raw request body for signature verification.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Payments"],
        summary="Stripe webhook receiver (no auth, HMAC verified)",
        responses={
            200: OpenApiResponse(description="Event processed"),
            400: OpenApiResponse(description="Invalid signature"),
        },
    )
    def post(self, request: Request) -> Response:
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        try:
            event = services.construct_webhook_event(payload, sig_header)
        except ValueError as e:
            logger.warning("Stripe webhook signature verification failed: %s", e)
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = services.process_webhook_event(event)
        except Exception as exc:
            logger.error("Stripe webhook processing error: %s", exc, exc_info=True)
            return Response(
                {"error": "Webhook processing failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(result, status=status.HTTP_200_OK)


class SubscriptionStatusView(APIView):
    """GET /api/v1/payments/subscription-status/

    Returns the current subscription status for the authenticated vendor.
    """

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Payments"],
        summary="Get current subscription status",
        responses={200: OpenApiResponse(description="Subscription status")},
    )
    def get(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return _no_vendor_response()

        result = services.get_subscription_status(vendor_id)
        return success_response(data=result, message="OK")


class InvoiceListView(APIView):
    """GET /api/v1/payments/invoices/

    Returns invoice history from Stripe for the authenticated vendor.
    """

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Payments"],
        summary="Get invoice history",
        responses={200: OpenApiResponse(description="Invoice list")},
    )
    def get(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return _no_vendor_response()

        result = services.get_invoices(vendor_id)
        return success_response(data=result, message=f"{len(result)} invoices found")


class CancelSubscriptionView(APIView):
    """POST /api/v1/payments/cancel/

    Cancel subscription at end of billing period.
    """

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Payments"],
        summary="Cancel subscription at period end",
        responses={
            200: OpenApiResponse(description="Cancellation confirmed"),
            400: OpenApiResponse(description="No active subscription"),
        },
    )
    def post(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return _no_vendor_response()

        try:
            result = services.cancel_subscription(
                vendor_id=vendor_id,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=result, message="Subscription cancellation scheduled")


class ResumeSubscriptionView(APIView):
    """POST /api/v1/payments/resume/

    Resume a subscription that was set to cancel at period end.
    """

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Payments"],
        summary="Resume canceled subscription",
        responses={
            200: OpenApiResponse(description="Subscription resumed"),
            400: OpenApiResponse(description="Not pending cancellation"),
        },
    )
    def post(self, request: Request) -> Response:
        vendor_id = _get_vendor_id(request)
        if not vendor_id:
            return _no_vendor_response()

        try:
            result = services.resume_subscription(
                vendor_id=vendor_id,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=result, message="Subscription resumed")
