"""
AirAd Backend — Vendors Service Layer (R4)

Phone encrypt/decrypt happens HERE — never in serializers or views.
BusinessHoursSchema validation on every write.
Every mutation calls log_action() (R5).
Soft delete: sets is_deleted=True — never hard delete (R6).
Multi-step mutations wrapped in @transaction.atomic.
"""

import logging
from typing import Any

from apps.audit.utils import log_action
from core.encryption import (  # noqa: F401 (EncryptionError used in docstrings)
    EncryptionError,
    decrypt,
    encrypt,
)
from core.schemas import BusinessHoursSchema
from django.contrib.gis.geos import Point
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from pydantic import ValidationError as PydanticValidationError

from .models import DataSource, QCStatus, Vendor

logger = logging.getLogger(__name__)

ERROR_LOG_CAP = 1000


# ---------------------------------------------------------------------------
# Vendor sub-resource services
# ---------------------------------------------------------------------------


def get_vendor_photos(vendor_pk: str) -> list[dict[str, Any]]:
    """Return FieldPhotos for a vendor with presigned S3 URLs.

    Args:
        vendor_pk: UUID string of the vendor.

    Returns:
        List of photo dicts with presigned_url included.
    """
    from apps.field_ops.models import FieldPhoto
    from core.storage import StorageError, generate_presigned_url

    photos = (
        FieldPhoto.objects.filter(
            field_visit__vendor_id=vendor_pk,
            is_active=True,
        )
        .select_related("field_visit")
        .order_by("-uploaded_at")
    )

    result = []
    for photo in photos:
        try:
            url = generate_presigned_url(photo.s3_key)
        except (StorageError, ValueError):
            url = ""
        result.append(
            {
                "id": photo.id,
                "field_visit_id": photo.field_visit_id,
                "presigned_url": url,
                "caption": photo.caption,
                "is_active": photo.is_active,
                "uploaded_at": photo.uploaded_at,
            }
        )
    return result


def get_vendor_visits(vendor_pk: str) -> Any:
    """Return FieldVisits for a vendor.

    Args:
        vendor_pk: UUID string of the vendor.

    Returns:
        QuerySet of FieldVisit instances.
    """
    from apps.field_ops.models import FieldVisit

    return (
        FieldVisit.objects.filter(
            vendor_id=vendor_pk,
        )
        .select_related("agent")
        .order_by("-visited_at")
    )


def get_vendor_tags(vendor_pk: str) -> Any:
    """Return tags assigned to a vendor.

    Args:
        vendor_pk: UUID string of the vendor.

    Returns:
        QuerySet of Tag instances.
    """
    vendor = Vendor.objects.get(id=vendor_pk)
    return vendor.tags.all()


@transaction.atomic
def assign_vendor_tag(
    vendor_pk: str, tag_id: str, actor: Any, request: HttpRequest
) -> Any:
    """Assign a tag to a vendor.

    Args:
        vendor_pk: UUID string of the vendor.
        tag_id: UUID string of the tag to assign.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        The Tag instance that was assigned.

    Raises:
        ValueError: If vendor or tag not found, or tag is inactive.
    """
    from apps.tags.models import Tag

    try:
        vendor = Vendor.objects.get(id=vendor_pk)
    except Vendor.DoesNotExist:
        raise ValueError(f"Vendor '{vendor_pk}' not found")

    try:
        tag = Tag.objects.get(id=tag_id)
    except Tag.DoesNotExist:
        raise ValueError(f"Tag '{tag_id}' not found")

    if not tag.is_active:
        raise ValueError(f"Tag '{tag.name}' is not active and cannot be assigned")

    MAX_TAGS_PER_VENDOR = 15
    current_count = vendor.tags.count()
    if current_count >= MAX_TAGS_PER_VENDOR:
        raise ValueError(
            f"Vendor already has {current_count} tags. "
            f"Maximum allowed is {MAX_TAGS_PER_VENDOR} (prevents keyword stuffing)."
        )

    vendor.tags.add(tag)

    log_action(
        action="VENDOR_TAG_ASSIGNED",
        actor=actor,
        target_obj=vendor,
        request=request,
        before={},
        after={"tag_id": str(tag.id), "tag_name": tag.name, "tag_type": tag.tag_type},
    )
    return tag


@transaction.atomic
def remove_vendor_tag(
    vendor_pk: str, tag_pk: str, actor: Any, request: HttpRequest
) -> None:
    """Remove a tag from a vendor.

    Args:
        vendor_pk: UUID string of the vendor.
        tag_pk: UUID string of the tag to remove.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Raises:
        ValueError: If vendor or tag not found.
    """
    from apps.tags.models import Tag

    try:
        vendor = Vendor.objects.get(id=vendor_pk)
    except Vendor.DoesNotExist:
        raise ValueError(f"Vendor '{vendor_pk}' not found")

    try:
        tag = Tag.objects.get(id=tag_pk)
    except Tag.DoesNotExist:
        raise ValueError(f"Tag '{tag_pk}' not found")

    vendor.tags.remove(tag)

    log_action(
        action="VENDOR_TAG_REMOVED",
        actor=actor,
        target_obj=vendor,
        request=request,
        before={"tag_id": str(tag.id), "tag_name": tag.name},
        after={},
    )


