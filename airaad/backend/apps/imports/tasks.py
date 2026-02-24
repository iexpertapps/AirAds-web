"""
AirAd Backend — Import Celery Tasks

process_import_batch: reads CSV from S3 via batch_id ONLY — never from broker payload (R8).
CSV content is streamed from S3 using boto3 StreamingBody — never loaded fully into memory.
Per-row errors appended via append_error_log() — capped at 1000 (R9).
Retry with exponential backoff: countdown = 2**retries * 60 seconds.
"""

import csv
import io
import logging
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from celery import shared_task
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

# Required CSV columns — must be present in header row
REQUIRED_COLUMNS: frozenset[str] = frozenset({
    "business_name",
    "longitude",
    "latitude",
    "city_slug",
    "area_slug",
})


def _validate_row(row: dict[str, str], row_num: int) -> list[dict[str, Any]]:
    """Validate a single CSV row and return a list of error dicts.

    Args:
        row: Dict of column name → raw string value from csv.DictReader.
        row_num: 1-indexed row number for error reporting.

    Returns:
        List of error dicts. Empty list means the row is valid.
    """
    errors: list[dict[str, Any]] = []

    business_name = row.get("business_name", "").strip()
    if not business_name:
        errors.append({"row": row_num, "field": "business_name", "msg": "business_name is required"})

    for coord_field in ("longitude", "latitude"):
        raw = row.get(coord_field, "").strip()
        if not raw:
            errors.append({"row": row_num, "field": coord_field, "msg": f"{coord_field} is required"})
        else:
            try:
                val = float(raw)
            except ValueError:
                errors.append({
                    "row": row_num, "field": coord_field,
                    "msg": f"{coord_field} must be a number, got '{raw}'"
                })
            else:
                # Reject null-island and out-of-range coordinates (spec §8.1 GPS validation)
                if coord_field == "longitude" and not (-180.0 < val < 180.0):
                    errors.append({"row": row_num, "field": coord_field, "msg": f"longitude {val} is out of valid range (-180, 180)"})
                elif coord_field == "latitude" and not (-90.0 < val < 90.0):
                    errors.append({"row": row_num, "field": coord_field, "msg": f"latitude {val} is out of valid range (-90, 90)"})
                elif val == 0.0:
                    errors.append({"row": row_num, "field": coord_field, "msg": f"{coord_field} is 0.0 — likely a null-island placeholder, not a real GPS coordinate"})

    for slug_field in ("city_slug", "area_slug"):
        if not row.get(slug_field, "").strip():
            errors.append({"row": row_num, "field": slug_field, "msg": f"{slug_field} is required"})

    return errors


@transaction.atomic
def _process_row(row: dict[str, str], row_num: int, batch: Any) -> bool:
    """Process a single validated CSV row — create or update a Vendor.

    Uses select_for_update() to prevent duplicate creation under concurrent tasks.
    Phone is encrypted in vendors/services.py — never here.

    Args:
        row: Validated CSV row dict.
        row_num: 1-indexed row number for logging.
        batch: ImportBatch instance (for created_by actor).

    Returns:
        True if the row was processed successfully, False on error.
    """
    from apps.geo.models import Area, City
    from apps.vendors.models import Vendor
    from apps.vendors.services import create_vendor
    from django.utils.text import slugify

    try:
        city = City.objects.get(slug=row["city_slug"].strip())
    except City.DoesNotExist:
        return False

    try:
        area = Area.objects.get(slug=row["area_slug"].strip(), city=city)
    except Area.DoesNotExist:
        return False

    business_name = row["business_name"].strip()
    base_slug = slugify(business_name)
    slug = base_slug

    # Ensure unique slug — use select_for_update to prevent concurrent
    # imports from creating duplicate slugs under race conditions.
    with transaction.atomic():
        if Vendor.all_objects.select_for_update().filter(slug=slug).exists():
            slug = f"{base_slug}-{row_num}"

    create_vendor(
        business_name=business_name,
        slug=slug,
        city_id=str(city.id),
        area_id=str(area.id),
        gps_lon=float(row["longitude"]),
        gps_lat=float(row["latitude"]),
        actor=batch.created_by,
        request=None,  # Celery context — no HTTP request
        phone=row.get("phone", "").strip(),
        description=row.get("description", "").strip(),
        address_text=row.get("address_text", "").strip(),
        data_source="CSV_IMPORT",
    )
    return True


