"""
AirAd Backend — Vendor Claim Flow Views (Phase B §3.2)

Zero business logic — all delegated to claim_services.py.
Authenticated endpoints for customers to claim vendor listings.
"""

import logging

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import CustomerUserJWTAuthentication
from core.exceptions import success_response

from .claim_services import (
    get_claim_status,
    get_claimable_vendors,
    submit_claim,
    upload_claim_proof,
    verify_claim_otp,
    withdraw_claim,
)

logger = logging.getLogger(__name__)


class _SubmitClaimSerializer(serializers.Serializer):
    vendor_id = serializers.UUIDField()


class SubmitClaimView(APIView):
    """POST /api/v1/vendors/claim/ — submit a claim on a vendor listing."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Claim"],
        summary="Submit a claim on an unclaimed vendor",
        request=_SubmitClaimSerializer,
        responses={
            200: OpenApiResponse(description="Claim submitted"),
            400: OpenApiResponse(description="Claim validation error"),
        },
    )
    def post(self, request: Request) -> Response:
        """Submit a claim for a vendor listing.

        Args:
            request: Authenticated HTTP request with vendor_id.

        Returns:
            200 with claim submission status.
        """
        serializer = _SubmitClaimSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = getattr(request.user, "id", None)
        if user_id is None:
            return Response(
                {"success": False, "data": None, "message": "Not authenticated", "errors": {}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            result = submit_claim(
                vendor_id=str(serializer.validated_data["vendor_id"]),
                customer_id=str(user_id),
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=result, message="Claim submitted")


class WithdrawClaimView(APIView):
    """DELETE /api/v1/vendors/{vendor_id}/claim/ — withdraw a pending claim."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Claim"],
        summary="Withdraw a pending vendor claim",
        responses={
            200: OpenApiResponse(description="Claim withdrawn"),
            400: OpenApiResponse(description="Withdrawal error"),
        },
    )
    def delete(self, request: Request, vendor_id: str) -> Response:
        """Withdraw a pending claim on a vendor.

        Args:
            request: Authenticated HTTP request.
            vendor_id: UUID of the vendor.

        Returns:
            200 with withdrawal status.
        """
        user_id = getattr(request.user, "id", None)
        if user_id is None:
            return Response(
                {"success": False, "data": None, "message": "Not authenticated", "errors": {}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            result = withdraw_claim(
                vendor_id=vendor_id,
                customer_id=str(user_id),
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=result, message="Claim withdrawn")


class ClaimableVendorsView(APIView):
    """GET /api/v1/vendors/claimable/ — search for unclaimed vendors."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Vendor Claim"],
        summary="Search for claimable (unclaimed) vendors",
        parameters=[
            OpenApiParameter(name="lat", type=float, required=False),
            OpenApiParameter(name="lng", type=float, required=False),
            OpenApiParameter(name="q", type=str, required=False),
        ],
        responses={200: OpenApiResponse(description="List of claimable vendors")},
    )
    def get(self, request: Request) -> Response:
        """Search for unclaimed vendor listings.

        Args:
            request: HTTP request with optional lat/lng/q params.

        Returns:
            200 with list of claimable vendors.
        """
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        query = request.query_params.get("q", "")

        try:
            lat_f = float(lat) if lat else None
            lng_f = float(lng) if lng else None
        except (TypeError, ValueError):
            lat_f = None
            lng_f = None

        results = get_claimable_vendors(lat=lat_f, lng=lng_f, query=query)
        return success_response(data=results, message=f"{len(results)} claimable vendors found")


# =========================================================================
# Phase B — Additional Claim Flow Views (§B-3)
# =========================================================================


class _ClaimOTPSerializer(serializers.Serializer):
    otp_code = serializers.CharField(max_length=10)


class _ClaimProofSerializer(serializers.Serializer):
    proof_s3_key = serializers.CharField(max_length=500)
    license_s3_key = serializers.CharField(max_length=500, required=False, default="")


class ClaimVerifyOTPView(APIView):
    """POST /api/v1/vendors/{vendor_id}/claim/verify-otp/ — OTP verification for claim."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Claim"],
        summary="Verify OTP for automated claim approval",
        request=_ClaimOTPSerializer,
        responses={200: OpenApiResponse(description="OTP verified, claim approved")},
    )
    def post(self, request: Request, vendor_id: str) -> Response:
        """Verify OTP to auto-approve a claim."""
        ser = _ClaimOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user_id = getattr(request.user, "id", None)
        if user_id is None:
            return Response(
                {"success": False, "data": None, "message": "Not authenticated", "errors": {}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            result = verify_claim_otp(
                vendor_id=vendor_id,
                otp_code=ser.validated_data["otp_code"],
                customer_id=str(user_id),
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=result, message="OTP verified")


class ClaimUploadProofView(APIView):
    """POST /api/v1/vendors/{vendor_id}/claim/upload-proof/ — upload proof documents."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Claim"],
        summary="Upload proof for manual claim verification",
        request=_ClaimProofSerializer,
        responses={200: OpenApiResponse(description="Proof uploaded")},
    )
    def post(self, request: Request, vendor_id: str) -> Response:
        """Upload storefront photo and business license for claim proof."""
        ser = _ClaimProofSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user_id = getattr(request.user, "id", None)
        if user_id is None:
            return Response(
                {"success": False, "data": None, "message": "Not authenticated", "errors": {}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            result = upload_claim_proof(
                vendor_id=vendor_id,
                customer_id=str(user_id),
                proof_s3_key=ser.validated_data["proof_s3_key"],
                license_s3_key=ser.validated_data.get("license_s3_key", ""),
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=result, message="Proof uploaded")


class ClaimStatusView(APIView):
    """GET /api/v1/vendors/{vendor_id}/claim/status/ — check claim status."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Vendor Claim"],
        summary="Check current claim status for a vendor",
        responses={200: OpenApiResponse(description="Claim status")},
    )
    def get(self, request: Request, vendor_id: str) -> Response:
        """Return the current claim status for a vendor."""
        try:
            result = get_claim_status(vendor_id=vendor_id)
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=result)
