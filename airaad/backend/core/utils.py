"""
AirAd Backend — General Utilities

get_client_ip: Extracts real client IP from X-Forwarded-For or REMOTE_ADDR.
vendor_has_feature: Feature gating based on SubscriptionPackage (§3.5).
"""

import logging
from typing import TYPE_CHECKING

from django.http import HttpRequest

if TYPE_CHECKING:
    from apps.vendors.models import Vendor

logger = logging.getLogger(__name__)


def get_client_ip(request: HttpRequest) -> str:
    """Extract the real client IP address from the request.

    Uses ``REMOTE_ADDR`` as the authoritative source when behind a trusted
    reverse proxy (nginx). If ``NUM_PROXIES`` is set in Django settings
    (default 1), the rightmost non-proxy IP in ``X-Forwarded-For`` is used,
    which cannot be spoofed by the client.

    Taking the *leftmost* XFF entry is insecure because clients can inject
    arbitrary values there. The *rightmost* entry is appended by the trusted
    proxy and is reliable.

    Args:
        request: The incoming Django HTTP request.

    Returns:
        Client IP address string. Returns "unknown" if no IP can be determined.

    Example:
        >>> ip = get_client_ip(request)
        >>> isinstance(ip, str)
        True
    """
    from django.conf import settings

    num_proxies: int = getattr(settings, "NUM_PROXIES", 1)

    x_forwarded_for: str | None = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for and num_proxies > 0:
        # X-Forwarded-For: client, proxy1, ..., trusted-proxy
        # Take the entry num_proxies positions from the right — that is the
        # first IP added by the trusted proxy, not client-controlled.
        ips = [ip.strip() for ip in x_forwarded_for.split(",")]
        index = max(len(ips) - num_proxies, 0)
        ip = ips[index]
        return ip if ip else "unknown"

    return request.META.get("REMOTE_ADDR", "unknown")


def vendor_has_feature(vendor: "Vendor", feature: str) -> bool:
    """Check whether a vendor's subscription tier includes a given feature.

    This is the ONLY subscription feature gate in the entire codebase.
    No ``if vendor.subscription_level ==`` checks are permitted anywhere else.

    Reads the vendor's subscription_level and looks up the corresponding
    SubscriptionPackage to determine feature availability.

    Feature names:
        - ``HAPPY_HOUR`` — Gold+ (daily_happy_hours_allowed > 0)
        - ``VOICE_BOT`` — Gold+ (has_voice_bot=True)
        - ``SPONSORED_WINDOW`` — Gold+ (sponsored_placement_level != NONE)
        - ``TIME_HEATMAP`` — Gold+ (hourly analytics)
        - ``PREDICTIVE_RECOMMENDATIONS`` — Platinum only (has_predictive_reports=True)
        - ``EXTRA_REELS`` — Gold+ (max_videos > 1)
        - ``CAMPAIGN_SCHEDULING`` — Gold+ (campaign_scheduling_level != NONE)

    Args:
        vendor: The Vendor instance to check.
        feature: Feature name string (case-sensitive).

    Returns:
        True if the vendor's subscription tier includes the requested feature.

    Example:
        >>> vendor_has_feature(vendor, "HAPPY_HOUR")
        False  # if vendor is SILVER
    """
    try:
        from apps.subscriptions.models import SubscriptionPackage

        package = SubscriptionPackage.objects.filter(
            level=vendor.subscription_level,
            is_active=True,
        ).first()

        if package is None:
            return False

        feature_map: dict[str, bool] = {
            # Happy Hour — Gold+ (daily_happy_hours_allowed > 0)
            "HAPPY_HOUR": package.daily_happy_hours_allowed > 0,
            # Voice Bot tiers
            "VOICE_BOT": package.has_voice_bot,
            "VOICE_BOT_DYNAMIC": package.voice_bot_type in ("DYNAMIC", "ADVANCED"),
            "VOICE_BOT_ADVANCED": package.voice_bot_type == "ADVANCED",
            # Sponsored Placement tiers
            "SPONSORED_WINDOW": package.sponsored_placement_level != "NONE",
            "SPONSORED_LIMITED_TIME": package.sponsored_placement_level in (
                "LIMITED_TIME", "AREA_BOOST", "AREA_EXCLUSIVE",
            ),
            "SPONSORED_AREA_BOOST": package.sponsored_placement_level in (
                "AREA_BOOST", "AREA_EXCLUSIVE",
            ),
            "SPONSORED_AREA_EXCLUSIVE": package.sponsored_placement_level == "AREA_EXCLUSIVE",
            # Analytics
            "TIME_HEATMAP": package.analytics_level in ("STANDARD", "ADVANCED", "PREDICTIVE"),
            "PREDICTIVE_RECOMMENDATIONS": package.has_predictive_reports,
            "COMPETITOR_BENCHMARKING": package.analytics_level == "PREDICTIVE",
            # Reels
            "EXTRA_REELS": package.max_videos > 1,
            # Campaign Scheduling tiers
            "CAMPAIGN_SCHEDULING": package.campaign_scheduling_level != "NONE",
            "CAMPAIGN_BASIC": package.campaign_scheduling_level in (
                "BASIC", "ADVANCED", "SMART_AUTOMATION",
            ),
            "CAMPAIGN_ADVANCED": package.campaign_scheduling_level in (
                "ADVANCED", "SMART_AUTOMATION",
            ),
            "CAMPAIGN_SMART_AUTOMATION": package.campaign_scheduling_level == "SMART_AUTOMATION",
            # Discount types — Gold+ can create item-specific, Diamond+ flash, Gold+ BOGO
            "ITEM_SPECIFIC_DISCOUNT": package.level in ("GOLD", "DIAMOND", "PLATINUM"),
            "FLASH_DISCOUNT": package.level in ("DIAMOND", "PLATINUM"),
            "BOGO_DEAL": package.level in ("GOLD", "DIAMOND", "PLATINUM"),
            # Delivery — Diamond+
            "FREE_DELIVERY": package.max_delivery_configs != 0,
            # Voice search priority
            "VOICE_SEARCH_PRIORITY": package.voice_search_priority != "NONE",
        }

        return feature_map.get(feature, False)
    except Exception as exc:
        logger.error(
            "vendor_has_feature lookup failed — defaulting to False",
            extra={
                "vendor_id": str(getattr(vendor, "id", "?")),
                "feature": feature,
                "error": str(exc),
            },
        )
        return False
