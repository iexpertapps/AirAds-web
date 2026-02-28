"""
AirAd Backend — Reel Views (Phase B §B-9)

Thin views — all business logic lives in services.py (R4).
"""

from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import CustomerUserJWTAuthentication
from apps.reels import services
from core.exceptions import success_response


# ---------------------------------------------------------------------------
# Serializers (inline — single-use, kept with their views)
# ---------------------------------------------------------------------------

class _CreateReelSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    s3_key = serializers.CharField(max_length=500)
    thumbnail_s3_key = serializers.CharField(max_length=500, required=False, default="")
    duration_seconds = serializers.IntegerField(min_value=1)


class _UpdateReelSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    display_order = serializers.IntegerField(min_value=0, required=False)
    thumbnail_s3_key = serializers.CharField(max_length=500, required=False)


# ---------------------------------------------------------------------------
# Vendor Portal endpoints (IsAuthenticated — vendor owner)
# ---------------------------------------------------------------------------

class VendorReelListCreateView(APIView):
    """GET: list vendor's reels. POST: create a new reel."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        vendor = getattr(request.user, "owned_vendors", None)
        if vendor is None:
            return Response(
                {"detail": "No vendor linked to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        vendor_obj = vendor.first()
        if not vendor_obj:
            return Response(
                {"detail": "No vendor linked to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        data = services.list_vendor_reels(str(vendor_obj.pk))
        return success_response(data=data, message="OK")

    def post(self, request):
        vendor = getattr(request.user, "owned_vendors", None)
        if vendor is None:
            return Response(
                {"detail": "No vendor linked to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        vendor_obj = vendor.first()
        if not vendor_obj:
            return Response(
                {"detail": "No vendor linked to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = _CreateReelSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            reel = services.create_reel(
                vendor_id=str(vendor_obj.pk),
                title=ser.validated_data["title"],
                s3_key=ser.validated_data["s3_key"],
                duration_seconds=ser.validated_data["duration_seconds"],
                thumbnail_s3_key=ser.validated_data.get("thumbnail_s3_key", ""),
                request=request,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return success_response(
            data={"id": str(reel.pk), "status": reel.status},
            message="Reel created",
            status_code=status.HTTP_201_CREATED,
        )


class VendorReelDetailView(APIView):
    """PATCH: update reel metadata. DELETE: archive reel."""

    authentication_classes = [CustomerUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_vendor_id(self, request):
        vendor = getattr(request.user, "owned_vendors", None)
        if vendor is None:
            return None
        vendor_obj = vendor.first()
        return str(vendor_obj.pk) if vendor_obj else None

    def patch(self, request, reel_id):
        vendor_id = self._get_vendor_id(request)
        if not vendor_id:
            return Response(
                {"detail": "No vendor linked to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = _UpdateReelSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            reel = services.update_reel(
                reel_id=reel_id,
                vendor_id=vendor_id,
                data=ser.validated_data,
                request=request,
            )
        except services.VendorReel.DoesNotExist:
            return Response(
                {"detail": "Reel not found."}, status=status.HTTP_404_NOT_FOUND
            )

        return success_response(
            data={"id": str(reel.pk), "title": reel.title},
            message="Reel updated",
        )

    def delete(self, request, reel_id):
        vendor_id = self._get_vendor_id(request)
        if not vendor_id:
            return Response(
                {"detail": "No vendor linked to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            services.archive_reel(reel_id=reel_id, vendor_id=vendor_id, request=request)
        except services.VendorReel.DoesNotExist:
            return Response(
                {"detail": "Reel not found."}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Public endpoints (AllowAny)
# ---------------------------------------------------------------------------

class PublicVendorReelsView(APIView):
    """GET: list publicly visible reels for a vendor by slug."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, slug):
        data = services.list_public_reels(vendor_slug=slug)
        return Response({"results": data})


class ReelViewEventView(APIView):
    """POST: record a reel view event (fire-and-forget)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, reel_id):
        services.record_reel_view(reel_id=reel_id)
        return Response({"ok": True}, status=status.HTTP_202_ACCEPTED)
