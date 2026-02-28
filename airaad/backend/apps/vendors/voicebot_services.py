"""
AirAd Backend — Voice Bot Service Layer (Phase B §B-7, R4)

All voice bot config management logic lives here.
Every mutation calls AuditLog (R5).
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.vendors.models import Vendor, VoiceBotConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_ip(request: Any) -> str:
    if request is None:
        return ""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _calculate_completeness(config: VoiceBotConfig) -> int:
    """Calculate completeness score (0-100) for voice bot config."""
    checks = [
        bool(config.opening_hours_summary),
        bool(config.menu_items),
        bool(config.custom_qa_pairs),
        bool(config.delivery_info),
        bool(config.intro_message),
    ]
    return int((sum(checks) / len(checks)) * 100) if checks else 0


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def get_voicebot_config(vendor_id: str) -> dict:
    """Get or create voice bot config for a vendor.

    Args:
        vendor_id: UUID of the vendor.

    Returns:
        Dict with voice bot configuration data.

    Raises:
        Vendor.DoesNotExist: If vendor not found.
    """
    vendor = Vendor.objects.get(pk=vendor_id)
    config, _ = VoiceBotConfig.objects.get_or_create(vendor=vendor)

    return {
        "id": str(config.pk),
        "vendor_id": str(vendor_id),
        "menu_items": config.menu_items,
        "opening_hours_summary": config.opening_hours_summary,
        "delivery_info": config.delivery_info,
        "discount_summary": config.discount_summary,
        "custom_qa_pairs": config.custom_qa_pairs,
        "intro_message": config.intro_message,
        "pickup_available": config.pickup_available,
        "is_active": config.is_active,
        "completeness_score": config.completeness_score,
        "last_updated_at": config.last_updated_at.isoformat() if config.last_updated_at else None,
    }


@transaction.atomic
def update_voicebot_config(
    vendor_id: str,
    data: dict,
    *,
    request: Any = None,
) -> dict:
    """Update voice bot configuration for a vendor.

    Args:
        vendor_id: UUID of the vendor.
        data: Dict of fields to update.
        request: HTTP request for audit logging.

    Returns:
        Updated config dict.

    Raises:
        Vendor.DoesNotExist: If vendor not found.
    """
    vendor = Vendor.objects.get(pk=vendor_id)
    config, _ = VoiceBotConfig.objects.get_or_create(vendor=vendor)

    allowed = {
        "menu_items", "opening_hours_summary", "delivery_info",
        "custom_qa_pairs", "intro_message", "pickup_available", "is_active",
    }
    changed = {}
    for field in allowed:
        if field in data:
            old_val = getattr(config, field)
            setattr(config, field, data[field])
            changed[field] = True

    if changed:
        config.completeness_score = _calculate_completeness(config)
        config.last_updated_at = timezone.now()
        update_fields = [*changed.keys(), "completeness_score", "last_updated_at", "updated_at"]
        config.save(update_fields=update_fields)

        AuditLog.objects.create(
            action="VOICEBOT_CONFIG_UPDATED",
            target_type="VoiceBotConfig",
            target_id=config.pk,
            actor_label=str(vendor.owner_id) if vendor.owner_id else "",
            ip_address=_get_ip(request),
            before_state={},
            after_state={"fields_updated": list(changed.keys()), "vendor_id": str(vendor_id)},
        )
        logger.info("VoiceBotConfig updated for vendor %s — fields: %s", vendor_id, list(changed.keys()))

    return get_voicebot_config(vendor_id)


# ---------------------------------------------------------------------------
# Test query (rule-based matching)
# ---------------------------------------------------------------------------

def test_voice_query(vendor_id: str, query: str) -> dict:
    """Run a test voice query against the vendor's voice bot config.

    Uses simple keyword matching against menu items and custom QA pairs.

    Args:
        vendor_id: UUID of the vendor.
        query: Natural language query string.

    Returns:
        Dict with matched response and source.
    """
    config = VoiceBotConfig.objects.filter(vendor_id=vendor_id).first()
    if not config:
        return {"response": "Voice bot is not configured for this vendor.", "source": "system"}

    if not config.is_active:
        return {"response": "Voice bot is currently disabled.", "source": "system"}

    query_lower = query.lower().strip()

    # Check custom QA pairs first (highest priority)
    for qa in config.custom_qa_pairs or []:
        question = (qa.get("question") or "").lower()
        if question and question in query_lower or query_lower in question:
            return {"response": qa.get("answer", ""), "source": "custom_qa"}

    # Check menu items
    for item in config.menu_items or []:
        item_name = (item.get("name") or "").lower()
        if item_name and item_name in query_lower:
            price = item.get("price", "N/A")
            available = "available" if item.get("is_available", True) else "currently unavailable"
            desc = item.get("description", "")
            response = f"{item.get('name', '')} — PKR {price} ({available})"
            if desc:
                response += f". {desc}"
            return {"response": response, "source": "menu_items"}

    # Check for hours/timing keywords
    hours_keywords = {"hours", "open", "close", "timing", "time", "schedule"}
    if any(kw in query_lower for kw in hours_keywords):
        if config.opening_hours_summary:
            return {"response": config.opening_hours_summary, "source": "hours"}

    # Check for delivery keywords
    delivery_keywords = {"delivery", "deliver", "pickup", "pick up", "takeaway"}
    if any(kw in query_lower for kw in delivery_keywords):
        if config.delivery_info:
            return {"response": config.delivery_info, "source": "delivery"}

    # Check for discount/offer keywords
    discount_keywords = {"discount", "offer", "deal", "promotion", "sale", "happy hour"}
    if any(kw in query_lower for kw in discount_keywords):
        if config.discount_summary:
            return {"response": config.discount_summary, "source": "discounts"}

    # Fallback
    return {
        "response": "I couldn't find a specific answer. Please try asking about our menu, hours, delivery, or current offers.",
        "source": "fallback",
    }
