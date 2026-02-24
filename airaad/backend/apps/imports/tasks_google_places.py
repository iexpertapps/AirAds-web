"""
Celery task for Google Places import.
Receives ONLY batch_id — all params live on ImportBatch record.

Idempotency:
  - Skips if batch is PROCESSING (another worker has it) or DONE.
  - FAILED batches are resumable — the service uses processed_place_ids
    checkpoint to skip already-completed items.
"""

import logging

from apps.imports.models import ImportBatch
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="imports.process_google_places_import",
)
def process_google_places_import(self, batch_id: str) -> dict:
    """
    Idempotency (L6):
      - PROCESSING: skip (another worker owns it)
      - DONE: skip (already complete)
      - FAILED: resume (service reads checkpoint from processed_place_ids)
      - QUEUED: start fresh
    Retries up to 3 times on failure with exponential backoff.
    """
    try:
        batch = ImportBatch.objects.get(id=batch_id)
    except ImportBatch.DoesNotExist:
        logger.error(f"ImportBatch {batch_id} not found")
        return {"error": "not_found"}

    if batch.status == "PROCESSING":
        logger.warning(
            f"Batch {batch_id} already PROCESSING — skipping (another worker)"
        )
        return {"status": batch.status, "skipped": True}

    if batch.status == "DONE":
        logger.info(f"Batch {batch_id} already DONE — skipping")
        return {"status": batch.status, "skipped": True}

    # FAILED batches are resumable — checkpoint in processed_place_ids
    if batch.status == "FAILED":
        logger.info(
            f"Batch {batch_id} resuming from FAILED state | "
            f"checkpoint={len(batch.processed_place_ids)} places already done"
        )

    from apps.imports.google_places_service import GooglePlacesImportService

    try:
        service = GooglePlacesImportService(batch=batch)
        completed = service.run()
        return {
            "status": completed.status,
            "processed_rows": completed.processed_rows,
            "error_count": completed.error_count,
        }
    except Exception as exc:
        logger.exception(f"Google Places task failed for batch {batch_id}")
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
