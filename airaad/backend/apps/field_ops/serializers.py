"""
AirAd Backend — Field Ops Serializers

No business logic — validation only. Delegates to field_ops/services.py.
s3_key is read-only — set by services.py after S3 upload.
photo_url is a presigned URL generated on read via services.py.
"""

import logging

from rest_framework import serializers

from .models import FieldPhoto, FieldVisit

logger = logging.getLogger(__name__)


class FieldVisitSerializer(serializers.ModelSerializer):
    """Read serializer for FieldVisit."""

    agent_email = serializers.CharField(source="agent.email", read_only=True)
    vendor_name = serializers.CharField(source="vendor.business_name", read_only=True)
    vendor_id = serializers.UUIDField(source="vendor.id", read_only=True)
    gps_confirmed_point = serializers.SerializerMethodField(read_only=True)
    gps_confirmed = serializers.SerializerMethodField(read_only=True)
    photos_count = serializers.SerializerMethodField(read_only=True)
    drift_meters = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FieldVisit
        fields = [
            "id",
            "vendor",
            "vendor_id",
            "vendor_name",
            "agent",
            "agent_email",
            "visited_at",
            "visit_notes",
            "gps_confirmed",
            "gps_confirmed_point",
            "photos_count",
            "drift_meters",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "agent",
            "agent_email",
            "vendor_id",
            "vendor_name",
            "gps_confirmed",
            "gps_confirmed_point",
            "photos_count",
            "drift_meters",
            "created_at",
        ]

    def get_gps_confirmed(self, obj: FieldVisit) -> bool:
        """Return True if a GPS point was confirmed on-site."""
        return obj.gps_confirmed_point is not None

    def get_photos_count(self, obj: FieldVisit) -> int:
        """Return count of active photos for this visit."""
        try:
            return obj.photos.filter(is_active=True).count()
        except Exception:
            return 0

    def get_drift_meters(self, obj: FieldVisit) -> float | None:
        """Return GPS drift distance in metres if both vendor and confirmed points exist."""
        try:
            if obj.gps_confirmed_point is None:
                return None
            vendor = obj.vendor
            gps_lat = getattr(vendor, "gps_lat", None)
            gps_lon = getattr(vendor, "gps_lon", None)
            if not (gps_lat and gps_lon):
                return None
            from math import atan2, cos, radians, sin, sqrt

            R = 6_371_000
            lat1 = radians(float(gps_lat))
            lon1 = radians(float(gps_lon))
            lat2 = radians(obj.gps_confirmed_point.y)
            lon2 = radians(obj.gps_confirmed_point.x)
            dlat, dlon = lat2 - lat1, lon2 - lon1
            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            return round(R * 2 * atan2(sqrt(a), sqrt(1 - a)), 1)
        except Exception:
            return None

    def get_gps_confirmed_point(self, obj: FieldVisit) -> dict | None:
        """Return confirmed GPS point as {longitude, latitude} dict.

        Args:
            obj: FieldVisit instance.

        Returns:
            Dict with longitude and latitude, or None.
        """
        if obj.gps_confirmed_point:
            return {
                "longitude": obj.gps_confirmed_point.x,
                "latitude": obj.gps_confirmed_point.y,
            }
        return None


class CreateFieldVisitSerializer(serializers.Serializer):
    """Serializer for creating a FieldVisit. Delegates to field_ops/services.py."""

    vendor_id = serializers.UUIDField()
    visited_at = serializers.DateTimeField(required=False, allow_null=True)
    visit_notes = serializers.CharField(required=False, default="", allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    gps_lon = serializers.FloatField(required=False, allow_null=True)
    gps_lat = serializers.FloatField(required=False, allow_null=True)

    def validate(self, attrs: dict) -> dict:
        """Normalise notes/gps aliases and validate coordinate pairing.

        Args:
            attrs: Validated field data.

        Returns:
            Validated attrs dict.

        Raises:
            ValidationError: If only one of longitude/latitude is provided.
        """
        if attrs.get("notes") and not attrs.get("visit_notes"):
            attrs["visit_notes"] = attrs.pop("notes")
        else:
            attrs.pop("notes", None)
        lon = attrs.pop("gps_lon", None) or attrs.pop("longitude", None)
        lat = attrs.pop("gps_lat", None) or attrs.pop("latitude", None)
        if (lon is None) != (lat is None):
            raise serializers.ValidationError(
                "longitude and latitude must be provided together."
            )
        if lon is not None:
            attrs["longitude"] = lon
            attrs["latitude"] = lat
        return attrs


class FieldPhotoSerializer(serializers.ModelSerializer):
    """Read serializer for FieldPhoto — includes presigned URL."""

    photo_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FieldPhoto
        fields = [
            "id",
            "field_visit",
            "s3_key",
            "photo_url",
            "caption",
            "is_active",
            "uploaded_at",
        ]
        read_only_fields = ["id", "s3_key", "photo_url", "uploaded_at"]

    def get_photo_url(self, obj: FieldPhoto) -> str:
        """Generate a presigned S3 URL for the photo.

        Args:
            obj: FieldPhoto instance.

        Returns:
            Presigned HTTPS URL string.
        """
        from apps.field_ops.services import get_field_photo_url

        try:
            return get_field_photo_url(obj)
        except Exception as e:
            logger.error(
                "Failed to generate presigned URL",
                extra={"photo_id": str(obj.id), "error": str(e)},
            )
            return ""


class UploadFieldPhotoSerializer(serializers.Serializer):
    """Serializer for uploading a FieldPhoto. Delegates to field_ops/services.py."""

    file = serializers.ImageField(help_text="Photo file (JPEG, PNG).")
    caption = serializers.CharField(
        max_length=500, required=False, default="", allow_blank=True
    )
