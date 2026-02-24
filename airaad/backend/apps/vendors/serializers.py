"""
AirAd Backend — Vendors Serializers

VendorSerializer: to_representation decrypts phone on read.
Write path encrypts phone in vendors/services.py — NOT here.
GPS: accept latitude/longitude floats, return as dict on read.
No business logic — validation only.
read_only_fields explicitly declared.
"""

import logging

from rest_framework import serializers

from core.encryption import EncryptionError, decrypt

from .models import DataSource, QCStatus, Vendor

logger = logging.getLogger(__name__)


class GpsPointMixin:
    """Mixin that provides a shared get_gps_point() method for vendor serializers."""

    def get_gps_point(self, obj: Vendor) -> dict | None:
        """Return GPS point as {longitude, latitude} dict.

        Args:
            obj: Vendor instance.

        Returns:
            Dict with longitude and latitude, or None.
        """
        if obj.gps_point:
            return {"longitude": obj.gps_point.x, "latitude": obj.gps_point.y}
        return None


class VendorSerializer(GpsPointMixin, serializers.ModelSerializer):
    """Full Vendor serializer.

    Read path: phone_number_encrypted is decrypted and returned as phone_number.
    Write path: phone encryption happens in vendors/services.py — never here.
    GPS: gps_point returned as {longitude, latitude} dict.
    """

    phone_number = serializers.SerializerMethodField(read_only=True)
    gps_point = serializers.SerializerMethodField(read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    area_name = serializers.CharField(source="area.name", read_only=True)
    landmark_name = serializers.CharField(
        source="landmark.name", read_only=True, allow_null=True
    )
    qc_reviewed_by_email = serializers.CharField(
        source="qc_reviewed_by.email", read_only=True, allow_null=True
    )
    storefront_photo_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Vendor
        fields = [
            "id",
            "business_name",
            "slug",
            "description",
            "gps_point",
            "address_text",
            "city",
            "city_name",
            "area",
            "area_name",
            "landmark",
            "landmark_name",
            "phone_number",
            "business_hours",
            "claimed_status",
            "storefront_photo_url",
            "qc_status",
            "qc_reviewed_by",
            "qc_reviewed_by_email",
            "qc_reviewed_at",
            "qc_notes",
            "data_source",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "phone_number",
            "gps_point",
            "city_name",
            "area_name",
            "landmark_name",
            "qc_reviewed_by_email",
            "storefront_photo_url",
            "is_deleted",
            "claimed_status",
            "created_at",
            "updated_at",
        ]

    def get_storefront_photo_url(self, obj: Vendor) -> str:
        """Return a presigned S3 URL for the storefront photo, or empty string.

        Args:
            obj: Vendor instance.

        Returns:
            Presigned URL string, or empty string if no photo or generation fails.
        """
        if not obj.storefront_photo_key:
            return ""
        try:
            from core.storage import generate_presigned_url

            return generate_presigned_url(obj.storefront_photo_key)
        except (Exception,):
            return ""

    def get_phone_number(self, obj: Vendor) -> str:
        """Decrypt and return the phone number MASKED on read.

        Phone numbers are NEVER returned in plain text in any API response.
        Only the last 4 digits are visible; the rest is replaced with asterisks.
        Example: +92300****567 → ********4567

        Args:
            obj: Vendor instance.

        Returns:
            Masked phone number string, or empty string on error.
        """
        if not obj.phone_number_encrypted:
            return ""
        try:
            plain = decrypt(bytes(obj.phone_number_encrypted))
            if not plain:
                return ""
            # Mask all but last 4 digits
            if len(plain) > 4:
                return "*" * (len(plain) - 4) + plain[-4:]
            return "*" * len(plain)
        except EncryptionError as e:
            logger.error(
                "Failed to decrypt phone for vendor",
                extra={"vendor_id": str(obj.id), "error": str(e)},
            )
            return ""

    def get_gps_point(self, obj: Vendor) -> dict | None:
        """Return GPS point as {longitude, latitude} dict.

        Args:
            obj: Vendor instance.

        Returns:
            Dict with longitude and latitude, or None.
        """
        if obj.gps_point:
            return {"longitude": obj.gps_point.x, "latitude": obj.gps_point.y}
        return None


class CreateVendorSerializer(serializers.Serializer):
    """Serializer for creating a Vendor. Delegates to vendors/services.py.

    Accepts both longitude/latitude and gps_lon/gps_lat field names.
    slug is optional — auto-generated from business_name if omitted.
    """

    business_name = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=280, required=False, allow_blank=True)
    description = serializers.CharField(required=False, default="", allow_blank=True)
    longitude = serializers.FloatField(
        required=False, help_text="GPS longitude (alias: gps_lon)."
    )
    latitude = serializers.FloatField(
        required=False, help_text="GPS latitude (alias: gps_lat)."
    )
    gps_lon = serializers.FloatField(required=False, help_text="GPS longitude alias.")
    gps_lat = serializers.FloatField(required=False, help_text="GPS latitude alias.")
    address_text = serializers.CharField(
        max_length=500, required=False, default="", allow_blank=True
    )
    city_id = serializers.UUIDField()
    area_id = serializers.UUIDField()
    landmark_id = serializers.UUIDField(required=False, allow_null=True)
    phone = serializers.CharField(
        max_length=20, required=False, default="", allow_blank=True
    )
    business_hours = serializers.DictField(required=False, allow_null=True)
    storefront_photo_key = serializers.CharField(
        max_length=500, required=False, default="", allow_blank=True
    )
    data_source = serializers.ChoiceField(
        choices=[s.value for s in DataSource],
        default=DataSource.MANUAL_ENTRY,
    )

    def validate(self, attrs: dict) -> dict:
        """Normalise gps_lon/gps_lat aliases and auto-generate slug."""
        import re

        # Normalise coordinate field names
        lon = attrs.pop("gps_lon", None) or attrs.pop("longitude", None)
        lat = attrs.pop("gps_lat", None) or attrs.pop("latitude", None)
        if lon is None or lat is None:
            raise serializers.ValidationError(
                "GPS coordinates are required (longitude/latitude or gps_lon/gps_lat)."
            )
        attrs["gps_lon"] = lon
        attrs["gps_lat"] = lat
        # Auto-generate slug if not provided
        if not attrs.get("slug"):
            base = re.sub(r"[^\w\s-]", "", attrs["business_name"].lower())
            attrs["slug"] = re.sub(r"[\s_]+", "-", base).strip("-")[:280]
        return attrs


