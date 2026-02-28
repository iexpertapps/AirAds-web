"""
AirAd Backend — Voice Bot Views (Phase B §B-7)

Thin views — all business logic lives in voicebot_services.py (R4).
"""

from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import CustomerUserJWTAuthentication
from apps.vendors import voicebot_services
from apps.vendors.models import Vendor
from core.exceptions import success_response


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class _UpdateVoiceBotSerializer(serializers.Serializer):
    menu_items = serializers.ListField(required=False)
    opening_hours_summary = serializers.CharField(required=False, allow_blank=True)
    delivery_info = serializers.DictField(required=False)
    custom_qa_pairs = serializers.ListField(required=False)
    intro_message = serializers.CharField(required=False, allow_blank=True)
    pickup_available = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)


class _TestQuerySerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_vendor_obj(request):
    """Return the first owned vendor for the authenticated user, or None."""
    owned = getattr(request.user, "owned_vendors", None)
    if owned is None:
        return None
    return owned.first()


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class VendorVoiceBotView(APIView):
    """GET: get voice bot config. PUT: update voice bot config."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        vendor = _get_vendor_obj(request)
        if not vendor:
            return Response(
                {"detail": "No vendor linked to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            data = voicebot_services.get_voicebot_config(str(vendor.pk))
        except Vendor.DoesNotExist:
            return Response(
                {"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return success_response(data=data, message="OK")

    def put(self, request):
        vendor = _get_vendor_obj(request)
        if not vendor:
            return Response(
                {"detail": "No vendor linked to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = _UpdateVoiceBotSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            data = voicebot_services.update_voicebot_config(
                vendor_id=str(vendor.pk),
                data=ser.validated_data,
                request=request,
            )
        except Vendor.DoesNotExist:
            return Response(
                {"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return success_response(data=data, message="Voice bot config updated")


class VendorVoiceBotTestView(APIView):
    """POST: test a voice query against the vendor's config."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        vendor = _get_vendor_obj(request)
        if not vendor:
            return Response(
                {"detail": "No vendor linked to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = _TestQuerySerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        result = voicebot_services.test_voice_query(
            vendor_id=str(vendor.pk),
            query=ser.validated_data["query"],
        )
        return success_response(data=result, message="OK")
