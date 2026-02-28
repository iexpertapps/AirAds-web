"""
AirAd Backend — OTP Utility Functions (core/otp.py)

Centralised OTP generation, hashing, and rate-limit helpers.
Used by apps/accounts/otp_services.py. Abstracted here so other
modules (e.g. claim flow) can reuse without importing from accounts.
"""

import hashlib
import secrets


OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 3
OTP_RATE_LIMIT_SECONDS = 60


def generate_otp(length: int = OTP_LENGTH) -> str:
    """Generate a cryptographically secure numeric OTP code.

    Args:
        length: Number of digits (default 6).

    Returns:
        String of random digits, e.g. "482917".
    """
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_otp(otp: str) -> str:
    """SHA-256 hash an OTP code for secure storage.

    Args:
        otp: Raw OTP string.

    Returns:
        64-character hex SHA-256 digest.
    """
    return hashlib.sha256(otp.strip().encode("utf-8")).hexdigest()


def hash_phone(phone: str) -> str:
    """SHA-256 hash a phone number for unique lookups.

    Args:
        phone: Raw phone number in E.164 format.

    Returns:
        64-character hex SHA-256 digest.
    """
    return hashlib.sha256(phone.strip().encode("utf-8")).hexdigest()
