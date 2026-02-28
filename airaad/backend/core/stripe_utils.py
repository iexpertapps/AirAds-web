"""
AirAd Backend — Stripe Utility Functions (core/stripe_utils.py)

Centralised Stripe helpers used by apps/payments/services.py.
All Stripe API calls go through these wrappers for consistent
error handling and logging.
"""

import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def get_stripe_client() -> Any:
    """Return a configured Stripe module instance.

    Reads STRIPE_SECRET_KEY from Django settings. Returns None
    if the key is not configured (development mode).

    Returns:
        The stripe module with api_key set, or None if unconfigured.
    """
    secret_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not secret_key:
        logger.warning("Stripe not configured — STRIPE_SECRET_KEY is empty")
        return None

    import stripe

    stripe.api_key = secret_key
    return stripe


def get_price_id_for_level(level: str) -> str | None:
    """Map a subscription level to its Stripe Price ID.

    Args:
        level: Subscription level string (GOLD, DIAMOND, PLATINUM).

    Returns:
        Stripe Price ID string, or None if not configured.
    """
    price_map = {
        "GOLD": getattr(settings, "STRIPE_PRICE_GOLD", ""),
        "DIAMOND": getattr(settings, "STRIPE_PRICE_DIAMOND", ""),
        "PLATINUM": getattr(settings, "STRIPE_PRICE_PLATINUM", ""),
    }
    price_id = price_map.get(level, "")
    return price_id if price_id else None


def verify_webhook_signature(payload: bytes, sig_header: str) -> Any:
    """Verify a Stripe webhook signature and return the event.

    Args:
        payload: Raw request body bytes.
        sig_header: Stripe-Signature header value.

    Returns:
        Stripe Event object.

    Raises:
        ValueError: If signature verification fails.
    """
    stripe = get_stripe_client()
    if stripe is None:
        raise ValueError("Stripe is not configured")

    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET is not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        return event
    except stripe.error.SignatureVerificationError as e:
        logger.error("Stripe webhook signature verification failed: %s", str(e))
        raise ValueError(f"Invalid Stripe signature: {e}") from e
