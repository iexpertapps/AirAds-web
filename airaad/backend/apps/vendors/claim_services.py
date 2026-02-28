"""
AirAd Backend — Vendor Claim Flow Service (Phase B §3.2)

All claim logic lives here — views only call these functions.
Claim lifecycle: UNCLAIMED → CLAIM_PENDING → CLAIMED / CLAIM_REJECTED.
Every mutation calls log_action() (R5).
All multi-step mutations wrapped in @transaction.atomic.
"""

import logging
from typing import Any

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.audit.utils import log_action

logger = logging.getLogger(__name__)


@transaction.atomic
def submit_claim(
    vendor_id: str,
    customer_id: str,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Submit a claim request for a vendor listing.

    A customer (authenticated via OTP) claims ownership of an unclaimed vendor.
    Sets claimed_status to CLAIM_PENDING and assigns the owner FK.

    Args:
        vendor_id: UUID string of the vendor to claim.
        customer_id: UUID string of the CustomerUser submitting the claim.
        request: HTTP request for audit tracing.

    Returns:
        Dict with claim submission status.

    Raises:
        ValueError: If vendor not found, already claimed/pending, or customer not found.
    """
    from apps.accounts.models import CustomerUser
    from apps.vendors.models import ClaimedStatus, Vendor

    try:
        vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    except Vendor.DoesNotExist:
        raise ValueError("Vendor not found")

    if vendor.claimed_status != ClaimedStatus.UNCLAIMED:
        raise ValueError(
            f"Vendor is already {vendor.claimed_status}. Only UNCLAIMED vendors can be claimed."
        )

    try:
        customer = CustomerUser.objects.get(id=customer_id, is_active=True)
    except CustomerUser.DoesNotExist:
        raise ValueError("Customer user not found or inactive")

    if not customer.is_phone_verified:
        raise ValueError("Phone must be verified before claiming a vendor")

    existing_claim = Vendor.objects.filter(
        owner=customer,
        claimed_status__in=[ClaimedStatus.CLAIM_PENDING, ClaimedStatus.CLAIMED],
    ).first()
    if existing_claim:
        raise ValueError(
            f"You already have an active claim on '{existing_claim.business_name}'. "
            "One vendor per customer at this time."
        )

    before = {
        "claimed_status": vendor.claimed_status,
        "owner": None,
    }

    vendor.claimed_status = ClaimedStatus.CLAIM_PENDING
    vendor.owner = customer
    vendor.save(update_fields=["claimed_status", "owner", "updated_at"])

    log_action(
        action="VENDOR_CLAIM_SUBMITTED",
        actor=None,
        target_obj=vendor,
        request=request,
        before=before,
        after={
            "claimed_status": ClaimedStatus.CLAIM_PENDING,
            "owner_id": str(customer.id),
        },
    )

    return {
        "vendor_id": str(vendor.id),
        "business_name": vendor.business_name,
        "claimed_status": vendor.claimed_status,
        "message": "Claim submitted successfully. An admin will review your request.",
    }


@transaction.atomic
def withdraw_claim(
    vendor_id: str,
    customer_id: str,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Withdraw a pending claim on a vendor.

    Only the owner who submitted the claim can withdraw it.

    Args:
        vendor_id: UUID string of the vendor.
        customer_id: UUID string of the CustomerUser withdrawing.
        request: HTTP request for audit tracing.

    Returns:
        Dict with withdrawal status.

    Raises:
        ValueError: If vendor not found or claim is not pending by this customer.
    """
    from apps.vendors.models import ClaimedStatus, Vendor

    try:
        vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    except Vendor.DoesNotExist:
        raise ValueError("Vendor not found")

    if vendor.claimed_status != ClaimedStatus.CLAIM_PENDING:
        raise ValueError("Only CLAIM_PENDING vendors can have claims withdrawn")

    if str(vendor.owner_id) != customer_id:
        raise ValueError("You are not the claimant for this vendor")

    before = {
        "claimed_status": vendor.claimed_status,
        "owner_id": str(vendor.owner_id),
    }

    vendor.claimed_status = ClaimedStatus.UNCLAIMED
    vendor.owner = None
    vendor.save(update_fields=["claimed_status", "owner", "updated_at"])

    log_action(
        action="VENDOR_CLAIM_WITHDRAWN",
        actor=None,
        target_obj=vendor,
        request=request,
        before=before,
        after={"claimed_status": ClaimedStatus.UNCLAIMED, "owner": None},
    )

    return {
        "vendor_id": str(vendor.id),
        "business_name": vendor.business_name,
        "claimed_status": vendor.claimed_status,
        "message": "Claim withdrawn successfully.",
    }


def get_claimable_vendors(
    lat: float | None = None,
    lng: float | None = None,
    query: str = "",
) -> list[dict[str, Any]]:
    """Search for unclaimed vendors that can be claimed.

    Used by the claim flow UI to present claimable vendor listings.

    Args:
        lat: Optional latitude for proximity sorting.
        lng: Optional longitude for proximity sorting.
        query: Optional text search on business_name.

    Returns:
        List of vendor dicts with basic info.
    """
    from apps.vendors.models import ClaimedStatus, Vendor

    qs = Vendor.objects.filter(
        is_deleted=False,
        claimed_status=ClaimedStatus.UNCLAIMED,
        qc_status__in=["APPROVED", "PENDING"],  # Include PENDING for testing, change to APPROVED only for production
    ).select_related("city", "area")

    if query:
        qs = qs.filter(business_name__icontains=query)

    if lat and lng:
        # Use proper GIS syntax for PointField coordinate filtering
        from django.contrib.gis.geos import Point
        
        # Create a bounding box polygon for the search area
        lat_delta = 5.0  # ~555km
        lng_delta = 5.0  # ~555km
        
        min_lat, max_lat = lat - lat_delta, lat + lat_delta
        min_lng, max_lng = lng - lng_delta, lng + lng_delta
        
        # Create a polygon representing the bounding box
        from django.contrib.gis.geos import Polygon
        bbox = Polygon.from_bbox((min_lng, min_lat, max_lng, max_lat))
        
        qs = qs.filter(gps_point__intersects=bbox)

    results = []
    for v in qs[:50]:
        gps = None
        if v.gps_point:
            gps = {"longitude": v.gps_point.x, "latitude": v.gps_point.y}

        results.append({
            "id": str(v.id),
            "business_name": v.business_name,
            "slug": v.slug,
            "gps_point": gps,
            "address_text": v.address_text,
            "city_name": v.city.name if v.city else "",
            "area_name": v.area.name if v.area else "",
        })

    return results


@transaction.atomic
def verify_claim_otp(
    vendor_id: str,
    otp_code: str,
    customer_id: str,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Verify OTP for automated claim verification path.

    The vendor's registered phone receives an OTP. The claimant enters it here
    to prove they have access to the business phone number.

    Args:
        vendor_id: UUID of the vendor being claimed.
        otp_code: The OTP code entered by the user.
        customer_id: UUID of the CustomerUser.
        request: HTTP request for audit tracing.

    Returns:
        Dict with verification result.

    Raises:
        ValueError: If vendor not found, claim not pending, or OTP invalid.
    """
    from apps.vendors.models import ClaimedStatus, Vendor

    try:
        vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    except Vendor.DoesNotExist:
        raise ValueError("Vendor not found")

    if vendor.claimed_status != ClaimedStatus.CLAIM_PENDING:
        raise ValueError("Vendor does not have a pending claim")

    if str(vendor.owner_id) != customer_id:
        raise ValueError("You are not the claimant for this vendor")

    # Verify OTP against the vendor's phone number
    from apps.accounts.otp_services import verify_otp_code

    phone = vendor.phone_number
    if not phone:
        raise ValueError("Vendor has no registered phone number for OTP verification")

    is_valid = verify_otp_code(phone, otp_code)
    if not is_valid:
        raise ValueError("Invalid or expired OTP code")

    # Auto-approve claim via OTP path
    before = {"claimed_status": vendor.claimed_status}
    vendor.claimed_status = ClaimedStatus.CLAIMED
    vendor.save(update_fields=["claimed_status", "updated_at"])

    log_action(
        action="VENDOR_CLAIM_OTP_VERIFIED",
        actor=None,
        target_obj=vendor,
        request=request,
        before=before,
        after={"claimed_status": ClaimedStatus.CLAIMED},
    )

    return {
        "vendor_id": str(vendor.id),
        "business_name": vendor.business_name,
        "claimed_status": vendor.claimed_status,
        "message": "OTP verified. Claim approved automatically.",
    }


@transaction.atomic
def upload_claim_proof(
    vendor_id: str,
    customer_id: str,
    proof_s3_key: str,
    license_s3_key: str = "",
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Upload proof documents for manual claim verification path.

    The claimant uploads a storefront photo and optionally a business license.
    The claim remains in CLAIM_PENDING for admin review.

    Args:
        vendor_id: UUID of the vendor being claimed.
        customer_id: UUID of the CustomerUser.
        proof_s3_key: S3 key for the storefront proof photo.
        license_s3_key: Optional S3 key for business license document.
        request: HTTP request for audit tracing.

    Returns:
        Dict with upload status.

    Raises:
        ValueError: If vendor not found or claim not pending.
    """
    from apps.vendors.models import ClaimedStatus, Vendor

    try:
        vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    except Vendor.DoesNotExist:
        raise ValueError("Vendor not found")

    if vendor.claimed_status != ClaimedStatus.CLAIM_PENDING:
        raise ValueError("Vendor does not have a pending claim")

    if str(vendor.owner_id) != customer_id:
        raise ValueError("You are not the claimant for this vendor")

    # Store proof references in vendor metadata
    proof_data = {
        "proof_s3_key": proof_s3_key,
        "license_s3_key": license_s3_key,
        "uploaded_at": timezone.now().isoformat(),
    }

    # Update vendor's metadata with proof info
    metadata = vendor.metadata or {}
    metadata["claim_proof"] = proof_data
    vendor.metadata = metadata
    vendor.save(update_fields=["metadata", "updated_at"])

    log_action(
        action="VENDOR_CLAIM_PROOF_UPLOADED",
        actor=None,
        target_obj=vendor,
        request=request,
        before={},
        after=proof_data,
    )

    return {
        "vendor_id": str(vendor.id),
        "business_name": vendor.business_name,
        "claimed_status": vendor.claimed_status,
        "message": "Proof uploaded. An admin will review your claim.",
    }


def get_claim_status(vendor_id: str) -> dict[str, Any]:
    """Get the current claim status for a vendor.

    Args:
        vendor_id: UUID of the vendor.

    Returns:
        Dict with claim status details.

    Raises:
        ValueError: If vendor not found.
    """
    from apps.vendors.models import Vendor

    try:
        vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    except Vendor.DoesNotExist:
        raise ValueError("Vendor not found")

    has_proof = False
    if vendor.metadata and "claim_proof" in (vendor.metadata or {}):
        has_proof = True

    return {
        "vendor_id": str(vendor.id),
        "business_name": vendor.business_name,
        "claimed_status": vendor.claimed_status,
        "owner_id": str(vendor.owner_id) if vendor.owner_id else None,
        "has_proof_uploaded": has_proof,
        "updated_at": vendor.updated_at.isoformat(),
    }
