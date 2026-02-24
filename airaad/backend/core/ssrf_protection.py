"""
AirAd Backend — SSRF Protection

Validates external URLs against an allowlist before making outbound HTTP requests.
All external HTTP calls MUST use validate_external_url() before fetching.
"""

import logging
from urllib.parse import urlparse

from django.conf import settings

logger = logging.getLogger(__name__)


class SSRFError(Exception):
    """Raised when an outbound URL fails the SSRF allowlist check."""


def validate_external_url(url: str) -> str:
    """Validate that a URL targets an allowed external domain.

    All outbound HTTP requests MUST pass through this function before
    being executed. Only domains listed in settings.ALLOWED_EXTERNAL_DOMAINS
    are permitted.

    Args:
        url: The URL to validate.

    Returns:
        The validated URL string (unchanged).

    Raises:
        SSRFError: If the URL's domain is not in the allowlist.
        ValueError: If the URL is malformed or empty.
    """
    if not url:
        raise ValueError("URL must not be empty")

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise SSRFError(f"Only HTTP/HTTPS schemes are allowed, got: {parsed.scheme!r}")

    if not parsed.hostname:
        raise SSRFError(f"URL has no hostname: {url!r}")

    hostname = parsed.hostname.lower()

    # Block private/internal IP ranges
    _BLOCKED_PREFIXES = (
        "127.",
        "10.",
        "172.16.",
        "172.17.",
        "172.18.",
        "172.19.",
        "172.20.",
        "172.21.",
        "172.22.",
        "172.23.",
        "172.24.",
        "172.25.",
        "172.26.",
        "172.27.",
        "172.28.",
        "172.29.",
        "172.30.",
        "172.31.",
        "192.168.",
        "0.",
        "169.254.",
    )
    _BLOCKED_HOSTS = ("localhost", "metadata.google.internal", "[::1]")

    if hostname in _BLOCKED_HOSTS or any(
        hostname.startswith(p) for p in _BLOCKED_PREFIXES
    ):
        raise SSRFError(f"Blocked internal/private address: {hostname!r}")

    allowed_domains: list[str] = getattr(settings, "ALLOWED_EXTERNAL_DOMAINS", [])
    if not any(hostname == d or hostname.endswith(f".{d}") for d in allowed_domains):
        logger.warning(
            "SSRF blocked: domain not in allowlist",
            extra={"url": url, "hostname": hostname},
        )
        raise SSRFError(
            f"Domain {hostname!r} is not in the allowed external domains list"
        )

    return url
