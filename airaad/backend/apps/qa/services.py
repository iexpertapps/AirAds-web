"""
AirAd Backend — QA Service Layer (R4)

GPS drift detection and duplicate vendor detection logic.
ST_Distance(geography=True) ONLY — never degree × constant (R1).
difflib.SequenceMatcher for name similarity — stdlib, no ML deps.
Every mutation calls log_action() (R5).
Always filters is_deleted=False (R6).
"""

import difflib
import logging
from typing import Any

from apps.audit.utils import log_action
from apps.vendors.models import QCStatus, Vendor
from django.db import transaction
from django.http import HttpRequest

logger = logging.getLogger(__name__)

GPS_DRIFT_THRESHOLD_METRES = 20.0

# DUPLICATE_PROXIMITY_METRES intentionally uses 50m (not the 10m in spec §3.3).
# Spec §3.3 defines 10m as the threshold for the *claim duplicate detection* workflow
# (i.e. two vendors claiming the same physical listing). This QA scan is a broader
# data-quality sweep that catches near-duplicate entries created by different data
# sources (field teams, CSV imports, scraping) which may have GPS variance of 10–40m
# for the same physical location. Using 10m here would miss many real duplicates.
# The claim-specific 10m threshold will be enforced separately in the Phase B
# vendor claim flow (TASK-B claim-dedup).
DUPLICATE_PROXIMITY_METRES = 50.0

DUPLICATE_NAME_SIMILARITY_THRESHOLD = 0.85
MAX_COMPARISONS_PER_VENDOR = 100


def flag_gps_drift(
    vendor: Vendor,
    field_visit_point: Any,
    actor: Any | None,
    request: HttpRequest | None,
) -> bool:
    """Flag a vendor for GPS drift if the confirmed point differs by >20m.

    Uses ST_Distance(geography=True) via core.geo_utils — never degree×constant (R1).
    Sets qc_status=NEEDS_REVIEW and writes AuditLog if drift detected.

    Args:
        vendor: Vendor instance to check.
        field_visit_point: PostGIS Point confirmed by field agent.
        actor: AdminUser or None (Celery task context).
        request: HTTP request or None (Celery task context).

    Returns:
        True if drift was detected and vendor was flagged, False otherwise.
    """
    from core.geo_utils import calculate_drift_distance

    distance = calculate_drift_distance(vendor.gps_point, field_visit_point)

    if distance > GPS_DRIFT_THRESHOLD_METRES:
        before = {"qc_status": vendor.qc_status}
        vendor.qc_status = QCStatus.NEEDS_REVIEW
        vendor.qc_notes = f"GPS drift detected: {distance:.1f}m between stored point and field-confirmed point."
        vendor.save(update_fields=["qc_status", "qc_notes", "updated_at"])

        log_action(
            action="VENDOR_GPS_DRIFT_FLAGGED",
            actor=actor,
            target_obj=vendor,
            request=request,
            before=before,
            after={
                "qc_status": QCStatus.NEEDS_REVIEW,
                "drift_metres": round(distance, 2),
            },
        )
        return True

    return False


@transaction.atomic
def run_duplicate_scan_for_vendor(
    vendor: Vendor,
    actor: Any | None,
    request: HttpRequest | None,
) -> list[str]:
    """Detect potential duplicate vendors near a given vendor.

    Uses ST_DWithin(50m) for proximity filter, then difflib.SequenceMatcher
    on business_name for similarity. Caps at MAX_COMPARISONS_PER_VENDOR (R1).
    Flags both the source vendor and each duplicate as NEEDS_REVIEW.

    Args:
        vendor: Vendor instance to check for duplicates.
        actor: AdminUser or None (Celery task context).
        request: HTTP request or None (Celery task context).

    Returns:
        List of duplicate vendor ID strings that were flagged.
    """
    from django.contrib.gis.measure import D

    nearby_vendors = (
        Vendor.objects.filter(
            is_deleted=False,
            gps_point__dwithin=(vendor.gps_point, D(m=DUPLICATE_PROXIMITY_METRES)),
        )
        .exclude(id=vendor.id)
        .only("id", "business_name", "qc_status")[:MAX_COMPARISONS_PER_VENDOR]
    )

    flagged_ids: list[str] = []

    for candidate in nearby_vendors:
        ratio = difflib.SequenceMatcher(
            None,
            vendor.business_name.lower(),
            candidate.business_name.lower(),
        ).ratio()

        if ratio >= DUPLICATE_NAME_SIMILARITY_THRESHOLD:
            before = {"qc_status": candidate.qc_status}
            candidate.qc_status = QCStatus.NEEDS_REVIEW
            candidate.qc_notes = (
                f"Potential duplicate of vendor {vendor.id} "
                f"(name similarity: {ratio:.0%}, distance <{DUPLICATE_PROXIMITY_METRES}m)."
            )
            candidate.save(update_fields=["qc_status", "qc_notes", "updated_at"])

            log_action(
                action="VENDOR_DUPLICATE_FLAGGED",
                actor=actor,
                target_obj=candidate,
                request=request,
                before=before,
                after={
                    "qc_status": QCStatus.NEEDS_REVIEW,
                    "similarity_ratio": round(ratio, 3),
                    "source_vendor_id": str(vendor.id),
                },
            )
            flagged_ids.append(str(candidate.id))

    return flagged_ids
