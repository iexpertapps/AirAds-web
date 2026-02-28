"""
AirAd Backend — Stripe Payment Services (Phase C §8)

All Stripe business logic lives here — views only call these functions.
Every mutation calls log_action() (R5).
Idempotency enforced via StripeEvent table.
"""

import logging
from datetime import datetime, timezone as dt_tz
from typing import Any

import stripe
from django.conf import settings
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.audit.utils import log_action

from .models import (
    StripeCustomer,
    StripeEvent,
    SubscriptionStatus,
    VendorSubscription,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stripe Price ID mapping — maps subscription level to Stripe Price ID.
# Set these in environment variables.
# ---------------------------------------------------------------------------
LEVEL_TO_PRICE_MAP: dict[str, str] = {}


def _init_stripe() -> None:
    """Initialize the Stripe API key from settings."""
    stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")


def _get_price_map() -> dict[str, str]:
    """Load the Stripe Price ID → subscription level mapping from settings."""
    global LEVEL_TO_PRICE_MAP
    if not LEVEL_TO_PRICE_MAP:
        LEVEL_TO_PRICE_MAP = {
            "GOLD": getattr(settings, "STRIPE_PRICE_GOLD", ""),
            "DIAMOND": getattr(settings, "STRIPE_PRICE_DIAMOND", ""),
            "PLATINUM": getattr(settings, "STRIPE_PRICE_PLATINUM", ""),
        }
    return LEVEL_TO_PRICE_MAP


def _price_to_level(price_id: str) -> str:
    """Reverse-map a Stripe Price ID to a subscription level.

    Args:
        price_id: Stripe Price ID string.

    Returns:
        Subscription level string (GOLD, DIAMOND, PLATINUM) or SILVER as fallback.
    """
    price_map = _get_price_map()
    for level, pid in price_map.items():
        if pid == price_id:
            return level
    return "SILVER"


# ---------------------------------------------------------------------------
# Stripe Customer Management
# ---------------------------------------------------------------------------

def get_or_create_stripe_customer(vendor_id: str) -> StripeCustomer:
    """Get or create a Stripe Customer for a vendor.

    Args:
        vendor_id: UUID of the Vendor.

    Returns:
        StripeCustomer instance.
    """
    from apps.vendors.models import Vendor

    _init_stripe()

    try:
        return StripeCustomer.objects.get(vendor_id=vendor_id)
    except StripeCustomer.DoesNotExist:
        pass

    vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)

    customer = stripe.Customer.create(
        name=vendor.business_name,
        metadata={
            "vendor_id": str(vendor.id),
            "vendor_slug": vendor.slug,
        },
    )

    sc = StripeCustomer.objects.create(
        vendor=vendor,
        stripe_customer_id=customer.id,
    )

    logger.info(
        "Stripe customer created",
        extra={"vendor_id": str(vendor.id), "stripe_customer_id": customer.id},
    )

    return sc


# ---------------------------------------------------------------------------
# Checkout Session
# ---------------------------------------------------------------------------