def get_vendor_analytics_stub(vendor_pk: str) -> dict[str, int]:
    """Return Phase A analytics stub for a vendor.

    Args:
        vendor_pk: UUID string of the vendor.

    Returns:
        Dict with zero-value analytics fields (Phase B will populate these).
    """
    return {
        "total_views": 0,
        "views_this_week": 0,
        "search_appearances": 0,
    }


# ---------------------------------------------------------------------------
# Business hours validation
# ---------------------------------------------------------------------------


def validate_business_hours(hours_data: dict[str, Any]) -> dict[str, Any]:
    """Validate business hours dict against BusinessHoursSchema.

    Args:
        hours_data: Raw dict with 7 day keys.

    Returns:
        Validated and serialised hours dict.

    Raises:
        ValueError: If the data fails Pydantic validation.
    """
    try:
        schema = BusinessHoursSchema(**hours_data)
        return schema.to_dict()
    except PydanticValidationError as e:
        raise ValueError(f"Invalid business_hours: {e}") from e


# ---------------------------------------------------------------------------
# Phone encryption helpers
# ---------------------------------------------------------------------------


def encrypt_phone(phone: str) -> bytes:
    """Encrypt a phone number string using AES-256-GCM.

    Args:
        phone: Raw phone number string.

    Returns:
        Encrypted bytes for storage in BinaryField.

    Raises:
        EncryptionError: If encryption fails.
    """
    return encrypt(phone)


def decrypt_phone(ciphertext: bytes) -> str:
    """Decrypt a phone number from BinaryField storage.

    Args:
        ciphertext: Encrypted bytes from BinaryField.

    Returns:
        Decrypted phone number string.

    Raises:
        EncryptionError: If decryption fails.
    """
    return decrypt(bytes(ciphertext))


# ---------------------------------------------------------------------------
# Vendor CRUD
# ---------------------------------------------------------------------------


@transaction.atomic
def create_vendor(
    business_name: str,
    slug: str,
    city_id: str,
    area_id: str,
    gps_lon: float,
    gps_lat: float,
    actor: Any,
    request: HttpRequest,
    phone: str = "",
    description: str = "",
    address_text: str = "",
    landmark_id: str | None = None,
    business_hours: dict[str, Any] | None = None,
    data_source: str = DataSource.MANUAL_ENTRY,
    storefront_photo_key: str = "",
) -> Vendor:
    """Create a new Vendor record.

    Phone is encrypted with AES-256-GCM before storage (R2).
    business_hours is validated via BusinessHoursSchema before storage.
    GPS point stored as Point(longitude, latitude) — lon/lat order.
    Every creation writes an AuditLog entry (R5).

    Args:
        business_name: Trading name of the business.
        slug: URL-safe identifier — must be unique.
        city_id: UUID string of the parent City.
        area_id: UUID string of the parent Area.
        gps_lon: GPS longitude.
        gps_lat: GPS latitude.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.
        phone: Raw phone number string (will be encrypted).
        description: Optional long-form description.
        address_text: Human-readable address.
        landmark_id: Optional UUID string of a Landmark.
        business_hours: Optional 7-day hours dict (validated by schema).
        data_source: DataSource value.

    Returns:
        Newly created Vendor instance.

    Raises:
        ValueError: If slug exists, business_hours invalid, or FK not found.
        EncryptionError: If phone encryption fails.
    """
    from apps.geo.models import Area, City, Landmark

    if Vendor.all_objects.filter(slug=slug).exists():
        raise ValueError(f"Vendor with slug '{slug}' already exists")

    try:
        city = City.objects.get(id=city_id)
    except City.DoesNotExist:
        raise ValueError(f"City '{city_id}' not found")

    try:
        area = Area.objects.get(id=area_id)
    except Area.DoesNotExist:
        raise ValueError(f"Area '{area_id}' not found")

    landmark = None
    if landmark_id:
        try:
            landmark = Landmark.objects.get(id=landmark_id)
        except Landmark.DoesNotExist:
            raise ValueError(f"Landmark '{landmark_id}' not found")

    validated_hours: dict[str, Any] = {}
    if business_hours:
        validated_hours = validate_business_hours(business_hours)

    phone_encrypted = encrypt_phone(phone) if phone else b""

    vendor = Vendor.objects.create(
        business_name=business_name.strip(),
        slug=slug.strip(),
        description=description,
        gps_point=Point(gps_lon, gps_lat, srid=4326),  # lon/lat order
        address_text=address_text,
        city=city,
        area=area,
        landmark=landmark,
        phone_number_encrypted=phone_encrypted,
        business_hours=validated_hours,
        data_source=data_source,
        storefront_photo_key=storefront_photo_key,
    )

    log_action(
        action="VENDOR_CREATED",
        actor=actor,
        target_obj=vendor,
        request=request,
        before={},
        after={
            "business_name": vendor.business_name,
            "slug": vendor.slug,
            "data_source": vendor.data_source,
            "qc_status": vendor.qc_status,
        },
    )
    return vendor


