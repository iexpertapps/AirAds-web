"""
AirAd Backend — Discount Views (Phase B §B-6)

Thin views — all business logic lives in discount_services.py (R4).
"""

from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import CustomerUserJWTAuthentication
from apps.vendors import discount_services
from apps.vendors.models import Discount
from core.exceptions import success_response


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class _CreateDiscountSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    discount_type = serializers.ChoiceField(
        choices=["PERCENTAGE", "FIXED_AMOUNT", "BOGO", "HAPPY_HOUR", "FLASH_DEAL", "ITEM_SPECIFIC"]
    )
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    applies_to = serializers.CharField(max_length=50, required=False, default="ALL")
    item_description = serializers.CharField(required=False, default="")
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    is_recurring = serializers.BooleanField(required=False, default=False)
    recurrence_days = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=7),
        required=False,
        default=[],
    )
    min_order_value = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=0
    )
    ar_badge_text = serializers.CharField(max_length=50, required=False, default="")
    delivery_radius_m = serializers.IntegerField(required=False, allow_null=True, default=None)
    free_delivery_distance_m = serializers.IntegerField(required=False, allow_null=True, default=None)


class _UpdateDiscountSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    value = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    applies_to = serializers.CharField(max_length=50, required=False)
    item_description = serializers.CharField(required=False)
    start_time = serializers.DateTimeField(required=False)
    end_time = serializers.DateTimeField(required=False)
    is_recurring = serializers.BooleanField(required=False)
    recurrence_days = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=7), required=False
    )
    min_order_value = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    ar_badge_text = serializers.CharField(max_length=50, required=False)
    delivery_radius_m = serializers.IntegerField(required=False, allow_null=True)
    free_delivery_distance_m = serializers.IntegerField(required=False, allow_null=True)


class _HappyHourSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    applies_to = serializers.CharField(max_length=50, required=False, default="ALL")
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    ar_badge_text = serializers.CharField(max_length=50, required=False, default="Happy Hour")


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

class VendorDiscountListCreateView(APIView):
    """GET: list vendor's discounts. POST: create a new discount."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        vendor = _get_vendor_obj(request)
        if not vendor:
            return Response(
                {"detail": "No vendor linked to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        data = discount_services.list_vendor_discounts(str(vendor.pk))
        return success_response(data=data, message="OK")

    def post(self, request):
        vendor = _get_vendor_obj(request)
        if not vendor:
            return Response(
                {"detail": "No vendor linked to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = _CreateDiscountSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        discount = discount_services.create_discount(
            vendor_id=str(vendor.pk),
            data=ser.validated_data,
            request=request,
        )
        return success_response(
            data={"id": str(discount.pk), "title": discount.title},
            message="Discount created",
            status_code=status.HTTP_201_CREATED,
        )


class VendorDiscountDetailView(APIView):
    """PATCH: update discount. DELETE: deactivate discount."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, discount_id):
        vendor = _get_vendor_obj(request)
        if not vendor:
            return Response(
                {"detail": "No vendor linked to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = _UpdateDiscountSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            discount = discount_services.update_discount(
                discount_id=discount_id,
                vendor_id=str(vendor.pk),
                data=ser.validated_data,
                request=request,
            )
        except Discount.DoesNotExist:
            return Response(
                {"detail": "Discount not found."}, status=status.HTTP_404_NOT_FOUND
            )

        return success_response(
            data={"id": str(discount.pk), "title": discount.title},
            message="Discount updated",
        )

    def delete(self, request, discount_id):
        vendor = _get_vendor_obj(request)
        if not vendor:
            return Response(
                {"detail": "No vendor linked to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            discount_services.deactivate_discount(
                discount_id=discount_id,
                vendor_id=str(vendor.pk),
                request=request,
            )
        except Discount.DoesNotExist:
            return Response(
                {"detail": "Discount not found."}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class VendorDiscountAnalyticsView(APIView):
    """GET: campaign performance analytics for a discount."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, discount_id):
        vendor = _get_vendor_obj(request)
        if not vendor:
            return Response(
                {"detail": "No vendor linked to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            data = discount_services.get_discount_analytics(
                discount_id=discount_id,
                vendor_id=str(vendor.pk),
            )
        except Discount.DoesNotExist:
            return Response(
                {"detail": "Discount not found."}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(data)


class VendorHappyHourCreateView(APIView):
    """POST: create a happy hour (tier-gated)."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        vendor = _get_vendor_obj(request)
        if not vendor:
            return Response(
                {"detail": "No vendor linked to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = _HappyHourSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            discount = discount_services.create_happy_hour(
                vendor_id=str(vendor.pk),
                data=ser.validated_data,
                request=request,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"id": str(discount.pk), "title": discount.title},
            status=status.HTTP_201_CREATED,
        )
