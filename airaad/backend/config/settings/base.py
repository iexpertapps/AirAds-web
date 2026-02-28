"""
AirAd Backend — Base Settings
Shared across all environments. Never import directly; use environment-specific modules.
"""

from datetime import timedelta
from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# AES-256-GCM encryption key — 32 bytes, base64-encoded (R2)
ENCRYPTION_KEY: str = env("ENCRYPTION_KEY")

# Number of trusted reverse proxies in front of the app (used by get_client_ip).
# Set to 0 to use REMOTE_ADDR directly (no proxy). Default: 1 (single nginx).
NUM_PROXIES: int = env.int("NUM_PROXIES", default=1)

# CORS — allowed origins. Override in environment-specific settings.
# Production: set CORS_ALLOWED_ORIGINS via env. Development: CORS_ALLOW_ALL_ORIGINS=True.
CORS_ALLOWED_ORIGINS: list[str] = env.list("CORS_ALLOWED_ORIGINS", default=[])

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
DJANGO_APPS: list[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
]

THIRD_PARTY_APPS: list[str] = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_celery_beat",
    "storages",
    "corsheaders",
]

LOCAL_APPS: list[str] = [
    "apps.accounts",
    "apps.audit",
    "apps.geo",
    "apps.tags",
    "apps.vendors",
    "apps.imports",
    "apps.field_ops",
    "apps.qa",
    "apps.analytics",
    "apps.subscriptions",
    "apps.discovery",
    "apps.governance",
    "apps.vendor_portal",
    "apps.payments",
    "apps.reels",
    "apps.notifications",
    "apps.customer_auth",
    "apps.user_portal",
    "apps.user_preferences",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# RequestIDMiddleware MUST be index 0 — security and tracing critical.
# ---------------------------------------------------------------------------
MIDDLEWARE: list[str] = [
    "core.middleware.RequestIDMiddleware",  # index 0 — FIRST (R3 tracing)
    "django.middleware.security.SecurityMiddleware",
    "core.security_middleware.SecurityHeadersMiddleware",  # CSP, Permissions-Policy, Referrer-Policy
    "corsheaders.middleware.CorsMiddleware",  # must be before CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database — PostGIS (GeoDjango mandatory)
# CONN_MAX_AGE=60 keeps connections alive for 60 seconds (performance).
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        **env.db(
            "DATABASE_URL", default="postgis://airaad:airaad@localhost:5432/airaad_db"
        ),
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# ---------------------------------------------------------------------------
# Cache — Redis
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
    }
}

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.AdminUser"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# SimpleJWT
# ACCESS=15min, REFRESH=7days, ROTATE_REFRESH_TOKENS=True
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "apps.accounts.serializers.CustomTokenObtainPairSerializer",
}

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "300/minute",
        "login": "10/minute",
    },
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardResultsPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
}

# ---------------------------------------------------------------------------
# drf-spectacular (OpenAPI)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "AirAd API",
    "DESCRIPTION": "Hyperlocal vendor discovery platform — Nearby + Now",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v1/",
}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL: str = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND: str = env(
    "CELERY_RESULT_BACKEND", default="redis://localhost:6379/0"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes soft limit

# ---------------------------------------------------------------------------
# AWS S3 Storage
# ---------------------------------------------------------------------------
AWS_ACCESS_KEY_ID: str = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY: str = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME: str = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME: str = env("AWS_S3_REGION_NAME", default="us-east-1")
AWS_S3_PRESIGNED_URL_EXPIRY: int = env.int("AWS_S3_PRESIGNED_URL_EXPIRY", default=3600)
AWS_DEFAULT_ACL = None  # Never public — presigned URLs only
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = True  # Presigned URLs

# ---------------------------------------------------------------------------
# Google Places API
# ---------------------------------------------------------------------------
GOOGLE_PLACES_API_KEY = env("GOOGLE_PLACES_API_KEY", default="")

# ---------------------------------------------------------------------------
# Stripe — Subscription Payments (Phase C §8)
# ---------------------------------------------------------------------------
STRIPE_SECRET_KEY: str = env("STRIPE_SECRET_KEY", default="")
STRIPE_PUBLISHABLE_KEY: str = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_WEBHOOK_SECRET: str = env("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_PRICE_GOLD: str = env("STRIPE_PRICE_GOLD", default="")
STRIPE_PRICE_DIAMOND: str = env("STRIPE_PRICE_DIAMOND", default="")
STRIPE_PRICE_PLATINUM: str = env("STRIPE_PRICE_PLATINUM", default="")
STRIPE_SILVER_PRICE_ID: str = env("STRIPE_SILVER_PRICE_ID", default="")

# ---------------------------------------------------------------------------
# Twilio SMS (Phase B — core/sms.py)
# ---------------------------------------------------------------------------
TWILIO_ACCOUNT_SID: str = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN: str = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_PHONE_NUMBER: str = env("TWILIO_PHONE_NUMBER", default="")

# ---------------------------------------------------------------------------
# Firebase Cloud Messaging (Phase B — notifications)
# ---------------------------------------------------------------------------
FIREBASE_CREDENTIALS_JSON: str = env("FIREBASE_CREDENTIALS_JSON", default="")

# ---------------------------------------------------------------------------
# Sentry error tracking
# ---------------------------------------------------------------------------
SENTRY_DSN: str = env("SENTRY_DSN", default="")

# ---------------------------------------------------------------------------
# OTP Manual Mode (Temporary — until Twilio is integrated)
# When set, _generate_otp() returns this fixed code instead of a random one,
# and SMS sending is skipped (logged only). Set to empty string "" to disable.
# To enable Twilio: remove this setting (or set to ""), configure TWILIO_*
# env vars, and the OTP system will automatically use real SMS delivery.
# ---------------------------------------------------------------------------
MANUAL_OTP_CODE: str = env("MANUAL_OTP_CODE", default="005261")

# ---------------------------------------------------------------------------
# JWT token lifetimes
# ---------------------------------------------------------------------------
JWT_ACCESS_LIFETIME_MINUTES: int = env.int("JWT_ACCESS_LIFETIME_MINUTES", default=60)
JWT_REFRESH_LIFETIME_DAYS: int = env.int("JWT_REFRESH_LIFETIME_DAYS", default=7)

# ---------------------------------------------------------------------------
# Session security — idle timeout after 30 minutes
# ---------------------------------------------------------------------------
SESSION_COOKIE_AGE = 1800  # 30 minutes idle timeout
SESSION_SAVE_EVERY_REQUEST = True  # Reset timeout on each request
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# ---------------------------------------------------------------------------
# Security — Referrer-Policy
# ---------------------------------------------------------------------------
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# ---------------------------------------------------------------------------
# File upload limits — 10 MB max per file
# ---------------------------------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

# ---------------------------------------------------------------------------
# SSRF protection — allowed external domains for outbound requests
# ---------------------------------------------------------------------------
ALLOWED_EXTERNAL_DOMAINS: list[str] = [
    "maps.googleapis.com",
    "places.googleapis.com",
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & Media
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
        },
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "core": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
