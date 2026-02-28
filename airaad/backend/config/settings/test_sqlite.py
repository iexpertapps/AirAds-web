"""
AirAd Backend — Test Settings (SQLite for local testing)
CELERY_TASK_ALWAYS_EAGER=True, fast hashing, dummy AWS vars, in-memory cache.
"""

from .base import env  # noqa: F811 — explicit import to satisfy flake8 F405

# ---------------------------------------------------------------------------
# Security — test secret key
# ---------------------------------------------------------------------------
SECRET_KEY = 'django-insecure-test-key-for-unit-tests-only-not-for-production'

# ---------------------------------------------------------------------------
# Encryption — test encryption key for development/testing
# ---------------------------------------------------------------------------
ENCRYPTION_KEY = 'test-encryption-key-32-chars-long!'

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
# URL Configuration
# ---------------------------------------------------------------------------
ROOT_URLCONF = 'config.urls'

# ---------------------------------------------------------------------------
# Disable PostGIS/GIS for SQLite tests
# ---------------------------------------------------------------------------
# Remove GIS apps that require PostGIS
INSTALLED_APPS = [
    app for app in [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'rest_framework',
        'rest_framework_simplejwt',
        'corsheaders',
        'django_filters',
        'core',
        'apps.accounts',
        'apps.customer_auth',
        'apps.user_preferences',
        'apps.user_portal',
        'apps.audit',
    ]
    if app not in ['django.contrib.gis', 'django.contrib.gis.db.backends.postgis']
]

# ---------------------------------------------------------------------------
# Remove analytics app that has foreign key dependencies
# ---------------------------------------------------------------------------
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'apps.analytics']

# ---------------------------------------------------------------------------
# Add missing Django settings for admin
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ---------------------------------------------------------------------------
# Remove PostGIS spatial database for SQLite
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",  # In-memory SQLite for fast tests
        "TEST": {
            "NAME": ":memory:",
        },
    }
}

# ---------------------------------------------------------------------------
# Media files — temp directory for tests
# ---------------------------------------------------------------------------
MEDIA_ROOT = "/tmp/airaad_test_media"
STATIC_ROOT = "/tmp/airaad_test_static"