def create_checkout_session(
    vendor_id: str,
    level: str,
    success_url: str,
    cancel_url: str,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Create a Stripe Checkout Session for subscription purchase.

    Args:
        vendor_id: UUID of the Vendor.
        level: Target subscription level (GOLD, DIAMOND, PLATINUM).
        success_url: URL to redirect on success (include {CHECKOUT_SESSION_ID}).
        cancel_url: URL to redirect on cancel.
        request: HTTP request for audit.

    Returns:
        Dict with session_id and checkout_url.

    Raises:
        ValueError: If level is invalid or price not configured.
    """
    _init_stripe()
    price_map = _get_price_map()
    price_id = price_map.get(level)

    if not price_id:
        raise ValueError(
            f"Invalid subscription level '{level}'. Choose GOLD, DIAMOND, or PLATINUM."
        )

    sc = get_or_create_stripe_customer(vendor_id)

    session = stripe.checkout.Session.create(
        customer=sc.stripe_customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "vendor_id": vendor_id,
            "target_level": level,
        },
        subscription_data={
            "metadata": {
                "vendor_id": vendor_id,
                "target_level": level,
            },
        },
    )

    log_action(
        action="STRIPE_CHECKOUT_CREATED",
        actor=None,
        target_obj=sc,
        request=request,
        before={},
        after={
            "session_id": session.id,
            "target_level": level,
            "vendor_id": vendor_id,
        },
    )

    return {
        "session_id": session.id,
        "checkout_url": session.url,
    }


# ---------------------------------------------------------------------------
# Customer Portal Session
# ---------------------------------------------------------------------------

def create_portal_session(
    vendor_id: str,
    return_url: str,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Create a Stripe Customer Portal session for billing management.

    Args:
        vendor_id: UUID of the Vendor.
        return_url: URL to redirect when the customer leaves the portal.
        request: HTTP request for audit.

    Returns:
        Dict with portal_url.

    Raises:
        ValueError: If no Stripe customer exists for this vendor.
    """
    _init_stripe()

    try:
        sc = StripeCustomer.objects.get(vendor_id=vendor_id)
    except StripeCustomer.DoesNotExist:
        raise ValueError("No Stripe customer found for this vendor. Subscribe first.")

    session = stripe.billing_portal.Session.create(
        customer=sc.stripe_customer_id,
        return_url=return_url,
    )

    return {"portal_url": session.url}


# ---------------------------------------------------------------------------
# Subscription Status
# ---------------------------------------------------------------------------

def get_subscription_status(vendor_id: str) -> dict[str, Any]:
    """Get the current subscription status for a vendor.

    Args:
        vendor_id: UUID of the Vendor.

    Returns:
        Dict with subscription info or null if no subscription.
    """
    from apps.vendors.models import Vendor

    vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)

    try:
        vs = VendorSubscription.objects.get(vendor_id=vendor_id)
    except VendorSubscription.DoesNotExist:
        return {
            "has_subscription": False,
            "level": vendor.subscription_level or "SILVER",
            "status": None,
            "current_period_end": None,
            "cancel_at_period_end": False,
        }

    return {
        "has_subscription": True,
        "level": vendor.subscription_level or "SILVER",
        "status": vs.status,
        "stripe_subscription_id": vs.stripe_subscription_id,
        "current_period_start": (
            vs.current_period_start.isoformat() if vs.current_period_start else None
        ),
        "current_period_end": (
            vs.current_period_end.isoformat() if vs.current_period_end else None
        ),
        "cancel_at_period_end": vs.cancel_at_period_end,
        "canceled_at": vs.canceled_at.isoformat() if vs.canceled_at else None,
    }


# ---------------------------------------------------------------------------
# Invoice History
# ---------------------------------------------------------------------------

