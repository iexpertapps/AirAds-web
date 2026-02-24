"""
AirAd Backend — Staging Settings
Mirrors production exactly: DEBUG=False, strict security, structured JSON logging.
Uses its own DATABASE_URL and REDIS_URL — completely separate from production.
"""

from .base import *  # noqa: F401, F403
from .base import AWS_S3_REGION_NAME, AWS_STORAGE_BUCKET_NAME, env

# ---------------------------------------------------------------------------
# Security — identical to production
# ---------------------------------------------------------------------------
DEBUG = False

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# Database — staging uses its own DATABASE_URL (PostGIS engine set in base)
# ---------------------------------------------------------------------------
# Inherited from base.py — ENGINE is already postgis, CONN_MAX_AGE=60

# ---------------------------------------------------------------------------
# Static & Media — S3 via django-storages (same config as production)
# ---------------------------------------------------------------------------
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "region_name": AWS_S3_REGION_NAME,
            "default_acl": None,
            "file_overwrite": False,
            "querystring_auth": True,
        },
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3StaticStorage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "region_name": AWS_S3_REGION_NAME,
            "location": "static",
            "default_acl": "public-read",
            "querystring_auth": False,
        },
    },
}

STATIC_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/static/"

# ---------------------------------------------------------------------------
# Logging — structured JSON, same as production
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": (
                '{"time": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "message": "%(message)s"}'
            ),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "core": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "security.alerts": {
            "handlers": ["console"],
            "level": "CRITICAL",
            "propagate": False,
        },
    },
}
