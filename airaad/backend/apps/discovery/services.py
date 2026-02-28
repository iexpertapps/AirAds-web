"""
AirAd Backend — Discovery & Search Engine (Phase B §3.3)

RankingService: pure function, independently testable.
1. ST_DWithin filter FIRST
2. Score: Text match (30%) + Distance (25%) + Active offer (15%) + Popularity 30d (15%) + Subscription (15%)
3. Subscription scores use visibility_boost_weight from SubscriptionPackage
4. Paid tier cannot override distance by more than 30%

All geospatial operations use PostGIS ST_DWithin/ST_Distance — never degree×constant (R1).
"""

import difflib
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

logger = logging.getLogger(__name__)

DEFAULT_RADIUS_METERS = 2000
MAX_RADIUS_METERS = 10000
MAX_RESULTS = 50


@dataclass
class ScoredVendor:
    """A vendor with its computed ranking score and breakdown."""

    vendor: Any
    total_score: float = 0.0
    text_score: float = 0.0
    distance_score: float = 0.0
    offer_score: float = 0.0
    popularity_score: float = 0.0
    subscription_score: float = 0.0
    distance_meters: float = 0.0


class RankingService:
    """Stateless ranking service — all methods are class methods for testability.

    Scoring weights (§3.3):
        Text match:     30%
        Distance:       25%
        Active offer:   15%
        Popularity:     15%
        Subscription:   15%

    Constraint: Subscription score cannot override distance by more than 30%.
    """

    WEIGHT_TEXT = 0.30
    WEIGHT_DISTANCE = 0.25
    WEIGHT_OFFER = 0.15
    WEIGHT_POPULARITY = 0.15
    WEIGHT_SUBSCRIPTION = 0.15

    MAX_SUBSCRIPTION_DISTANCE_OVERRIDE = 0.30

    @classmethod
    def rank_vendors(
        cls,
        vendors_qs: QuerySet,
        center: Point,
        query: str = "",
        radius_meters: float = DEFAULT_RADIUS_METERS,
    ) -> list[ScoredVendor]:
        """Rank a queryset of vendors by the composite scoring formula.

        Args:
            vendors_qs: Pre-filtered QuerySet of Vendor objects (already within radius).
            center: GPS point to measure distance from.
            query: Optional text search query.
            radius_meters: Search radius for distance normalization.

        Returns:
            List of ScoredVendor sorted by total_score descending.
        """
        scored: list[ScoredVendor] = []
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        for vendor in vendors_qs:
            sv = ScoredVendor(vendor=vendor)

            dist_m = getattr(vendor, "distance", None)
            if dist_m is not None:
                sv.distance_meters = dist_m.m if hasattr(dist_m, "m") else float(dist_m)
            else:
                sv.distance_meters = radius_meters

            sv.text_score = cls._compute_text_score(vendor, query) if query else 0.0

            sv.distance_score = cls._compute_distance_score(
                sv.distance_meters, radius_meters
            )

            sv.offer_score = cls._compute_offer_score(vendor, now)

            sv.popularity_score = cls._compute_popularity_score(vendor, thirty_days_ago)

            sv.subscription_score = cls._compute_subscription_score(vendor)

            raw_sub_contribution = sv.subscription_score * cls.WEIGHT_SUBSCRIPTION
            max_distance_override = sv.distance_score * cls.WEIGHT_DISTANCE * cls.MAX_SUBSCRIPTION_DISTANCE_OVERRIDE
            capped_sub_contribution = min(raw_sub_contribution, sv.distance_score * cls.WEIGHT_DISTANCE + max_distance_override)

            sv.total_score = (
                sv.text_score * cls.WEIGHT_TEXT
                + sv.distance_score * cls.WEIGHT_DISTANCE
                + sv.offer_score * cls.WEIGHT_OFFER
                + sv.popularity_score * cls.WEIGHT_POPULARITY
                + capped_sub_contribution
            )

            scored.append(sv)

        scored.sort(key=lambda s: s.total_score, reverse=True)
        return scored[:MAX_RESULTS]

    @classmethod
    def _compute_text_score(cls, vendor: Any, query: str) -> float:
        """Compute text relevance score using SequenceMatcher.

        Checks business_name and tag names.

        Args:
            vendor: Vendor instance.
            query: Search query string.

        Returns:
            Float between 0.0 and 1.0.
        """
        query_lower = query.lower()
        name_lower = vendor.business_name.lower()

        if query_lower in name_lower:
            return 1.0

        name_ratio = difflib.SequenceMatcher(None, query_lower, name_lower).ratio()

        tag_score = 0.0
        if hasattr(vendor, "_prefetched_objects_cache") and "tags" in vendor._prefetched_objects_cache:
            for tag in vendor.tags.all():
                tag_ratio = difflib.SequenceMatcher(
                    None, query_lower, tag.name.lower()
                ).ratio()
                tag_score = max(tag_score, tag_ratio)

        return max(name_ratio, tag_score)

    @classmethod
    def _compute_distance_score(cls, distance_m: float, radius_m: float) -> float:
        """Compute distance score — closer is better.

        Args:
            distance_m: Distance from center in metres.
            radius_m: Search radius in metres.

        Returns:
            Float between 0.0 and 1.0.
        """
        if radius_m <= 0:
            return 0.0
        normalized = max(0.0, 1.0 - (distance_m / radius_m))
        return normalized

    @classmethod
    def _compute_offer_score(cls, vendor: Any, now: Any) -> float:
        """Compute active offer score.

        Args:
            vendor: Vendor instance.
            now: Current datetime.

        Returns:
            1.0 if vendor has any active discount, 0.0 otherwise.
        """
        has_active = getattr(vendor, "active_discount_count", None)
        if has_active is not None:
            return 1.0 if has_active > 0 else 0.0

        if hasattr(vendor, "discounts"):
            return 1.0 if vendor.discounts.filter(
                is_active=True,
                start_time__lte=now,
                end_time__gte=now,
            ).exists() else 0.0
        return 0.0

    @classmethod
    def _compute_popularity_score(cls, vendor: Any, since: Any) -> float:
        """Compute popularity score based on views in the last 30 days.

        Normalizes to [0, 1] using log scale to prevent outlier dominance.

        Args:
            vendor: Vendor instance.
            since: Datetime cutoff (30 days ago).

        Returns:
            Float between 0.0 and 1.0.
        """
        import math

        views = getattr(vendor, "recent_view_count", None)
        if views is None:
            views = vendor.total_views or 0

        if views <= 0:
            return 0.0
        return min(1.0, math.log1p(views) / math.log1p(1000))

    @classmethod
    def _compute_subscription_score(cls, vendor: Any) -> float:
        """Compute subscription tier score using visibility_boost_weight.

        Args:
            vendor: Vendor instance with subscription_level.

        Returns:
            Normalized float between 0.0 and 1.0.
        """
        weight_map = {
            "SILVER": 1.0,
            "GOLD": 1.2,
            "DIAMOND": 1.5,
            "PLATINUM": 2.0,
        }
        weight = weight_map.get(getattr(vendor, "subscription_level", "SILVER"), 1.0)
        return min(1.0, (weight - 1.0) / 1.0)


