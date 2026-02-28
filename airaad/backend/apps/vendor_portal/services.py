"""
AirAd Backend — Vendor Portal Service Layer (Phase C)

All vendor portal business logic lives here — views only call these functions.
Every mutation calls log_action() (R5).
"""

import logging
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.audit.utils import log_action
from core.encryption import decrypt, encrypt
from core.utils import get_client_ip, vendor_has_feature

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# C-1: Vendor Portal Authentication
# ---------------------------------------------------------------------------

def vendor_send_otp(phone: str, request: HttpRequest | None = None) -> dict[str, Any]:
    """Send OTP for vendor portal login.

    Delegates to the shared OTP service with purpose=VENDOR_LOGIN.

    Args:
        phone: Raw phone number string.
        request: HTTP request for audit tracing.

    Returns:
        Dict with OTP send status.
    """
    from apps.accounts.otp_services import send_otp

    return send_otp(phone=phone, purpose="VENDOR_LOGIN", request=request)


@transaction.atomic
def vendor_verify_otp(
    phone: str,
    otp_code: str,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Verify OTP and log in the vendor.

    On success, finds the CustomerUser and the Vendor they own.
    Returns JWT tokens with vendor_id in claims.

    Args:
        phone: Raw phone number string.
        otp_code: The OTP code to verify.
        request: HTTP request for audit tracing.

    Returns:
        Dict with JWT tokens, vendor info, and user info.

    Raises:
        ValueError: If OTP invalid, or user has no claimed vendor.
    """
    from apps.accounts.otp_services import verify_otp

    result = verify_otp(
        phone=phone,
        otp_code=otp_code,
        purpose="VENDOR_LOGIN",
        request=request,
    )

    customer_id = result["user"]["id"]

    from apps.accounts.models import CustomerUser
    from apps.vendors.models import ClaimedStatus, Vendor

    customer = CustomerUser.objects.get(id=customer_id)

    vendor = Vendor.objects.filter(
        owner=customer,
        claimed_status=ClaimedStatus.CLAIMED,
        is_deleted=False,
    ).first()

    if vendor is None:
        vendor = Vendor.objects.filter(
            owner=customer,
            claimed_status=ClaimedStatus.CLAIM_PENDING,
            is_deleted=False,
        ).first()

    # Determine activation stage for the frontend onboarding flow
    activation_stage = "UNCLAIMED"
    vendor_id = None
    subscription_level = "SILVER"
    if vendor is not None:
        vendor_id = str(vendor.id)
        subscription_level = vendor.subscription_level or "SILVER"
        if vendor.claimed_status == ClaimedStatus.CLAIM_PENDING:
            activation_stage = "CLAIM_PENDING"
        elif vendor.claimed_status == ClaimedStatus.CLAIMED:
            has_profile = bool(getattr(vendor, "phone_number", "") or getattr(vendor, "business_hours", ""))
            activation_stage = "PROFILE_COMPLETE" if has_profile else "CLAIMED"

    # Return flat structure matching frontend VerifyOTPResponse interface
    return {
        "access": result["tokens"]["access"],
        "refresh": result["tokens"]["refresh"],
        "user": {
            "id": customer_id,
            "phone": phone,
            "full_name": result["user"]["full_name"] or "",
            "vendor_id": vendor_id,
            "activation_stage": activation_stage,
            "subscription_level": subscription_level,
        },
    }


def vendor_get_me(customer_id: str) -> dict[str, Any]:
    """Get the current vendor user's profile and linked vendor.

    Args:
        customer_id: UUID string of the CustomerUser.

    Returns:
        Dict with user info and linked vendor.
    """
    from apps.accounts.models import CustomerUser
    from apps.vendors.models import ClaimedStatus, Vendor

    customer = CustomerUser.objects.get(id=customer_id)

    vendor = Vendor.objects.filter(
        owner=customer,
        claimed_status__in=[ClaimedStatus.CLAIMED, ClaimedStatus.CLAIM_PENDING],
        is_deleted=False,
    ).select_related("city", "area", "vendor_subscription").first()

    vendor_data = None
    if vendor:
        vendor_data = {
            "vendor_id": str(vendor.id),
            "business_name": vendor.business_name,
            "slug": vendor.slug,
            "claimed_status": vendor.claimed_status,
            "subscription_level": vendor.subscription_level,
            "is_verified": vendor.is_verified,
            "city_name": vendor.city.name if vendor.city else "",
            "area_name": vendor.area.name if vendor.area else "",
        }

    return {
        "user": {
            "id": str(customer.id),
            "full_name": customer.full_name,
            "email": customer.email,
            "user_type": customer.user_type,
            "is_phone_verified": customer.is_phone_verified,
        },
        "vendor": vendor_data,
    }


# ---------------------------------------------------------------------------
# C-2: Vendor Portal Profile APIs
# ---------------------------------------------------------------------------

def get_vendor_profile(vendor_id: str) -> dict[str, Any]:
    """Get the full vendor profile for portal display.

    Args:
        vendor_id: UUID string of the Vendor.

    Returns:
        Full profile dict.
    """
    from apps.vendors.models import Vendor

    vendor = Vendor.objects.select_related(
        "city", "area", "landmark", "vendor_subscription"
    ).get(id=vendor_id, is_deleted=False)

    gps = None
    if vendor.gps_point:
        gps = {"longitude": vendor.gps_point.x, "latitude": vendor.gps_point.y}

    phone_masked = ""
    if vendor.phone_number_encrypted:
        try:
            plain = decrypt(bytes(vendor.phone_number_encrypted))
            if plain and len(plain) > 4:
                phone_masked = "*" * (len(plain) - 4) + plain[-4:]
        except Exception:
            pass

    from core.storage import generate_presigned_url

    logo_url = ""
    if vendor.logo_key:
        try:
            logo_url = generate_presigned_url(vendor.logo_key)
        except Exception:
            pass

    cover_url = ""
    if vendor.cover_photo_key:
        try:
            cover_url = generate_presigned_url(vendor.cover_photo_key)
        except Exception:
            pass

    storefront_url = ""
    if vendor.storefront_photo_key:
        try:
            storefront_url = generate_presigned_url(vendor.storefront_photo_key)
        except Exception:
            pass

    return {
        "id": str(vendor.id),
        "business_name": vendor.business_name,
        "slug": vendor.slug,
        "description": vendor.description,
        "gps_point": gps,
        "address_text": vendor.address_text,
        "city_name": vendor.city.name if vendor.city else "",
        "area_name": vendor.area.name if vendor.area else "",
        "landmark_name": vendor.landmark.name if vendor.landmark else "",
        "phone_masked": phone_masked,
        "business_hours": vendor.business_hours,
        "claimed_status": vendor.claimed_status,
        "claimed_at": vendor.claimed_at.isoformat() if vendor.claimed_at else None,
        "is_verified": vendor.is_verified,
        "subscription_level": vendor.subscription_level,
        "subscription_valid_until": (
            vendor.subscription_valid_until.isoformat()
            if vendor.subscription_valid_until
            else None
        ),
        "offers_delivery": vendor.offers_delivery,
        "offers_pickup": vendor.offers_pickup,
        "activation_stage": vendor.activation_stage,
        "total_views": vendor.total_views,
        "total_profile_taps": vendor.total_profile_taps,
        "logo_url": logo_url,
        "cover_photo_url": cover_url,
        "storefront_photo_url": storefront_url,
    }


@transaction.atomic
def update_vendor_profile(
    vendor_id: str,
    updates: dict[str, Any],
    actor_id: str | None = None,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Update vendor business info.

    Allowed fields: business_name, description, address_text.

    Args:
        vendor_id: UUID of the vendor.
        updates: Dict of field:value pairs.
        actor_id: CustomerUser UUID for audit.
        request: HTTP request for audit.

    Returns:
        Dict with updated fields.
    """
    from apps.vendors.models import Vendor

    vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    allowed = {"business_name", "description", "address_text"}
    before = {k: getattr(vendor, k) for k in allowed}
    changed: list[str] = []

    for field, value in updates.items():
        if field in allowed and value is not None:
            setattr(vendor, field, value)
            changed.append(field)

    if changed:
        vendor.save(update_fields=changed + ["updated_at"])
        log_action(
            action="VENDOR_PROFILE_UPDATED",
            actor=None,
            target_obj=vendor,
            request=request,
            before=before,
            after={k: getattr(vendor, k) for k in allowed},
        )

    return {"updated_fields": changed, "vendor_id": str(vendor.id)}


@transaction.atomic
def update_business_hours(
    vendor_id: str,
    hours: dict[str, Any],
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Update vendor business hours.

    Validates via Pydantic schema before saving.

    Args:
        vendor_id: UUID of the vendor.
        hours: Business hours dict (7 days).
        request: HTTP request for audit.

    Returns:
        Dict confirming update.
    """
    from core.schemas import BusinessHoursSchema
    from apps.vendors.models import Vendor

    BusinessHoursSchema(**hours)

    vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    before = {"business_hours": vendor.business_hours}
    vendor.business_hours = hours
    vendor.save(update_fields=["business_hours", "updated_at"])

    log_action(
        action="VENDOR_HOURS_UPDATED",
        actor=None,
        target_obj=vendor,
        request=request,
        before=before,
        after={"business_hours": hours},
    )

    return {"vendor_id": str(vendor.id), "business_hours": hours}


@transaction.atomic
def update_services(
    vendor_id: str,
    offers_delivery: bool | None = None,
    offers_pickup: bool | None = None,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Update vendor delivery/pickup flags.

    Args:
        vendor_id: UUID of the vendor.
        offers_delivery: Delivery flag.
        offers_pickup: Pickup flag.
        request: HTTP request for audit.

    Returns:
        Dict confirming update.
    """
    from apps.vendors.models import Vendor

    vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    before = {
        "offers_delivery": vendor.offers_delivery,
        "offers_pickup": vendor.offers_pickup,
    }
    changed: list[str] = []

    if offers_delivery is not None:
        vendor.offers_delivery = offers_delivery
        changed.append("offers_delivery")
    if offers_pickup is not None:
        vendor.offers_pickup = offers_pickup
        changed.append("offers_pickup")

    if changed:
        vendor.save(update_fields=changed + ["updated_at"])
        log_action(
            action="VENDOR_SERVICES_UPDATED",
            actor=None,
            target_obj=vendor,
            request=request,
            before=before,
            after={
                "offers_delivery": vendor.offers_delivery,
                "offers_pickup": vendor.offers_pickup,
            },
        )

    return {
        "vendor_id": str(vendor.id),
        "offers_delivery": vendor.offers_delivery,
        "offers_pickup": vendor.offers_pickup,
    }


def generate_upload_url(vendor_id: str, upload_type: str) -> dict[str, Any]:
    """Generate a presigned S3 upload URL for logo or cover photo.

    Args:
        vendor_id: UUID of the vendor.
        upload_type: "logo" or "cover".

    Returns:
        Dict with upload_url and object_key.
    """
    import uuid

    from core.storage import generate_presigned_upload_url

    ext = "jpg"
    key = f"vendors/{vendor_id}/{upload_type}/{uuid.uuid4().hex}.{ext}"
    url = generate_presigned_upload_url(key, content_type=f"image/{ext}")

    return {"upload_url": url, "object_key": key}


@transaction.atomic
def confirm_upload(
    vendor_id: str,
    upload_type: str,
    object_key: str,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Confirm that a logo/cover upload completed and save the key.

    Args:
        vendor_id: UUID of the vendor.
        upload_type: "logo" or "cover".
        object_key: S3 object key.
        request: HTTP request for audit.

    Returns:
        Dict confirming update.
    """
    from apps.vendors.models import Vendor

    vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    field_map = {"logo": "logo_key", "cover": "cover_photo_key"}
    field_name = field_map.get(upload_type)

    if not field_name:
        raise ValueError(f"Invalid upload_type: {upload_type}")

    before = {field_name: getattr(vendor, field_name)}
    setattr(vendor, field_name, object_key)
    vendor.save(update_fields=[field_name, "updated_at"])

    log_action(
        action=f"VENDOR_{upload_type.upper()}_UPLOADED",
        actor=None,
        target_obj=vendor,
        request=request,
        before=before,
        after={field_name: object_key},
    )

    return {"vendor_id": str(vendor.id), field_name: object_key}


@transaction.atomic
def request_location_change(
    vendor_id: str,
    new_lat: float,
    new_lng: float,
    reason: str = "",
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Submit a GPS location change request for admin review.

    Sets location_pending_review=True and stores new coords in gps_baseline.

    Args:
        vendor_id: UUID of the vendor.
        new_lat: Proposed new latitude.
        new_lng: Proposed new longitude.
        reason: Reason for the change.
        request: HTTP request for audit.

    Returns:
        Dict confirming submission.
    """
    from django.contrib.gis.geos import Point

    from apps.vendors.models import Vendor

    vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)

    if vendor.location_pending_review:
        raise ValueError("A location change is already pending review.")

    new_point = Point(new_lng, new_lat, srid=4326)
    before = {
        "location_pending_review": False,
        "gps_baseline": (
            {"lng": vendor.gps_baseline.x, "lat": vendor.gps_baseline.y}
            if vendor.gps_baseline
            else None
        ),
    }

    vendor.gps_baseline = new_point
    vendor.location_pending_review = True
    vendor.save(update_fields=["gps_baseline", "location_pending_review", "updated_at"])

    log_action(
        action="VENDOR_LOCATION_CHANGE_REQUESTED",
        actor=None,
        target_obj=vendor,
        request=request,
        before=before,
        after={
            "location_pending_review": True,
            "gps_baseline": {"lng": new_lng, "lat": new_lat},
            "reason": reason,
        },
    )

    return {
        "vendor_id": str(vendor.id),
        "location_pending_review": True,
        "message": "Location change submitted for admin review.",
    }


def get_profile_completeness(vendor_id: str) -> dict[str, Any]:
    """Calculate profile completeness score for a vendor.

    Checks: business_name, description, address, phone, hours,
    logo, cover, GPS, delivery/pickup, at least 1 tag.

    Args:
        vendor_id: UUID of the vendor.

    Returns:
        Dict with score (0-100), completed items, and missing items.
    """
    from apps.vendors.models import Vendor

    vendor = Vendor.objects.select_related("city", "area").get(
        id=vendor_id, is_deleted=False
    )

    checks = {
        "business_name": bool(vendor.business_name),
        "description": bool(vendor.description and len(vendor.description) >= 20),
        "address_text": bool(vendor.address_text),
        "phone": bool(vendor.phone_number_encrypted),
        "business_hours": bool(vendor.business_hours),
        "gps_location": bool(vendor.gps_point),
        "logo": bool(vendor.logo_key),
        "cover_photo": bool(vendor.cover_photo_key),
        "delivery_or_pickup": vendor.offers_delivery or vendor.offers_pickup,
        "at_least_one_tag": vendor.tags.filter(is_active=True).exists(),
    }

    completed = [k for k, v in checks.items() if v]
    missing = [k for k, v in checks.items() if not v]
    score = int((len(completed) / len(checks)) * 100)

    return {
        "score": score,
        "total_checks": len(checks),
        "completed_count": len(completed),
        "completed": completed,
        "missing": missing,
    }


# ---------------------------------------------------------------------------
# C-3: Vendor Portal Dashboard API
# ---------------------------------------------------------------------------

def get_vendor_dashboard(vendor_id: str) -> dict[str, Any]:
    """Aggregate all dashboard data for the vendor portal home screen.

    Returns:
    - Profile completeness
    - Subscription info + features
    - Active discounts count
    - This week's views, taps, navigation
    - Reel count vs limit
    - Upcoming scheduled discounts
    - Voice bot completeness (if applicable)
    - Upgrade prompt (if Silver/Gold)

    Args:
        vendor_id: UUID of the vendor.

    Returns:
        Aggregated dashboard dict.
    """
    from django.db.models import Count, Q

    from apps.analytics.models import AnalyticsEvent, EventType
    from apps.subscriptions.models import SubscriptionPackage
    from apps.vendors.models import Discount, Vendor, VoiceBotConfig

    vendor = Vendor.objects.select_related("vendor_subscription").get(
        id=vendor_id, is_deleted=False
    )

    # Profile completeness
    completeness = get_profile_completeness(vendor_id)

    # Subscription info
    sub_level = vendor.subscription_level or "SILVER"
    package = SubscriptionPackage.objects.filter(
        level=sub_level, is_active=True
    ).first()

    subscription_info = {
        "level": sub_level,
        "name": package.name if package else sub_level,
        "valid_until": (
            vendor.subscription_valid_until.isoformat()
            if vendor.subscription_valid_until
            else None
        ),
        "max_videos": package.max_videos if package else 1,
        "daily_happy_hours_allowed": (
            package.daily_happy_hours_allowed if package else 0
        ),
        "has_voice_bot": package.has_voice_bot if package else False,
        "has_predictive_reports": package.has_predictive_reports if package else False,
    }

    # Active discounts
    now = timezone.now()
    active_discounts = Discount.objects.filter(
        vendor=vendor, is_active=True
    ).filter(
        Q(start_time__lte=now) & (Q(end_time__isnull=True) | Q(end_time__gte=now))
    ).count()

    upcoming_discounts = Discount.objects.filter(
        vendor=vendor, is_active=True, start_time__gt=now
    ).order_by("start_time").values(
        "id", "title", "discount_type", "value", "start_time"
    )[:5]

    # This week's analytics
    week_ago = now - timedelta(days=7)
    week_events = AnalyticsEvent.objects.filter(
        vendor_id=vendor_id, created_at__gte=week_ago
    )
    weekly_views = week_events.filter(
        event_type__in=[EventType.VENDOR_VIEW, EventType.VIEW]
    ).count()
    weekly_taps = week_events.filter(event_type=EventType.PROFILE_TAP).count()
    weekly_nav = week_events.filter(event_type=EventType.NAVIGATION_STARTED).count()

    # Reel count (Phase B — count reel events as a proxy until Reel model exists)
    reel_count = AnalyticsEvent.objects.filter(
        vendor_id=vendor_id,
        event_type__in=[EventType.REEL_VIEW, EventType.REEL_VIEWED],
    ).values("metadata__reel_id").distinct().count()
    reel_limit = subscription_info["max_videos"]

    # Voice bot completeness
    voicebot_score = None
    if subscription_info["has_voice_bot"]:
        vb = VoiceBotConfig.objects.filter(vendor=vendor).first()
        if vb:
            checks = [
                bool(vb.opening_hours_summary),
                bool(vb.menu_items),
                bool(vb.custom_qa_pairs),
                bool(vb.delivery_info),
            ]
            voicebot_score = int((sum(checks) / len(checks)) * 100)
        else:
            voicebot_score = 0

    # Upgrade prompt
    upgrade_prompt = None
    if sub_level in ("SILVER", "GOLD"):
        next_tier = "GOLD" if sub_level == "SILVER" else "DIAMOND"
        next_pkg = SubscriptionPackage.objects.filter(
            level=next_tier, is_active=True
        ).first()
        if next_pkg:
            upgrade_prompt = {
                "next_tier": next_tier,
                "next_tier_name": next_pkg.name,
                "price_monthly": str(next_pkg.price_monthly),
                "key_benefit": (
                    "Unlock voice bot & sponsored placement"
                    if sub_level == "SILVER"
                    else "Unlock predictive reports & area boost"
                ),
            }

    return {
        "business_name": vendor.business_name,
        "profile_completeness": completeness,
        "subscription": subscription_info,
        "active_discounts_count": active_discounts,
        "upcoming_discounts": list(upcoming_discounts),
        "weekly_stats": {
            "views": weekly_views,
            "taps": weekly_taps,
            "navigation_clicks": weekly_nav,
        },
        "reels": {
            "count": reel_count,
            "limit": reel_limit,
        },
        "voicebot_completeness": voicebot_score,
        "upgrade_prompt": upgrade_prompt,
        "activation_stage": vendor.activation_stage,
    }


# ---------------------------------------------------------------------------
# C-4: Landing Page Data API (Public)
# ---------------------------------------------------------------------------

def get_landing_page_stats() -> dict[str, Any]:
    """Get public stats for the vendor portal landing page.

    Returns:
    - Total active vendors
    - Total cities covered
    - Average view increase after claim (calculated)
    - Subscription tier overview
    - Featured success stories placeholder

    Returns:
        Dict with landing page data.
    """
    from django.db.models import Avg

    from apps.geo.models import City
    from apps.subscriptions.models import SubscriptionPackage
    from apps.vendors.models import ClaimedStatus, Vendor

    total_vendors = Vendor.objects.filter(is_deleted=False, qc_status="APPROVED").count()
    claimed_vendors = Vendor.objects.filter(
        is_deleted=False,
        claimed_status=ClaimedStatus.CLAIMED,
    ).count()
    total_cities = City.objects.filter(is_active=True).count()

    avg_views = (
        Vendor.objects.filter(
            is_deleted=False,
            claimed_status=ClaimedStatus.CLAIMED,
        ).aggregate(avg_views=Avg("total_views"))["avg_views"]
        or 0
    )

    tiers = SubscriptionPackage.objects.filter(is_active=True).order_by(
        "price_monthly"
    ).values("level", "name", "price_monthly", "max_videos")

    # Featured stories: top 3 claimed vendors by views with highest tier
    featured_qs = (
        Vendor.objects.filter(
            is_deleted=False,
            claimed_status=ClaimedStatus.CLAIMED,
            total_views__gt=0,
        )
        .exclude(subscription_level="SILVER")
        .order_by("-total_views")[:3]
    )
    featured_stories = [
        {
            "business_name": v.business_name,
            "subscription_level": v.subscription_level,
            "total_views": v.total_views,
            "city": v.city.name if v.city else "",
        }
        for v in featured_qs.select_related("city")
    ]

    return {
        "total_active_vendors": total_vendors,
        "claimed_vendors": claimed_vendors,
        "total_cities": total_cities,
        "avg_views_after_claim": round(avg_views),
        "subscription_tiers": list(tiers),
        "featured_stories": featured_stories,
    }


# =========================================================================
# B-3: Activation Stage (§3.2)
# =========================================================================


def _compute_completeness(vendor: "Vendor") -> int:
    """Compute profile completeness score (0-100) from a Vendor instance.

    Used internally by get_activation_stage() without an extra DB fetch.
    """
    checks = {
        "business_name": bool(vendor.business_name),
        "description": bool(vendor.description and len(vendor.description) >= 20),
        "address_text": bool(vendor.address_text),
        "phone": bool(vendor.phone_number_encrypted),
        "business_hours": bool(vendor.business_hours),
        "gps_location": bool(vendor.gps_point),
        "logo": bool(vendor.logo_key),
        "cover_photo": bool(vendor.cover_photo_key),
        "delivery_or_pickup": vendor.offers_delivery or vendor.offers_pickup,
        "at_least_one_tag": vendor.tags.filter(is_active=True).exists(),
    }
    completed = sum(1 for v in checks.values() if v)
    return int((completed / len(checks)) * 100)


def get_activation_stage(vendor_id: str) -> dict[str, Any]:
    """Return current activation stage, criteria met, and next stage requirements.

    Progressive Activation Strategy stages:
    CLAIM → ENGAGEMENT → MONETIZATION → GROWTH → RETENTION

    Args:
        vendor_id: UUID of the vendor.

    Returns:
        Dict with current_stage, criteria_met, next_stage, next_criteria.
    """
    from apps.vendors.models import ActivationStage, Vendor

    vendor = Vendor.objects.get(pk=vendor_id, is_deleted=False)

    stage = vendor.activation_stage
    criteria_met: dict[str, bool] = {}
    next_stage: str | None = None
    next_criteria: dict[str, str] = {}

    # CLAIM stage: vendor has been claimed
    if stage == ActivationStage.CLAIM:
        criteria_met = {
            "vendor_claimed": vendor.claimed_status == "CLAIMED",
            "profile_complete": _compute_completeness(vendor) >= 50,
        }
        next_stage = ActivationStage.ENGAGEMENT
        next_criteria = {
            "vendor_claimed": "Claim your vendor listing",
            "profile_complete": "Complete at least 50% of your profile",
        }

    # ENGAGEMENT stage: vendor is engaging with features
    elif stage == ActivationStage.ENGAGEMENT:
        from apps.reels.models import VendorReel

        media_count = sum([
            bool(vendor.storefront_photo_key),
            bool(vendor.logo_key),
            bool(vendor.cover_photo_key),
        ]) + VendorReel.objects.filter(vendor=vendor, is_active=True).count()
        has_media = media_count >= 3
        has_hours = bool(vendor.business_hours)
        criteria_met = {
            "has_3_media": has_media,
            "has_business_hours": has_hours,
            "has_description": bool(vendor.description),
        }
        next_stage = ActivationStage.MONETIZATION
        next_criteria = {
            "has_3_media": "Upload at least 3 photos/reels",
            "has_business_hours": "Set your business hours",
            "has_description": "Add a business description",
        }

    # MONETIZATION stage: vendor starts monetizing
    elif stage == ActivationStage.MONETIZATION:
        from apps.vendors.models import Discount

        has_discount = Discount.objects.filter(vendor=vendor, is_active=True).exists()
        is_paid = vendor.subscription_level != "SILVER"
        criteria_met = {
            "has_active_discount": has_discount,
            "is_paid_subscriber": is_paid,
        }
        next_stage = ActivationStage.GROWTH
        next_criteria = {
            "has_active_discount": "Create at least one active discount or deal",
            "is_paid_subscriber": "Upgrade to a paid subscription tier",
        }

    # GROWTH stage: vendor is growing
    elif stage == ActivationStage.GROWTH:
        from apps.reels.models import VendorReel

        has_reel = VendorReel.objects.filter(
            vendor=vendor, is_active=True
        ).exists()
        criteria_met = {
            "has_reel": has_reel,
            "views_above_threshold": vendor.total_views >= 100,
        }
        next_stage = ActivationStage.RETENTION
        next_criteria = {
            "has_reel": "Upload at least one reel/video",
            "views_above_threshold": "Reach 100+ total views",
        }

    # RETENTION stage: final stage
    elif stage == ActivationStage.RETENTION:
        criteria_met = {"retained": True}
        next_stage = None
        next_criteria = {}

    all_met = all(criteria_met.values()) if criteria_met else False

    return {
        "current_stage": stage,
        "criteria_met": criteria_met,
        "all_criteria_met": all_met,
        "next_stage": next_stage,
        "next_criteria": next_criteria,
        "activation_stage_updated_at": (
            vendor.activation_stage_updated_at.isoformat()
            if vendor.activation_stage_updated_at
            else None
        ),
    }
