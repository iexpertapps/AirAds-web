"""
AirAd Backend — Notification Celery Tasks (Phase B §B-10)

Async dispatch tasks for push, email, and SMS notifications.
Called by services or other Celery tasks — never by views directly.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_push_task(self, recipient_type: str, recipient_id: str, title: str, body: str, data: dict | None = None, device_token: str = ""):
    """Async push notification dispatch via FCM.

    Args:
        recipient_type: VENDOR or CUSTOMER.
        recipient_id: UUID of the recipient.
        title: Notification title.
        body: Notification body.
        data: Optional extra data payload.
        device_token: FCM device token.
    """
    from apps.notifications.services import send_push_notification

    try:
        send_push_notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            title=title,
            body=body,
            data=data,
            device_token=device_token,
        )
    except Exception as exc:
        logger.error("Push task failed: %s — retrying", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(self, recipient_type: str, recipient_id: str, email: str, title: str, body: str):
    """Async email notification dispatch.

    Args:
        recipient_type: VENDOR or CUSTOMER.
        recipient_id: UUID of the recipient.
        email: Recipient email address.
        title: Email subject.
        body: Email body (plain text).
    """
    from apps.notifications.services import send_email_notification

    try:
        send_email_notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            email=email,
            title=title,
            body=body,
        )
    except Exception as exc:
        logger.error("Email task failed: %s — retrying", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_sms_task(self, recipient_type: str, recipient_id: str, phone_number: str, body: str):
    """Async SMS notification dispatch.

    Args:
        recipient_type: VENDOR or CUSTOMER.
        recipient_id: UUID of the recipient.
        phone_number: Recipient phone number.
        body: SMS message body.
    """
    from apps.notifications.services import send_sms_notification

    try:
        send_sms_notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            phone_number=phone_number,
            body=body,
        )
    except Exception as exc:
        logger.error("SMS task failed: %s — retrying", exc)
        raise self.retry(exc=exc)
