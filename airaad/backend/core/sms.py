"""
AirAd Backend — SMS Service Abstraction (core/sms.py)

Twilio integration for production, logger fallback for development.
Uses TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER from settings.
If Twilio credentials are not configured, falls back to logging (graceful dev mode).
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(phone_number: str, message: str) -> bool:
    """Send an SMS message via Twilio (production) or log it (development).

    Args:
        phone_number: Destination phone number in E.164 format (e.g. "+923001234567").
        message: The SMS message body.

    Returns:
        True if the SMS was sent (or logged) successfully, False on failure.
    """
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
    auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
    from_number = getattr(settings, "TWILIO_PHONE_NUMBER", "")

    if not all([account_sid, auth_token, from_number]):
        logger.info(
            "SMS (dev mode — Twilio not configured): to=%s message=%s",
            phone_number[:4] + "****" + phone_number[-2:] if len(phone_number) > 6 else phone_number,
            message[:50],
        )
        return True

    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        sms = client.messages.create(
            body=message,
            from_=from_number,
            to=phone_number,
        )
        logger.info(
            "SMS sent via Twilio",
            extra={
                "sid": sms.sid,
                "to": phone_number[:4] + "****" + phone_number[-2:],
                "status": sms.status,
            },
        )
        return True
    except Exception as exc:
        logger.error(
            "SMS send failed",
            extra={
                "to": phone_number[:4] + "****" + phone_number[-2:] if len(phone_number) > 6 else phone_number,
                "error": str(exc),
            },
        )
        return False
