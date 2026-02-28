"""
AirAd Backend — Notification Service Layer (Phase B §B-10, R4)

All notification dispatch logic lives here.
Push notifications use FCM via firebase-admin (graceful fallback to logger if not configured).
Every dispatch is logged in NotificationLog for audit and retry.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.notifications.models import (
    NotificationChannel,
    NotificationLog,
    NotificationStatus,
    NotificationTemplate,
    RecipientType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------

def render_template(slug: str, context: dict) -> tuple[str, str] | None:
    """Render a notification template with the given context.

    Args:
        slug: Template slug (e.g. "claim_approved").
        context: Dict of placeholder values.

    Returns:
        Tuple of (rendered_title, rendered_body) or None if template not found/inactive.
    """
    tpl = NotificationTemplate.objects.filter(slug=slug, is_active=True).first()
    if not tpl:
        logger.warning("Notification template not found or inactive: %s", slug)
        return None

    try:
        title = tpl.title_template.format(**context)
        body = tpl.body_template.format(**context)
    except KeyError as exc:
        logger.error("Template '%s' missing placeholder: %s", slug, exc)
        return None

    return title, body


# ---------------------------------------------------------------------------
# Push notification (FCM)
# ---------------------------------------------------------------------------

def _get_fcm_app():
    """Lazily initialise and return the Firebase app.

    Returns None if firebase-admin is not installed or credentials are not configured.
    """
    try:
        import firebase_admin  # noqa: F811
        from firebase_admin import credentials

        if not firebase_admin._apps:
            cred_path = getattr(settings, "FIREBASE_CREDENTIALS_JSON", "")
            if not cred_path:
                logger.debug("FIREBASE_CREDENTIALS_JSON not set — FCM disabled.")
                return None
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        return firebase_admin.get_app()
    except ImportError:
        logger.debug("firebase-admin not installed — FCM disabled.")
        return None
    except Exception as exc:
        logger.error("Firebase init error: %s", exc)
        return None


def send_push_notification(
    recipient_type: str,
    recipient_id: str,
    title: str,
    body: str,
    data: dict | None = None,
    *,
    device_token: str = "",
) -> NotificationLog:
    """Send a push notification via FCM and log the result.

    Args:
        recipient_type: VENDOR or CUSTOMER.
        recipient_id: UUID of the recipient.
        title: Notification title.
        body: Notification body.
        data: Optional extra data payload.
        device_token: FCM device token. If empty, looked up from CustomerUser.

    Returns:
        The created NotificationLog entry.
    """
    log_entry = NotificationLog.objects.create(
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        title=title,
        body=body,
        data_payload=data or {},
        channel=NotificationChannel.PUSH,
        status=NotificationStatus.PENDING,
    )

    # Resolve device token if not provided
    if not device_token:
        from apps.accounts.models import CustomerUser
        try:
            user = CustomerUser.objects.get(pk=recipient_id)
            device_token = user.device_token
        except CustomerUser.DoesNotExist:
            pass

    if not device_token:
        log_entry.status = NotificationStatus.FAILED
        log_entry.error_message = "No device token available."
        log_entry.save(update_fields=["status", "error_message"])
        logger.warning("Push skipped — no device token for %s:%s", recipient_type, recipient_id)
        return log_entry

    app = _get_fcm_app()
    if app is None:
        # Graceful fallback — log but don't fail
        log_entry.status = NotificationStatus.FAILED
        log_entry.error_message = "FCM not configured."
        log_entry.save(update_fields=["status", "error_message"])
        logger.info("Push logged (FCM disabled): [%s] %s — %s", recipient_type, title, body)
        return log_entry

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=device_token,
        )
        messaging.send(message)

        log_entry.status = NotificationStatus.SENT
        log_entry.sent_at = timezone.now()
        log_entry.save(update_fields=["status", "sent_at"])
        logger.info("Push sent to %s:%s — %s", recipient_type, recipient_id, title)
    except Exception as exc:
        log_entry.status = NotificationStatus.FAILED
        log_entry.error_message = str(exc)[:500]
        log_entry.save(update_fields=["status", "error_message"])
        logger.error("Push failed for %s:%s — %s", recipient_type, recipient_id, exc)

    return log_entry


# ---------------------------------------------------------------------------
# Email notification
# ---------------------------------------------------------------------------

def send_email_notification(
    recipient_type: str,
    recipient_id: str,
    email: str,
    title: str,
    body: str,
) -> NotificationLog:
    """Send an email notification and log the result.

    Args:
        recipient_type: VENDOR or CUSTOMER.
        recipient_id: UUID of the recipient.
        email: Recipient email address.
        title: Email subject.
        body: Email body (plain text).

    Returns:
        The created NotificationLog entry.
    """
    from django.core.mail import send_mail

    log_entry = NotificationLog.objects.create(
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        title=title,
        body=body,
        channel=NotificationChannel.EMAIL,
        status=NotificationStatus.PENDING,
    )

    if not email:
        log_entry.status = NotificationStatus.FAILED
        log_entry.error_message = "No email address."
        log_entry.save(update_fields=["status", "error_message"])
        return log_entry

    try:
        send_mail(
            subject=title,
            message=body,
            from_email=None,  # uses DEFAULT_FROM_EMAIL
            recipient_list=[email],
            fail_silently=False,
        )
        log_entry.status = NotificationStatus.SENT
        log_entry.sent_at = timezone.now()
        log_entry.save(update_fields=["status", "sent_at"])
        logger.info("Email sent to %s — %s", email, title)
    except Exception as exc:
        log_entry.status = NotificationStatus.FAILED
        log_entry.error_message = str(exc)[:500]
        log_entry.save(update_fields=["status", "error_message"])
        logger.error("Email failed to %s — %s", email, exc)

    return log_entry


# ---------------------------------------------------------------------------
# SMS notification
# ---------------------------------------------------------------------------

def send_sms_notification(
    recipient_type: str,
    recipient_id: str,
    phone_number: str,
    body: str,
) -> NotificationLog:
    """Send an SMS notification and log the result.

    Args:
        recipient_type: VENDOR or CUSTOMER.
        recipient_id: UUID of the recipient.
        phone_number: Recipient phone number (plaintext, decrypted by caller).
        body: SMS message body.

    Returns:
        The created NotificationLog entry.
    """
    log_entry = NotificationLog.objects.create(
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        title="SMS",
        body=body,
        channel=NotificationChannel.SMS,
        status=NotificationStatus.PENDING,
    )

    try:
        from core.sms import send_sms
        success = send_sms(phone_number, body)
        if success:
            log_entry.status = NotificationStatus.SENT
            log_entry.sent_at = timezone.now()
        else:
            log_entry.status = NotificationStatus.FAILED
            log_entry.error_message = "SMS send returned False."
        log_entry.save(update_fields=["status", "sent_at", "error_message"])
    except ImportError:
        log_entry.status = NotificationStatus.FAILED
        log_entry.error_message = "core.sms module not available."
        log_entry.save(update_fields=["status", "error_message"])
        logger.warning("SMS skipped — core.sms not available.")
    except Exception as exc:
        log_entry.status = NotificationStatus.FAILED
        log_entry.error_message = str(exc)[:500]
        log_entry.save(update_fields=["status", "error_message"])
        logger.error("SMS failed to %s — %s", recipient_id, exc)

    return log_entry


# ---------------------------------------------------------------------------
# Template-based dispatch (convenience)
# ---------------------------------------------------------------------------

def notify_from_template(
    slug: str,
    recipient_type: str,
    recipient_id: str,
    context: dict,
    channel: str = NotificationChannel.PUSH,
    *,
    device_token: str = "",
    email: str = "",
    phone_number: str = "",
    data: dict | None = None,
) -> NotificationLog | None:
    """Render a template and dispatch via the specified channel.

    Args:
        slug: Template slug.
        recipient_type: VENDOR or CUSTOMER.
        recipient_id: UUID of the recipient.
        context: Template placeholder values.
        channel: Delivery channel (PUSH, EMAIL, SMS).
        device_token: FCM token (for PUSH).
        email: Email address (for EMAIL).
        phone_number: Phone number (for SMS).
        data: Extra data payload (for PUSH).

    Returns:
        NotificationLog entry or None if template not found.
    """
    rendered = render_template(slug, context)
    if rendered is None:
        return None

    title, body = rendered

    if channel == NotificationChannel.PUSH:
        return send_push_notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            title=title,
            body=body,
            data=data,
            device_token=device_token,
        )
    elif channel == NotificationChannel.EMAIL:
        return send_email_notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            email=email,
            title=title,
            body=body,
        )
    elif channel == NotificationChannel.SMS:
        return send_sms_notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            phone_number=phone_number,
            body=body,
        )
    else:
        logger.error("Unknown notification channel: %s", channel)
        return None