class UpdateVendorSerializer(serializers.Serializer):
    """Serializer for updating a Vendor. Delegates to vendors/services.py."""

    business_name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    longitude = serializers.FloatField(required=False)
    latitude = serializers.FloatField(required=False)
    address_text = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )
    city_id = serializers.UUIDField(required=False)
    area_id = serializers.UUIDField(required=False)
    landmark_id = serializers.UUIDField(required=False, allow_null=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    business_hours = serializers.DictField(required=False)
    storefront_photo_key = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )

    def validate(self, attrs: dict) -> dict:
        """Validate that longitude and latitude are provided together.

        Args:
            attrs: Validated field data.

        Returns:
            Validated attrs dict.

        Raises:
            ValidationError: If only one of longitude/latitude is provided.
        """
        has_lon = "longitude" in attrs
        has_lat = "latitude" in attrs
        if has_lon != has_lat:
            raise serializers.ValidationError(
                "longitude and latitude must be provided together."
            )
        if has_lon and has_lat:
            attrs["gps_lon"] = attrs.pop("longitude")
            attrs["gps_lat"] = attrs.pop("latitude")
        return attrs


class QCStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating a Vendor's QC status."""

    qc_status = serializers.ChoiceField(choices=[s.value for s in QCStatus])
    qc_notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs: dict) -> dict:
        """Enforce R3: rejection requires a non-empty reason.

        Args:
            attrs: Validated field data.

        Returns:
            Validated attrs dict.

        Raises:
            ValidationError: If status is REJECTED and qc_notes is empty.
        """
        status = attrs.get("qc_status")
        notes = attrs.get("qc_notes", "").strip()
        if status == QCStatus.REJECTED and not notes:
            raise serializers.ValidationError(
                {"qc_notes": "A rejection reason is required when rejecting a vendor."}
            )
        return attrs


class VendorPhotoSerializer(serializers.Serializer):
    """Serializer for FieldPhoto sub-resource on a vendor."""

    id = serializers.UUIDField(read_only=True)
    presigned_url = serializers.CharField(read_only=True)
    caption = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    uploaded_at = serializers.DateTimeField(read_only=True)
    visit_id = serializers.UUIDField(source="field_visit_id", read_only=True)


class VendorVisitSerializer(serializers.Serializer):
    """Serializer for FieldVisit sub-resource on a vendor."""

    id = serializers.UUIDField(read_only=True)
    agent_name = serializers.CharField(source="agent.full_name", read_only=True)
    visited_at = serializers.DateTimeField(read_only=True)
    visit_notes = serializers.CharField(read_only=True)
    gps_confirmed_point = serializers.SerializerMethodField(read_only=True)

    def get_gps_confirmed_point(self, obj) -> dict | None:
        if obj.gps_confirmed_point:
            return {
                "longitude": obj.gps_confirmed_point.x,
                "latitude": obj.gps_confirmed_point.y,
            }
        return None


class VendorTagSerializer(serializers.Serializer):
    """Serializer for Tag sub-resource on a vendor."""

    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    tag_type = serializers.CharField(read_only=True)
    display_label = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)


class AssignTagSerializer(serializers.Serializer):
    """Serializer for POST /vendors/<pk>/tags/ — assign a tag to a vendor."""

    tag_id = serializers.UUIDField()


class VendorListSerializer(GpsPointMixin, serializers.ModelSerializer):
    """Lightweight Vendor serializer for list views — no phone decryption."""

    gps_point = serializers.SerializerMethodField(read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    area_name = serializers.CharField(source="area.name", read_only=True)

    class Meta:
        model = Vendor
        fields = [
            "id",
            "business_name",
            "slug",
            "gps_point",
            "city_name",
            "area_name",
            "qc_status",
            "data_source",
            "claimed_status",
            "created_at",
        ]
        read_only_fields = fields
