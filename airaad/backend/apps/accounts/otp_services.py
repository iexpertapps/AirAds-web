"""
AirAd Backend — OTP Auth Service Layer (Phase B §3.2)

All OTP business logic lives here — never in views or serializers.
Phone numbers are hashed (SHA-256) for lookups and encrypted (AES-256-GCM) for storage.
OTP codes are hashed (SHA-256) before storage — never stored in plaintext.
Every mutation calls log_action() (R5).
"""

import hashlib
import logging
import secrets
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.audit.utils import log_action
from core.encryption import encrypt
from core.utils import get_client_ip

from .models import CustomerUser, OTPRequest, UserType

logger = logging.getLogger(__name__)

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 3
OTP_RATE_LIMIT_SECONDS = 60


def _hash_phone(phone: str) -> str:
    """Generate SHA-256 hash of a phone number for unique lookups.

    Args:
        phone: Raw phone number string (e.g. "+923001234567").

    Returns:
        64-character hex SHA-256 hash.
    """
    return hashlib.sha256(phone.strip().encode("utf-8")).hexdigest()


def _hash_otp(otp: str) -> str:
    """Generate SHA-256 hash of an OTP code for storage.

    Args:
        otp: Raw OTP code string.

    Returns:
        64-character hex SHA-256 hash.
    """
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def _generate_otp() -> str:
    """Generate a 6-digit OTP code.

    If settings.MANUAL_OTP_CODE is set (non-empty), returns that fixed code
    instead of a random one. This is the temporary manual mode for development
    without Twilio. When Twilio is integrated, set MANUAL_OTP_CODE="" to
    switch to real random OTPs.

    Returns:
        6-digit string (zero-padded).
    """
    from django.conf import settings

    manual_code = getattr(settings, "MANUAL_OTP_CODE", "")
    if manual_code:
        logger.info("OTP manual mode active — using fixed code")
        return manual_code.zfill(OTP_LENGTH)[:OTP_LENGTH]
    return f"{secrets.randbelow(10**OTP_LENGTH):0{OTP_LENGTH}d}"