def get_invoices(vendor_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Get invoice history from Stripe for a vendor.

    Args:
        vendor_id: UUID of the Vendor.
        limit: Max number of invoices to return.

    Returns:
        List of invoice dicts.
    """
    _init_stripe()

    try:
        sc = StripeCustomer.objects.get(vendor_id=vendor_id)
    except StripeCustomer.DoesNotExist:
        return []

    invoices = stripe.Invoice.list(
        customer=sc.stripe_customer_id,
        limit=limit,
    )

    results = []
    for inv in invoices.data:
        results.append({
            "id": inv.id,
            "number": inv.number,
            "status": inv.status,
            "amount_due": inv.amount_due,
            "amount_paid": inv.amount_paid,
            "currency": inv.currency,
            "created": datetime.fromtimestamp(inv.created, tz=dt_tz.utc).isoformat(),
            "hosted_invoice_url": inv.hosted_invoice_url,
            "invoice_pdf": inv.invoice_pdf,
        })

    return results


# ---------------------------------------------------------------------------
# Cancel / Resume Subscription
# ---------------------------------------------------------------------------

@transaction.atomic
def cancel_subscription(
    vendor_id: str,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Cancel a vendor's subscription at end of billing period.

    Does NOT immediately downgrade — waits for period end.
    Stripe webhook handles actual downgrade.

    Args:
        vendor_id: UUID of the Vendor.
        request: HTTP request for audit.

    Returns:
        Dict confirming cancellation.

    Raises:
        ValueError: If no active subscription exists.
    """
    _init_stripe()

    try:
        vs = VendorSubscription.objects.get(vendor_id=vendor_id)
    except VendorSubscription.DoesNotExist:
        raise ValueError("No active subscription to cancel.")

    if vs.status == SubscriptionStatus.CANCELED:
        raise ValueError("Subscription is already canceled.")

    stripe.Subscription.modify(
        vs.stripe_subscription_id,
        cancel_at_period_end=True,
    )

    vs.cancel_at_period_end = True
    vs.canceled_at = timezone.now()
    vs.save(update_fields=["cancel_at_period_end", "canceled_at", "updated_at"])

    log_action(
        action="STRIPE_SUBSCRIPTION_CANCEL_REQUESTED",
        actor=None,
        target_obj=vs,
        request=request,
        before={"cancel_at_period_end": False},
        after={"cancel_at_period_end": True},
    )

    return {
        "vendor_id": vendor_id,
        "stripe_subscription_id": vs.stripe_subscription_id,
        "cancel_at_period_end": True,
        "message": "Subscription will cancel at end of current billing period.",
    }


@transaction.atomic
def resume_subscription(
    vendor_id: str,
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Resume a subscription that was set to cancel at period end.

    Args:
        vendor_id: UUID of the Vendor.
        request: HTTP request for audit.

    Returns:
        Dict confirming resumption.

    Raises:
        ValueError: If subscription is not pending cancellation.
    """
    _init_stripe()

    try:
        vs = VendorSubscription.objects.get(vendor_id=vendor_id)
    except VendorSubscription.DoesNotExist:
        raise ValueError("No subscription found.")

    if not vs.cancel_at_period_end:
        raise ValueError("Subscription is not pending cancellation.")

    stripe.Subscription.modify(
        vs.stripe_subscription_id,
        cancel_at_period_end=False,
    )

    vs.cancel_at_period_end = False
    vs.canceled_at = None
    vs.save(update_fields=["cancel_at_period_end", "canceled_at", "updated_at"])

    log_action(
        action="STRIPE_SUBSCRIPTION_RESUMED",
        actor=None,
        target_obj=vs,
        request=request,
        before={"cancel_at_period_end": True},
        after={"cancel_at_period_end": False},
    )

    return {
        "vendor_id": vendor_id,
        "stripe_subscription_id": vs.stripe_subscription_id,
        "cancel_at_period_end": False,
        "message": "Subscription resumed. It will continue at end of billing period.",
    }


# ---------------------------------------------------------------------------
# Webhook Event Processing
# ---------------------------------------------------------------------------

def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Construct and verify a Stripe webhook event.

    Args:
        payload: Raw request body bytes.
        sig_header: Stripe-Signature header value.

    Returns:
        Verified Stripe Event object.

    Raises:
        ValueError: If signature verification fails.
    """
    _init_stripe()
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")

    if not endpoint_secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except stripe.error.SignatureVerificationError as e:
        raise ValueError(f"Invalid webhook signature: {e}") from e

    return event


@transaction.atomic
def process_webhook_event(event: stripe.Event) -> dict[str, Any]:
    """Process a Stripe webhook event with idempotency.

    Checks StripeEvent table first — skips if already processed.
    Dispatches to specific handlers based on event type.

    Args:
        event: Verified Stripe Event object.

    Returns:
        Dict with processing result.
    """
    event_id = event.id
    event_type = event.type

    existing = StripeEvent.objects.filter(stripe_event_id=event_id).first()
    if existing and existing.processed:
        logger.info("Webhook event already processed — skipping", extra={"event_id": event_id})
        return {"status": "already_processed", "event_id": event_id}

    if existing is None:
        existing = StripeEvent.objects.create(
            stripe_event_id=event_id,
            event_type=event_type,
            data=event.data.object if hasattr(event.data, "object") else {},
        )

    try:
        handler = _EVENT_HANDLERS.get(event_type)
        if handler:
            handler(event)
            existing.processed = True
            existing.save(update_fields=["processed"])
            logger.info(
                "Webhook event processed",
                extra={"event_id": event_id, "event_type": event_type},
            )
            return {"status": "processed", "event_id": event_id, "event_type": event_type}
        else:
            existing.processed = True
            existing.error_message = f"No handler for event type: {event_type}"
            existing.save(update_fields=["processed", "error_message"])
            logger.debug("No handler for webhook event type %s", event_type)
            return {"status": "ignored", "event_id": event_id, "event_type": event_type}

    except Exception as exc:
        existing.error_message = str(exc)[:2000]
        existing.save(update_fields=["error_message"])
        logger.error(
            "Webhook event processing failed",
            extra={"event_id": event_id, "event_type": event_type, "error": str(exc)},
            exc_info=True,
        )
        raise


# ---------------------------------------------------------------------------
# Individual Event Handlers
# ---------------------------------------------------------------------------

def _handle_checkout_session_completed(event: stripe.Event) -> None:
    """Handle checkout.session.completed — create subscription record.

    Flow:
    1. Extract vendor_id and target_level from metadata.
    2. Get or create VendorSubscription.
    3. Update vendor's subscription_level and valid_until.
    4. Log audit entry.
    """
    session = event.data.object
    vendor_id = session.metadata.get("vendor_id")
    target_level = session.metadata.get("target_level", "GOLD")
    stripe_subscription_id = session.subscription

    if not vendor_id or not stripe_subscription_id:
        logger.warning("checkout.session.completed missing vendor_id or subscription")
        return

    from apps.vendors.models import Vendor

    try:
        vendor = Vendor.objects.get(id=vendor_id, is_deleted=False)
    except Vendor.DoesNotExist:
        logger.error("checkout.session.completed: vendor %s not found", vendor_id)
        return

    _init_stripe()
    sub = stripe.Subscription.retrieve(stripe_subscription_id)

    vs, created = VendorSubscription.objects.update_or_create(
        vendor=vendor,
        defaults={
            "stripe_subscription_id": stripe_subscription_id,
            "stripe_price_id": sub.items.data[0].price.id if sub.items.data else "",
            "status": SubscriptionStatus.ACTIVE,
            "current_period_start": _ts_to_dt(sub.current_period_start),
            "current_period_end": _ts_to_dt(sub.current_period_end),
            "cancel_at_period_end": sub.cancel_at_period_end,
        },
    )

    before_level = vendor.subscription_level
    vendor.subscription_level = target_level
    vendor.subscription_valid_until = _ts_to_dt(sub.current_period_end)
    vendor.save(update_fields=["subscription_level", "subscription_valid_until", "updated_at"])

    log_action(
        action="STRIPE_SUBSCRIPTION_CREATED",
        actor=None,
        target_obj=vendor,
        request=None,
        before={"subscription_level": before_level},
        after={
            "subscription_level": target_level,
            "stripe_subscription_id": stripe_subscription_id,
        },
    )


def _handle_invoice_paid(event: stripe.Event) -> None:
    """Handle invoice.paid — update subscription period.

    Extends the subscription's current_period_end.
    """
    invoice = event.data.object
    stripe_subscription_id = invoice.subscription

    if not stripe_subscription_id:
        return

    try:
        vs = VendorSubscription.objects.get(
            stripe_subscription_id=stripe_subscription_id
        )
    except VendorSubscription.DoesNotExist:
        logger.warning("invoice.paid: subscription %s not found", stripe_subscription_id)
        return

    _init_stripe()
    sub = stripe.Subscription.retrieve(stripe_subscription_id)

    vs.status = SubscriptionStatus.ACTIVE
    vs.current_period_start = _ts_to_dt(sub.current_period_start)
    vs.current_period_end = _ts_to_dt(sub.current_period_end)
    vs.save(update_fields=[
        "status", "current_period_start", "current_period_end", "updated_at"
    ])

    vendor = vs.vendor
    vendor.subscription_valid_until = _ts_to_dt(sub.current_period_end)
    vendor.save(update_fields=["subscription_valid_until", "updated_at"])

    log_action(
        action="STRIPE_INVOICE_PAID",
        actor=None,
        target_obj=vendor,
        request=None,
        before={},
        after={
            "stripe_subscription_id": stripe_subscription_id,
            "period_end": vs.current_period_end.isoformat() if vs.current_period_end else None,
        },
    )


def _handle_invoice_payment_failed(event: stripe.Event) -> None:
    """Handle invoice.payment_failed — mark subscription PAST_DUE."""
    invoice = event.data.object
    stripe_subscription_id = invoice.subscription

    if not stripe_subscription_id:
        return

    try:
        vs = VendorSubscription.objects.get(
            stripe_subscription_id=stripe_subscription_id
        )
    except VendorSubscription.DoesNotExist:
        return

    vs.status = SubscriptionStatus.PAST_DUE
    vs.save(update_fields=["status", "updated_at"])

    log_action(
        action="STRIPE_PAYMENT_FAILED",
        actor=None,
        target_obj=vs.vendor,
        request=None,
        before={"status": "ACTIVE"},
        after={"status": "PAST_DUE", "stripe_subscription_id": stripe_subscription_id},
    )


def _handle_subscription_updated(event: stripe.Event) -> None:
    """Handle customer.subscription.updated — handle upgrade/downgrade."""
    sub_obj = event.data.object
    stripe_subscription_id = sub_obj.id

    try:
        vs = VendorSubscription.objects.get(
            stripe_subscription_id=stripe_subscription_id
        )
    except VendorSubscription.DoesNotExist:
        return

    new_price_id = sub_obj.items.data[0].price.id if sub_obj.items.data else ""
    new_level = _price_to_level(new_price_id)
    new_status = _map_stripe_status(sub_obj.status)

    before_level = vs.vendor.subscription_level
    vs.stripe_price_id = new_price_id
    vs.status = new_status
    vs.current_period_start = _ts_to_dt(sub_obj.current_period_start)
    vs.current_period_end = _ts_to_dt(sub_obj.current_period_end)
    vs.cancel_at_period_end = sub_obj.cancel_at_period_end
    vs.save(update_fields=[
        "stripe_price_id", "status", "current_period_start",
        "current_period_end", "cancel_at_period_end", "updated_at",
    ])

    vendor = vs.vendor
    if new_level != before_level:
        vendor.subscription_level = new_level
    vendor.subscription_valid_until = _ts_to_dt(sub_obj.current_period_end)
    vendor.save(update_fields=["subscription_level", "subscription_valid_until", "updated_at"])

    log_action(
        action="STRIPE_SUBSCRIPTION_UPDATED",
        actor=None,
        target_obj=vendor,
        request=None,
        before={"subscription_level": before_level},
        after={
            "subscription_level": new_level,
            "status": new_status,
            "cancel_at_period_end": sub_obj.cancel_at_period_end,
        },
    )


def _handle_subscription_deleted(event: stripe.Event) -> None:
    """Handle customer.subscription.deleted — downgrade to SILVER."""
    sub_obj = event.data.object
    stripe_subscription_id = sub_obj.id

    try:
        vs = VendorSubscription.objects.get(
            stripe_subscription_id=stripe_subscription_id
        )
    except VendorSubscription.DoesNotExist:
        return

    before_level = vs.vendor.subscription_level

    vs.status = SubscriptionStatus.CANCELED
    vs.cancel_at_period_end = False
    vs.save(update_fields=["status", "cancel_at_period_end", "updated_at"])

    vendor = vs.vendor
    vendor.subscription_level = "SILVER"
    vendor.subscription_valid_until = None
    vendor.save(update_fields=["subscription_level", "subscription_valid_until", "updated_at"])

    log_action(
        action="STRIPE_SUBSCRIPTION_DELETED",
        actor=None,
        target_obj=vendor,
        request=None,
        before={"subscription_level": before_level},
        after={"subscription_level": "SILVER", "status": "CANCELED"},
    )


# ---------------------------------------------------------------------------
# Handler dispatch map
# ---------------------------------------------------------------------------

_EVENT_HANDLERS: dict[str, Any] = {
    "checkout.session.completed": _handle_checkout_session_completed,
    "invoice.paid": _handle_invoice_paid,
    "invoice.payment_failed": _handle_invoice_payment_failed,
    "customer.subscription.updated": _handle_subscription_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
}


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _ts_to_dt(ts: int | None) -> datetime | None:
    """Convert a Unix timestamp to a timezone-aware datetime."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=dt_tz.utc)


def _map_stripe_status(status: str) -> str:
    """Map Stripe's subscription status string to our SubscriptionStatus."""
    mapping = {
        "active": SubscriptionStatus.ACTIVE,
        "past_due": SubscriptionStatus.PAST_DUE,
        "canceled": SubscriptionStatus.CANCELED,
        "incomplete": SubscriptionStatus.INCOMPLETE,
        "trialing": SubscriptionStatus.TRIALING,
        "unpaid": SubscriptionStatus.UNPAID,
    }
    return mapping.get(status, SubscriptionStatus.INCOMPLETE)