@transaction.atomic
def update_vendor(
    vendor: Vendor,
    updates: dict[str, Any],
    actor: Any,
    request: HttpRequest,
) -> Vendor:
    """Update a Vendor record.

    Phone is re-encrypted if provided in updates.
    business_hours is re-validated if provided.
    GPS point uses lon/lat order.

    Args:
        vendor: Vendor instance to update.
        updates: Dict of field names to new values.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Updated Vendor instance.

    Raises:
        ValueError: If business_hours is invalid.
        EncryptionError: If phone encryption fails.
    """
    before = {
        "business_name": vendor.business_name,
        "qc_status": vendor.qc_status,
        "is_deleted": vendor.is_deleted,
    }

    if "phone" in updates:
        vendor.phone_number_encrypted = encrypt_phone(updates.pop("phone"))

    if "business_hours" in updates:
        updates["business_hours"] = validate_business_hours(updates["business_hours"])

    if "gps_lon" in updates and "gps_lat" in updates:
        vendor.gps_point = Point(
            updates.pop("gps_lon"), updates.pop("gps_lat"), srid=4326
        )

    allowed_fields = {
        "business_name",
        "slug",
        "description",
        "address_text",
        "business_hours",
        "qc_notes",
        "data_source",
        "city_id",
        "area_id",
        "landmark_id",
        "storefront_photo_key",
        "claimed_status",
    }
    changed_fields: list[str] = []
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(vendor, field, value)
            changed_fields.append(field)

    # Always include gps_point and phone if they were updated above
    if "phone" in updates or vendor.phone_number_encrypted:
        changed_fields.append("phone_number_encrypted")
    if "gps_lon" in updates or "gps_lat" in updates:
        changed_fields.append("gps_point")

    # Deduplicate and always include updated_at
    save_fields = list(dict.fromkeys(changed_fields + ["updated_at"]))
    vendor.save(update_fields=save_fields)
    log_action(
        action="VENDOR_UPDATED",
        actor=actor,
        target_obj=vendor,
        request=request,
        before=before,
        after={"business_name": vendor.business_name, "qc_status": vendor.qc_status},
    )
    return vendor


@transaction.atomic
def soft_delete_vendor(vendor: Vendor, actor: Any, request: HttpRequest) -> None:
    """Soft-delete a Vendor — sets is_deleted=True, never hard-deletes (R6).

    Args:
        vendor: Vendor instance to soft-delete.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.
    """
    before = {"is_deleted": False, "business_name": vendor.business_name}
    vendor.delete()  # overridden delete() sets is_deleted=True
    log_action(
        action="VENDOR_DELETED",
        actor=actor,
        target_obj=vendor,
        request=request,
        before=before,
        after={"is_deleted": True},
    )


@transaction.atomic
def update_qc_status(
    vendor: Vendor,
    new_status: str,
    reviewer: Any,
    request: HttpRequest,
    notes: str = "",
) -> Vendor:
    """Update the QC status of a Vendor.

    Args:
        vendor: Vendor instance to update.
        new_status: New QCStatus value.
        reviewer: AdminUser performing the review.
        request: HTTP request for audit tracing.
        notes: Optional reviewer notes.

    Returns:
        Updated Vendor instance.

    Raises:
        ValueError: If new_status is not a valid QCStatus value.
    """
    valid_statuses = [s.value for s in QCStatus]
    if new_status not in valid_statuses:
        raise ValueError(
            f"Invalid QC status '{new_status}'. Must be one of {valid_statuses}"
        )

    if new_status == QCStatus.APPROVED:
        from apps.tags.models import TagType

        has_category_tag = vendor.tags.filter(
            tag_type=TagType.CATEGORY,
            is_active=True,
        ).exists()
        if not has_category_tag:
            raise ValueError(
                "Cannot approve vendor: at least one active CATEGORY tag must "
                "be assigned before approval. Assign a category tag first."
            )

    before = {"qc_status": vendor.qc_status, "qc_notes": vendor.qc_notes}

    vendor.qc_status = new_status
    vendor.qc_reviewed_by = reviewer
    vendor.qc_reviewed_at = timezone.now()
    vendor.qc_notes = notes
    vendor.save(
        update_fields=[
            "qc_status",
            "qc_reviewed_by",
            "qc_reviewed_at",
            "qc_notes",
            "updated_at",
        ]
    )

    log_action(
        action="VENDOR_QC_STATUS_CHANGED",
        actor=reviewer,
        target_obj=vendor,
        request=request,
        before=before,
        after={"qc_status": vendor.qc_status, "qc_notes": vendor.qc_notes},
    )
    return vendor
