"""
AirAd Backend — OTP Auth Serializers (Phase B §3.2)

No business logic — validation only. All logic in otp_services.py.
"""

from rest_framework import serializers


class SendOTPSerializer(serializers.Serializer):
    """Serializer for POST /api/v1/auth/customer/send-otp/ and vendor equivalent."""

    phone = serializers.CharField(
        max_length=20,
        help_text="Phone number with country code (e.g. +923001234567).",
    )
    purpose = serializers.ChoiceField(
        choices=["LOGIN", "CLAIM_VERIFY", "EMAIL_VERIFY"],
        default="LOGIN",
        required=False,
    )

    def validate_phone(self, value: str) -> str:
        """Validate phone number format.

        Args:
            value: Raw phone number string.

        Returns:
            Stripped phone number.

        Raises:
            ValidationError: If phone is too short or doesn't start with +.
        """
        value = value.strip()
        if len(value) < 8:
            raise serializers.ValidationError("Phone number must be at least 8 characters.")
        if not value.startswith("+"):
            raise serializers.ValidationError("Phone number must include country code (e.g. +92...).")
        return value


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for POST /api/v1/auth/customer/verify-otp/ and vendor equivalent."""

    phone = serializers.CharField(max_length=20)
    otp = serializers.CharField(
        min_length=6,
        max_length=6,
        help_text="6-digit OTP code.",
    )
    purpose = serializers.ChoiceField(
        choices=["LOGIN", "CLAIM_VERIFY", "EMAIL_VERIFY"],
        default="LOGIN",
        required=False,
    )

    def validate_phone(self, value: str) -> str:
        """Validate phone format."""
        value = value.strip()
        if len(value) < 8:
            raise serializers.ValidationError("Phone number must be at least 8 characters.")
        if not value.startswith("+"):
            raise serializers.ValidationError("Phone number must include country code.")
        return value

    def validate_otp(self, value: str) -> str:
        """Validate OTP is exactly 6 digits."""
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain only digits.")
        return value


class CustomerProfileSerializer(serializers.Serializer):
    """Serializer for customer profile read/update."""

    id = serializers.UUIDField(read_only=True)
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    user_type = serializers.CharField(read_only=True)
    is_phone_verified = serializers.BooleanField(read_only=True)
    device_token = serializers.CharField(
        max_length=500, required=False, allow_blank=True, write_only=True
    )
    created_at = serializers.DateTimeField(read_only=True)


class CustomerProfileUpdateSerializer(serializers.Serializer):
    """Serializer for PATCH /api/v1/auth/customer/profile/."""

    full_name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False)
    device_token = serializers.CharField(max_length=500, required=False, allow_blank=True)