def search_vendors(
    lat: float,
    lng: float,
    radius: float = DEFAULT_RADIUS_METERS,
    query: str = "",
    tag_ids: list[str] | None = None,
    tag_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Execute a vendor search with ranking.

    Uses ST_DWithin for spatial filtering, then applies RankingService scoring.

    Args:
        lat: Search center latitude.
        lng: Search center longitude.
        radius: Search radius in metres.
        query: Optional text search query.
        tag_ids: Optional list of tag UUID strings to filter by.
        tag_types: Optional list of tag types to filter by.

    Returns:
        List of vendor dicts with ranking scores.
    """
    from apps.vendors.models import Vendor

    if radius > MAX_RADIUS_METERS:
        radius = MAX_RADIUS_METERS

    center = Point(lng, lat, srid=4326)

    qs = (
        Vendor.objects.filter(
            is_deleted=False,
            qc_status="APPROVED",
            gps_point__dwithin=(center, D(m=radius)),
        )
        .select_related("city", "area")
        .prefetch_related("tags", "discounts")
        .annotate(distance=Distance("gps_point", center, spherical=True))
    )

    if query:
        qs = qs.filter(
            Q(business_name__icontains=query)
            | Q(tags__name__icontains=query)
            | Q(description__icontains=query)
        ).distinct()

    if tag_ids:
        qs = qs.filter(tags__id__in=tag_ids)

    if tag_types:
        qs = qs.filter(tags__tag_type__in=tag_types)

    scored = RankingService.rank_vendors(qs, center, query, radius)

    results = []
    for sv in scored:
        v = sv.vendor
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
            "subscription_level": v.subscription_level,
            "is_verified": v.is_verified,
            "distance_meters": round(sv.distance_meters, 1),
            "score": round(sv.total_score, 4),
            "has_active_offer": sv.offer_score > 0,
        })

    return results


def nearby_vendors(
    lat: float,
    lng: float,
    radius: float = DEFAULT_RADIUS_METERS,
) -> list[dict[str, Any]]:
    """Return nearby vendors without text search — ranked by distance + subscription.

    Args:
        lat: Center latitude.
        lng: Center longitude.
        radius: Radius in metres.

    Returns:
        List of vendor dicts ordered by proximity with subscription boost.
    """
    return search_vendors(lat=lat, lng=lng, radius=radius, query="")


def voice_search(
    lat: float,
    lng: float,
    transcript: str,
    radius: float = DEFAULT_RADIUS_METERS,
) -> list[dict[str, Any]]:
    """Process a voice search query using rule-based NLP (no ML).

    Extracts intent from transcript:
    - Food-related keywords → filter CATEGORY tags
    - Location keywords → filter LOCATION tags
    - "near me" / "nearby" → use default radius
    - Price keywords → filter INTENT tags (cheap, premium, etc.)

    Args:
        lat: User's GPS latitude.
        lng: User's GPS longitude.
        transcript: Raw voice transcript text.
        radius: Search radius in metres.

    Returns:
        List of ranked vendor dicts.
    """
    processed_query = transcript.strip()

    if not processed_query:
        return nearby_vendors(lat, lng, radius)

    intent_keywords = {
        "cheap": ["intent-cheap", "intent-budget-under-300"],
        "budget": ["intent-budget-under-300", "intent-budget-under-500"],
        "premium": ["intent-premium"],
        "luxury": ["intent-luxury"],
        "quick": ["intent-quick", "intent-grab-and-go"],
        "fast": ["intent-quick", "intent-fast-service"],
        "healthy": ["intent-healthy"],
        "halal": ["intent-halal"],
        "family": ["intent-family-friendly"],
        "romantic": ["intent-romantic"],
        "late night": ["intent-late-night"],
        "breakfast": ["intent-breakfast"],
    }

    tag_slugs: list[str] = []
    lower_transcript = processed_query.lower()

    for keyword, slugs in intent_keywords.items():
        if keyword in lower_transcript:
            tag_slugs.extend(slugs)

    tag_ids: list[str] = []
    if tag_slugs:
        from apps.tags.models import Tag

        tag_ids = list(
            Tag.objects.filter(slug__in=tag_slugs, is_active=True)
            .values_list("id", flat=True)
        )
        tag_ids = [str(tid) for tid in tag_ids]

    return search_vendors(
        lat=lat,
        lng=lng,
        radius=radius,
        query=processed_query,
        tag_ids=tag_ids if tag_ids else None,
    )


def voice_query_vendor(vendor_slug: str, question: str) -> dict[str, Any]:
    """Answer a voice question about a specific vendor using VoiceBotConfig.

    Rule-based matching against menu_items, custom_qa_pairs, opening hours,
    delivery info, and discount summary.

    Args:
        vendor_slug: Slug of the vendor to query.
        question: The voice question text.

    Returns:
        Dict with answer text and source.

    Raises:
        ValueError: If vendor not found or voice bot not configured.
    """
    from apps.vendors.models import Vendor, VoiceBotConfig
    from core.utils import vendor_has_feature

    try:
        vendor = Vendor.objects.get(slug=vendor_slug, is_deleted=False)
    except Vendor.DoesNotExist:
        raise ValueError(f"Vendor '{vendor_slug}' not found")

    if not vendor_has_feature(vendor, "VOICE_BOT"):
        raise ValueError("Voice bot is not available for this vendor's subscription tier")

    try:
        config = vendor.voice_bot_config
    except VoiceBotConfig.DoesNotExist:
        raise ValueError("Voice bot is not configured for this vendor")

    q_lower = question.lower()

    for qa_pair in config.custom_qa_pairs or []:
        if isinstance(qa_pair, dict):
            q = qa_pair.get("question", "").lower()
            if q and (q in q_lower or difflib.SequenceMatcher(None, q, q_lower).ratio() > 0.7):
                return {
                    "answer": qa_pair.get("answer", ""),
                    "source": "custom_qa",
                    "vendor": vendor.business_name,
                }

    menu_keywords = ["menu", "food", "eat", "dish", "price", "cost", "order"]
    if any(kw in q_lower for kw in menu_keywords):
        if config.menu_items:
            available_items = [
                item for item in config.menu_items
                if isinstance(item, dict) and item.get("is_available", True)
            ]
            if available_items:
                items_text = ", ".join(
                    f"{item.get('name', '?')} (PKR {item.get('price', '?')})"
                    for item in available_items[:10]
                )
                return {
                    "answer": f"Here's our menu: {items_text}",
                    "source": "menu_items",
                    "vendor": vendor.business_name,
                }

    time_keywords = ["open", "close", "hours", "timing", "time"]
    if any(kw in q_lower for kw in time_keywords):
        if config.opening_hours_summary:
            return {
                "answer": config.opening_hours_summary,
                "source": "opening_hours",
                "vendor": vendor.business_name,
            }

    delivery_keywords = ["deliver", "pickup", "takeaway", "delivery"]
    if any(kw in q_lower for kw in delivery_keywords):
        if config.delivery_info:
            info = config.delivery_info
            if isinstance(info, dict):
                parts = []
                if info.get("radius_km"):
                    parts.append(f"Delivery within {info['radius_km']} km")
                if info.get("free_within_km"):
                    parts.append(f"Free delivery within {info['free_within_km']} km")
                if info.get("charges"):
                    parts.append(f"Charges: {info['charges']}")
                answer_text = ". ".join(parts) if parts else "Delivery available."
            else:
                answer_text = str(info)
            if config.pickup_available:
                answer_text += " Pickup is also available."
            return {
                "answer": answer_text,
                "source": "delivery_info",
                "vendor": vendor.business_name,
            }

    deal_keywords = ["deal", "discount", "offer", "sale", "promotion"]
    if any(kw in q_lower for kw in deal_keywords):
        if config.discount_summary:
            return {
                "answer": config.discount_summary,
                "source": "discount_summary",
                "vendor": vendor.business_name,
            }

    return {
        "answer": f"I'm {vendor.business_name}. "
        f"{'We offer delivery. ' if vendor.offers_delivery else ''}"
        f"{'We have pickup available. ' if vendor.offers_pickup else ''}"
        f"Ask me about our menu, hours, delivery, or current deals!",
        "source": "fallback",
        "vendor": vendor.business_name,
    }


# =========================================================================
# Phase B — Nearby Reels Feed (§B-8)
# =========================================================================


def get_nearby_reels(
    lat: float,
    lng: float,
    radius_m: int = 5000,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return approved, active reels from vendors near the given coordinates.

    Uses PostGIS ST_DWithin for geo filtering.

    Args:
        lat: Latitude of the user.
        lng: Longitude of the user.
        radius_m: Search radius in metres (default 5000).
        limit: Max number of reels to return (default 20).

    Returns:
        List of reel dicts with vendor info and presigned URLs.
    """
    from apps.reels.models import ModerationStatus, ReelStatus, VendorReel
    from apps.vendors.models import Vendor
    from core.storage import generate_presigned_url

    center = Point(lng, lat, srid=4326)

    # Find vendor IDs within radius
    nearby_vendor_ids = list(
        Vendor.objects.filter(
            is_deleted=False,
            gps_point__dwithin=(center, D(m=radius_m)),
        ).values_list("id", flat=True)
    )

    if not nearby_vendor_ids:
        return []

    reels = (
        VendorReel.objects.filter(
            vendor_id__in=nearby_vendor_ids,
            status=ReelStatus.ACTIVE,
            moderation_status=ModerationStatus.APPROVED,
            is_active=True,
        )
        .select_related("vendor")
        .order_by("-created_at")[:limit]
    )

    results = []
    for r in reels:
        results.append({
            "id": str(r.pk),
            "title": r.title,
            "video_url": generate_presigned_url(r.s3_key) if r.s3_key else None,
            "thumbnail_url": (
                generate_presigned_url(r.thumbnail_s3_key)
                if r.thumbnail_s3_key
                else None
            ),
            "duration_seconds": r.duration_seconds,
            "view_count": r.view_count,
            "vendor_name": r.vendor.business_name,
            "vendor_slug": r.vendor.slug,
            "vendor_id": str(r.vendor_id),
            "created_at": r.created_at.isoformat(),
        })

    return results