def send_otp(
    phone: str,
    purpose: str = "LOGIN",
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Generate and send an OTP to the given phone number.

    Rate limited: max 1 OTP per phone per 60 seconds.
    OTP is hashed before storage — plaintext is only sent via SMS.

    In development/testing, the OTP is included in the response for convenience.
    In production, it is sent via SMS (Twilio abstraction layer).

    Args:
        phone: Raw phone number string.
        purpose: OTP purpose (LOGIN, CLAIM_VERIFY, EMAIL_VERIFY).
        request: HTTP request for audit tracing.

    Returns:
        Dict with success status and message.

    Raises:
        ValueError: If phone is empty or rate limited.
    """
    if not phone or not phone.strip():
        raise ValueError("Phone number is required")

    phone = phone.strip()
    phone_hash = _hash_phone(phone)

    recent_otp = OTPRequest.objects.filter(
        phone_hash=phone_hash,
        created_at__gte=timezone.now() - timedelta(seconds=OTP_RATE_LIMIT_SECONDS),
    ).first()

    if recent_otp is not None:
        raise ValueError(
            f"OTP already sent. Please wait {OTP_RATE_LIMIT_SECONDS} seconds before requesting again."
        )

    otp_code = _generate_otp()
    otp_hash = _hash_otp(otp_code)

    otp_request = OTPRequest.objects.create(
        phone_hash=phone_hash,
        otp_hash=otp_hash,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )

    _send_sms(phone, otp_code)

    log_action(
        action="OTP_SENT",
        actor=None,
        target_obj=otp_request,
        request=request,
        before={},
        after={"phone_hash": phone_hash[:8] + "...", "purpose": purpose},
    )

    from django.conf import settings

    result: dict[str, Any] = {
        "success": True,
        "message": f"OTP sent to {phone[:4]}****{phone[-2:]}",
        "expires_in_seconds": OTP_EXPIRY_MINUTES * 60,
    }

    if getattr(settings, "DEBUG", False) or getattr(settings, "TESTING", False):
        result["otp"] = otp_code

    return result


def _send_sms(phone: str, otp_code: str) -> None:
    """Send OTP via SMS using core.sms abstraction layer.

    Uses Twilio in production, logs in development (graceful fallback).
    When MANUAL_OTP_CODE is set, skips SMS entirely and only logs — this is
    the temporary manual mode. To enable real SMS: clear MANUAL_OTP_CODE and
    configure TWILIO_* env vars.

    Args:
        phone: Destination phone number.
        otp_code: The OTP code to send.
    """
    from django.conf import settings

    manual_code = getattr(settings, "MANUAL_OTP_CODE", "")
    if manual_code:
        masked = phone[:4] + "****" + phone[-2:] if len(phone) > 6 else phone
        logger.info(
            "OTP manual mode — SMS skipped (to=%s, code=%s)",
            masked,
            otp_code,
        )
        return

    from core.sms import send_sms

    message = f"Your AirAd verification code is: {otp_code}. Valid for {OTP_EXPIRY_MINUTES} minutes."
    send_sms(phone, message)


def verify_otp_code(phone: str, otp_code: str) -> bool:
    """Verify an OTP code without creating/logging in a user.

    Used by claim flow to verify OTP for automated claim approval.

    Args:
        phone: Raw phone number string.
        otp_code: The OTP code to verify.

    Returns:
        True if the OTP is valid, False otherwise.
    """
    if not phone or not otp_code:
        return False

    phone_hash = _hash_phone(phone.strip())
    otp_hash = _hash_otp(otp_code.strip())

    otp_request = (
        OTPRequest.objects.filter(
            phone_hash=phone_hash,
            is_used=False,
        )
        .order_by("-created_at")
        .first()
    )

    if otp_request is None:
        return False

    if otp_request.is_expired:
        return False

    if otp_request.attempts >= MAX_OTP_ATTEMPTS:
        return False

    otp_request.attempts += 1
    otp_request.save(update_fields=["attempts"])

    if otp_request.otp_hash != otp_hash:
        return False

    otp_request.is_used = True
    otp_request.save(update_fields=["is_used"])
    return True


@transaction.atomic
def verify_otp(
    phone: str,
    otp_code: str,
    purpose: str = "LOGIN",
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    """Verify an OTP code and create/login the customer user.

    On successful verification:
    1. Marks OTP as used
    2. Creates CustomerUser if first login (phone_hash not found)
    3. Returns JWT tokens (access + refresh) with user_type in claims

    Args:
        phone: Raw phone number string.
        otp_code: The OTP code to verify.
        purpose: Expected OTP purpose.
        request: HTTP request for audit tracing.

    Returns:
        Dict with JWT tokens, user data, and is_new_user flag.

    Raises:
        ValueError: If OTP is invalid, expired, or max attempts exceeded.
    """
    if not phone or not otp_code:
        raise ValueError("Phone number and OTP code are required")

    phone = phone.strip()
    phone_hash = _hash_phone(phone)
    otp_hash = _hash_otp(otp_code.strip())

    otp_request = (
        OTPRequest.objects.filter(
            phone_hash=phone_hash,
            purpose=purpose,
            is_used=False,
        )
        .order_by("-created_at")
        .first()
    )

    if otp_request is None:
        raise ValueError("No pending OTP found for this phone number")

    if otp_request.is_expired:
        raise ValueError("OTP has expired. Please request a new one.")

    if otp_request.attempts >= MAX_OTP_ATTEMPTS:
        raise ValueError("Maximum verification attempts exceeded. Please request a new OTP.")

    otp_request.attempts += 1
    otp_request.save(update_fields=["attempts"])

    if otp_request.otp_hash != otp_hash:
        remaining = MAX_OTP_ATTEMPTS - otp_request.attempts
        raise ValueError(f"Invalid OTP code. {remaining} attempt(s) remaining.")

    otp_request.is_used = True
    otp_request.save(update_fields=["is_used"])

    is_new_user = False
    customer = CustomerUser.objects.filter(phone_hash=phone_hash).first()

    if customer is None:
        phone_encrypted = encrypt(phone)
        customer = CustomerUser.objects.create(
            phone_hash=phone_hash,
            phone_encrypted=phone_encrypted,
            is_phone_verified=True,
            user_type=UserType.CUSTOMER,
        )
        is_new_user = True

        log_action(
            action="CUSTOMER_CREATED",
            actor=None,
            target_obj=customer,
            request=request,
            before={},
            after={
                "phone_hash": phone_hash[:8] + "...",
                "user_type": customer.user_type,
            },
        )
    else:
        if not customer.is_active:
            raise ValueError("Account is deactivated. Please contact support.")
        customer.is_phone_verified = True

    ip_address = get_client_ip(request) if request else None
    customer.last_login_at = timezone.now()
    customer.last_login_ip = ip_address
    customer.save(
        update_fields=[
            "is_phone_verified",
            "last_login_at",
            "last_login_ip",
            "updated_at",
        ]
    )

    log_action(
        action="CUSTOMER_OTP_LOGIN",
        actor=None,
        target_obj=customer,
        request=request,
        before={},
        after={
            "phone_hash": phone_hash[:8] + "...",
            "is_new_user": is_new_user,
            "ip": ip_address or "unknown",
        },
    )

    tokens = _generate_customer_tokens(customer)

    return {
        "tokens": tokens,
        "user": {
            "id": str(customer.id),
            "full_name": customer.full_name,
            "email": customer.email,
            "user_type": customer.user_type,
            "is_phone_verified": customer.is_phone_verified,
        },
        "is_new_user": is_new_user,
    }


def _generate_customer_tokens(customer: CustomerUser) -> dict[str, str]:
    """Generate JWT access and refresh tokens for a CustomerUser.

    Tokens include user_type, full_name, and email in claims.

    Args:
        customer: The authenticated CustomerUser.

    Returns:
        Dict with access and refresh token strings.
    """
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken()
    refresh["user_id"] = str(customer.id)
    refresh["user_type"] = customer.user_type
    refresh["full_name"] = customer.full_name
    refresh["email"] = customer.email

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


@transaction.atomic
def update_customer_profile(
    customer: CustomerUser,
    updates: dict[str, Any],
    request: HttpRequest | None = None,
) -> CustomerUser:
    """Update a customer's profile fields.

    Args:
        customer: The CustomerUser to update.
        updates: Dict of field names to new values.
        request: HTTP request for audit tracing.

    Returns:
        Updated CustomerUser instance.
    """
    before = {
        "full_name": customer.full_name,
        "email": customer.email,
    }

    allowed_fields = {"full_name", "email", "device_token"}
    changed_fields: list[str] = []

    for field, value in updates.items():
        if field in allowed_fields:
            setattr(customer, field, value)
            changed_fields.append(field)

    if changed_fields:
        save_fields = list(dict.fromkeys(changed_fields + ["updated_at"]))
        customer.save(update_fields=save_fields)

        log_action(
            action="CUSTOMER_PROFILE_UPDATED",
            actor=None,
            target_obj=customer,
            request=request,
            before=before,
            after={
                "full_name": customer.full_name,
                "email": customer.email,
            },
        )

    return customer
