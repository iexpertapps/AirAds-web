"""
AirAd Backend — Custom JWT Authentication for CustomerUser

SimpleJWT defaults to AUTH_USER_MODEL (AdminUser) for user lookup.
Vendor portal tokens are issued with CustomerUser IDs, so we need
a custom authentication class that resolves CustomerUser instead.
"""

import logging

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken

logger = logging.getLogger(__name__)


class CustomerUserJWTAuthentication(JWTAuthentication):
    """JWT authentication that resolves CustomerUser from the token."""

    def get_user(self, validated_token):
        """Look up CustomerUser by user_id claim instead of AUTH_USER_MODEL."""
        from apps.accounts.models import CustomerUser

        user_id = validated_token.get("user_id")
        if not user_id:
            raise InvalidToken("Token contained no recognizable user identification")

        try:
            user = CustomerUser.objects.get(id=user_id, is_active=True)
        except CustomerUser.DoesNotExist:
            raise AuthenticationFailed("User not found or inactive")

        return user
