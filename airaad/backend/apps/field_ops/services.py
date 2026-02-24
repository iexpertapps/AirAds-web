"""
AirAd Backend — Field Ops Service Layer (R4)

All field visit and photo business logic lives here.
Every mutation calls log_action() (R5).
FieldPhoto.s3_key stores S3 key only — presigned URL generated on read.
"""

import logging
from typing import IO, Any

from apps.audit.utils import log_action
from core.storage import generate_presigned_url, upload_file_to_s3
from django.contrib.gis.geos import Point
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from .models import FieldPhoto, FieldVisit

logger = logging.getLogger(__name__)


@transaction.atomic
def create_field_visit(
    vendor_id: str,
    agent: Any,
    request: HttpRequest,
    visited_at: Any | None = None,
    visit_notes: str = "",
    gps_lon: float | None = None,
    gps_lat: float | None = None,
) -> FieldVisit:
    """Record a new field visit to a vendor location.

    Args:
        vendor_id: UUID string of the Vendor being visited.
        agent: AdminUser (FIELD_AGENT role) conducting the visit.
        request: HTTP request for audit tracing.
        visited_at: Datetime of the visit. Defaults to now().
        visit_notes: Free-text notes from the agent.
        gps_lon: Optional confirmed GPS longitude.
        gps_lat: Optional confirmed GPS latitude.

    Returns:
        Newly created FieldVisit instance.

    Raises:
        ValueError: If vendor not found.
    """
    from apps.vendors.models import Vendor

    try:
        vendor = Vendor.objects.get(id=vendor_id)
    except Vendor.DoesNotExist:
        raise ValueError(f"Vendor '{vendor_id}' not found")

    gps_point = None
    if gps_lon is not None and gps_lat is not None:
        gps_point = Point(gps_lon, gps_lat, srid=4326)

    visit = FieldVisit.objects.create(
        vendor=vendor,
        agent=agent,
        visited_at=visited_at or timezone.now(),
        visit_notes=visit_notes,
        gps_confirmed_point=gps_point,
    )

    log_action(
        action="FIELD_VISIT_CREATED",
        actor=agent,
        target_obj=visit,
        request=request,
        before={},
        after={
            "vendor_id": str(vendor_id),
            "agent_id": str(agent.id),
            "visited_at": visit.visited_at.isoformat(),
        },
    )
    return visit


@transaction.atomic
def upload_field_photo(
    visit: FieldVisit,
    file: IO[bytes],
    actor: Any,
    request: HttpRequest,
    caption: str = "",
) -> FieldPhoto:
    """Upload a photo taken during a field visit to S3 and create a FieldPhoto record.

    Stores only the S3 key — never a public URL (R).
    Presigned URL is generated on read via get_field_photo_url().

    Args:
        visit: FieldVisit instance this photo belongs to.
        file: Binary file-like object of the photo.
        actor: AdminUser uploading the photo.
        request: HTTP request for audit tracing.
        caption: Optional caption string.

    Returns:
        Newly created FieldPhoto instance.

    Raises:
        StorageError: If S3 upload fails.
    """
    s3_key = upload_file_to_s3(file, prefix=f"field-photos/{visit.id}")

    photo = FieldPhoto.objects.create(
        field_visit=visit,
        s3_key=s3_key,
        caption=caption,
    )

    log_action(
        action="FIELD_PHOTO_UPLOADED",
        actor=actor,
        target_obj=photo,
        request=request,
        before={},
        after={"visit_id": str(visit.id), "s3_key": s3_key},
    )
    return photo


def get_field_photo_url(photo: FieldPhoto, expiry: int = 3600) -> str:
    """Generate a presigned S3 URL for a FieldPhoto.

    Args:
        photo: FieldPhoto instance.
        expiry: URL expiry in seconds (default 3600).

    Returns:
        Presigned HTTPS URL string.

    Raises:
        StorageError: If presigned URL generation fails.
    """
    return generate_presigned_url(photo.s3_key, expiry=expiry)
