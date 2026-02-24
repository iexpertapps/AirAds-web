"""
AirAd Backend — Test Settings
CELERY_TASK_ALWAYS_EAGER=True, fast hashing, dummy AWS vars, in-memory cache.
"""

from .development import *  # noqa: F401, F403
from .base import env  # noqa: F811 — explicit import to satisfy flake8 F405

# ---------------------------------------------------------------------------
# Celery — run tasks synchronously in tests (no broker needed)
# ---------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ---------------------------------------------------------------------------
# Testing flag — allows weak dev encryption key in core/encryption.py
# ---------------------------------------------------------------------------
TESTING = True

# ---------------------------------------------------------------------------
# Database — test database (Django creates/destroys automatically)
# ENGINE inherited (postgis), CONN_MAX_AGE inherited
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": env("POSTGRES_DB", default="test_airaad_db"),
        "USER": env("POSTGRES_USER", default="airaad"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="airaad"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "CONN_MAX_AGE": 0,  # No persistent connections in tests
        "TEST": {
            "NAME": env("POSTGRES_DB", default="test_airaad_db"),
        },
    }
}

# ---------------------------------------------------------------------------
# Cache — dummy cache in tests (no Redis needed)
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# ---------------------------------------------------------------------------
# Password hashing — MD5 for speed in tests only
# ---------------------------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ---------------------------------------------------------------------------
# AWS — dummy values for tests (moto intercepts all boto3 calls)
# ---------------------------------------------------------------------------
AWS_ACCESS_KEY_ID = "test-access-key"
AWS_SECRET_ACCESS_KEY = "test-secret-key"
AWS_STORAGE_BUCKET_NAME = "test-airaad-bucket"
AWS_S3_REGION_NAME = "us-east-1"

# ---------------------------------------------------------------------------
# Encryption — deterministic test key (32 bytes, base64-encoded)
# Generated: python -c "import base64; print(base64.b64encode(b'a'*32).decode())"
# ---------------------------------------------------------------------------
ENCRYPTION_KEY = "dGVzdGtleV9haXJhYWRfMzJieXRlc19wYWRkaW5nISE="

# ---------------------------------------------------------------------------
# Email — suppress all emails in tests
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ---------------------------------------------------------------------------
# Logging — minimal in tests
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
    },
}
