"""
AirAd Backend — Payments Celery Tasks (Phase C §8)

Async Stripe operations as fallback if webhooks are missed.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="apps.payments.tasks.sync_subscription_status")
def sync_subscription_status(self: Any, vendor_id: str) -> None:
    """Pull latest subscription status from Stripe API and update local DB.

    Used as a fallback if a webhook event is missed. Can be triggered
    manually or via a periodic reconciliation task.

    Args:
        vendor_id: UUID string of the vendor to sync.
    """
    from django.conf import settings

    stripe_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not stripe_key:
        logger.warning("sync_subscription_status: STRIPE_SECRET_KEY not configured")
        return

    try:
        import stripe

        stripe.api_key = stripe_key

        from apps.payments.models import StripeCustomer, VendorSubscription

        try:
            stripe_customer = StripeCustomer.objects.get(vendor_id=vendor_id)
        except StripeCustomer.DoesNotExist:
            logger.info(
                "sync_subscription_status: no Stripe customer for vendor %s",
                vendor_id,
            )
            return

        # Fetch subscriptions from Stripe
        subscriptions = stripe.Subscription.list(
            customer=stripe_customer.stripe_customer_id,
            limit=1,
            status="all",
        )

        if not subscriptions.data:
            logger.info(
                "sync_subscription_status: no subscriptions found for vendor %s",
                vendor_id,
            )
            return

        sub = subscriptions.data[0]

        # Update or create local subscription record
        local_sub, created = VendorSubscription.objects.update_or_create(
            vendor_id=vendor_id,
            defaults={
                "stripe_subscription_id": sub.id,
                "status": sub.status.upper(),
                "current_period_start": sub.current_period_start,
                "current_period_end": sub.current_period_end,
            },
        )

        action = "created" if created else "updated"
        logger.info(
            "sync_subscription_status: %s subscription for vendor %s — status=%s",
            action,
            vendor_id,
            sub.status,
        )

    except Exception as exc:
        logger.error(
            "sync_subscription_status failed",
            extra={"vendor_id": vendor_id, "error": str(exc)},
        )
