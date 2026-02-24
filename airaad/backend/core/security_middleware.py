"""
AirAd Backend — Security Headers Middleware

Adds all required security headers to every HTTP response:
- Content-Security-Policy
- Permissions-Policy
- Referrer-Policy
- X-Content-Type-Options (reinforced)
- Cache-Control for authenticated responses

Must be placed AFTER SecurityMiddleware in settings.MIDDLEWARE.
"""

import logging
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """Add comprehensive security headers to every response.

    Complements Django's SecurityMiddleware with headers that Django
    does not set by default: CSP, Permissions-Policy, Referrer-Policy,
    and Cache-Control for authenticated responses.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response: HttpResponse = self.get_response(request)

        # Content-Security-Policy — strict default, allow self only
        if not response.get("Content-Security-Policy"):
            response["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )

        # Permissions-Policy — disable all sensitive browser features
        if not response.get("Permissions-Policy"):
            response["Permissions-Policy"] = (
                "camera=(), microphone=(), geolocation=(), "
                "payment=(), usb=(), magnetometer=(), "
                "gyroscope=(), accelerometer=()"
            )

        # Referrer-Policy
        if not response.get("Referrer-Policy"):
            response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Reinforce X-Content-Type-Options (Django SecurityMiddleware also sets this)
        response["X-Content-Type-Options"] = "nosniff"

        # Prevent caching of authenticated API responses
        if hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response["Pragma"] = "no-cache"

        return response