@shared_task(bind=True, max_retries=3, name="apps.imports.tasks.process_import_batch")
def process_import_batch(self: Any, batch_id: str) -> None:
    """Process a CSV import batch by streaming the file from S3.

    Receives batch_id ONLY — CSV content is NEVER passed over the broker (R8).
    Streams CSV from S3 using boto3 StreamingBody — never fully loaded into memory.
    Per-row errors are appended via append_error_log() — capped at 1000 entries (R9).
    Retries up to 3 times with exponential backoff: countdown = 2**retries * 60s.

    Args:
        batch_id: UUID string of the ImportBatch to process.
    """
    from apps.imports.models import ImportBatch, ImportStatus
    from apps.imports.services import append_error_log

    logger.info("Import task started", extra={"batch_id": batch_id})

    # --- Fetch batch ---
    try:
        batch = ImportBatch.objects.select_related("created_by").get(id=batch_id)
    except ImportBatch.DoesNotExist:
        logger.error("ImportBatch not found — aborting", extra={"batch_id": batch_id})
        return

    # --- Idempotency guard ---
    if batch.status == ImportStatus.PROCESSING:
        logger.warning("Batch already processing — idempotency guard hit", extra={"batch_id": batch_id})
        return

    # --- Mark as PROCESSING ---
    batch.status = ImportStatus.PROCESSING
    batch.save(update_fields=["status", "updated_at"])

    # --- Stream CSV from S3 ---
    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        response = s3_client.get_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=batch.file_key,
        )
        streaming_body = response["Body"]
    except (BotoCoreError, ClientError) as exc:
        logger.error(
            "S3 fetch failed — retrying",
            extra={"batch_id": batch_id, "error": str(exc)},
        )
        batch.status = ImportStatus.FAILED
        batch.save(update_fields=["status", "updated_at"])
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)

    # --- Parse and process CSV ---
    processed = 0
    errors_total = 0

    try:
        with streaming_body as body:
            text_stream = io.TextIOWrapper(body, encoding="utf-8-sig", errors="replace")
            reader = csv.DictReader(text_stream)

            # Validate header columns
            if reader.fieldnames is None:
                raise ValueError("CSV file is empty or has no header row")

            missing_cols = REQUIRED_COLUMNS - set(reader.fieldnames)
            if missing_cols:
                raise ValueError(f"CSV missing required columns: {sorted(missing_cols)}")

            row_num = 0
            for row_num, row in enumerate(reader, start=1):
                # Per-row validation
                row_errors = _validate_row(row, row_num)
                if row_errors:
                    for err in row_errors:
                        append_error_log(batch, err)
                    errors_total += len(row_errors)
                    continue

                # Process row — create vendor
                try:
                    success = _process_row(row, row_num, batch)
                    if not success:
                        append_error_log(batch, {
                            "row": row_num,
                            "field": "city_slug/area_slug",
                            "msg": f"City '{row.get('city_slug')}' or Area '{row.get('area_slug')}' not found",
                        })
                        errors_total += 1
                    else:
                        processed += 1
                except Exception as row_exc:
                    append_error_log(batch, {
                        "row": row_num,
                        "field": "__row__",
                        "msg": str(row_exc),
                    })
                    errors_total += 1
                    logger.warning(
                        "Row processing error",
                        extra={"batch_id": batch_id, "row": row_num, "error": str(row_exc)},
                    )

                # Update progress every 100 rows
                if row_num % 100 == 0:
                    batch.processed_rows = processed
                    batch.save(update_fields=["processed_rows", "updated_at"])

    except ValueError as exc:
        logger.error(
            "CSV parse error — marking FAILED",
            extra={"batch_id": batch_id, "error": str(exc)},
        )
        batch.status = ImportStatus.FAILED
        append_error_log(batch, {"row": 0, "field": "__header__", "msg": str(exc)})
        batch.save(update_fields=["status", "updated_at"])
        return

    # --- Mark DONE ---
    batch.status = ImportStatus.DONE
    batch.total_rows = row_num
    batch.processed_rows = processed
    batch.error_count = errors_total
    batch.save(update_fields=["status", "total_rows", "processed_rows", "error_count", "updated_at"])

    logger.info(
        "Import batch complete",
        extra={
            "batch_id": batch_id,
            "processed": processed,
            "errors": errors_total,
            "total": batch.total_rows,
        },
    )
