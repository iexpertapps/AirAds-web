"""
AirAd Backend — Imports Service Layer (R4, R8, R9)

CSV content is NEVER passed over the Celery broker — only batch_id (R8).
error_log is capped at 1000 entries via append_error_log() (R9).
Every mutation calls log_action() (R5).
"""

import logging
from typing import IO, Any

from django.db import transaction
from django.http import HttpRequest

from apps.audit.utils import log_action
from core.file_validation import FileValidationError, validate_uploaded_file
from core.storage import upload_file_to_s3

from .models import ImportBatch, ImportStatus

logger = logging.getLogger(__name__)

ERROR_LOG_CAP = 1000


def append_error_log(batch: ImportBatch, error: dict[str, Any]) -> None:
    """Append a per-row error to the batch error_log, capped at 1000 entries (R9).

    Silently drops errors beyond the cap — never raises.
    Saves only the error_log and error_count fields for efficiency.

    Args:
        batch: ImportBatch instance to update.
        error: Dict describing the error (e.g. {"row": 5, "field": "phone", "msg": "..."}).
    """
    if len(batch.error_log) >= ERROR_LOG_CAP:
        return

    batch.error_log.append(error)
    batch.error_count = len(batch.error_log)
    batch.save(update_fields=["error_log", "error_count", "updated_at"])


@transaction.atomic
def create_import_batch(
    file: IO[bytes],
    filename: str,
    actor: Any,
    request: HttpRequest,
) -> ImportBatch:
    """Upload a CSV file to S3 and create an ImportBatch record.

    The CSV file is uploaded to S3 and only the S3 key is stored.
    CSV content is NEVER passed to the Celery task — only batch_id (R8).
    The Celery task is dispatched after the DB record is committed.

    Args:
        file: File-like object (binary mode) of the uploaded CSV.
        filename: Original filename for logging purposes.
        actor: AdminUser who uploaded the file.
        request: HTTP request for audit tracing.

    Returns:
        Newly created ImportBatch instance with status=QUEUED.

    Raises:
        StorageError: If S3 upload fails.
    """
    from apps.imports.tasks import process_import_batch

    # Validate file type (magic bytes) and size before uploading to S3
    try:
        validate_uploaded_file(
            file=file,
            filename=filename,
            allowed_types=["text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
        )
    except FileValidationError as e:
        raise ValueError(f"File validation failed: {e}") from e

    s3_key = upload_file_to_s3(file, prefix="imports")

    batch = ImportBatch.objects.create(
        file_key=s3_key,
        status=ImportStatus.QUEUED,
        created_by=actor,
    )

    log_action(
        action="IMPORT_BATCH_CREATED",
        actor=actor,
        target_obj=batch,
        request=request,
        before={},
        after={
            "file_key": s3_key,
            "filename": filename,
            "status": ImportStatus.QUEUED,
        },
    )

    # Dispatch Celery task — passes batch_id ONLY, never CSV content (R8)
    process_import_batch.delay(str(batch.id))

    return batch


def get_batch_or_404(batch_id: str, actor: Any) -> ImportBatch:
    """Retrieve an ImportBatch by ID, scoped to the requesting actor.

    Args:
        batch_id: UUID string of the ImportBatch.
        actor: AdminUser requesting the batch (SUPER_ADMIN sees all).

    Returns:
        ImportBatch instance.

    Raises:
        ImportBatch.DoesNotExist: If not found.
    """
    from apps.accounts.models import AdminRole

    qs = ImportBatch.objects.select_related("created_by", "area")
    if getattr(actor, "role", None) != AdminRole.SUPER_ADMIN:
        qs = qs.filter(created_by=actor)

    return qs.get(id=batch_id)
