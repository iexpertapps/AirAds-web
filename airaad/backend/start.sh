#!/bin/bash
# =============================================================================
# AirAd Backend — Container Startup Script
# =============================================================================
# Execution order:
#   1. Wait for database to be ready
#   2. Run database migrations
#   3. Collect static files (if not using S3, or S3 configured)
#   4. Start gunicorn bound to 0.0.0.0:$PORT
#
# This script is the container entrypoint for production.
# DigitalOcean App Platform injects $PORT at runtime.
# =============================================================================

set -e

echo "============================================"
echo "  AirAd Backend — Starting"
echo "============================================"
echo "  DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-not set}"
echo "  PORT=${PORT:-8000}"
echo "  ALLOWED_HOSTS=${ALLOWED_HOSTS:-not set}"
echo "============================================"

# ---------------------------------------------------------------------------
# Step 1: Wait for database to be ready (max 60 seconds)
# ---------------------------------------------------------------------------
echo ""
echo "[1/4] Waiting for database..."

python << 'PYEOF'
import sys
import time
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

for attempt in range(1, 31):
    try:
        import django
        django.setup()
        from django.db import connection
        connection.ensure_connection()
        print(f"  Database ready (attempt {attempt})")
        sys.exit(0)
    except Exception as e:
        print(f"  Attempt {attempt}/30: {e}")
        time.sleep(2)

print("  ERROR: Database not available after 60 seconds")
sys.exit(1)
PYEOF

# ---------------------------------------------------------------------------
# Step 2: Run database migrations
# ---------------------------------------------------------------------------
echo ""
echo "[2/4] Running database migrations..."
python manage.py migrate --noinput
echo "  Migrations complete"

# ---------------------------------------------------------------------------
# Step 3: Collect static files
# ---------------------------------------------------------------------------
echo ""
echo "[3/4] Collecting static files..."
python manage.py collectstatic --noinput 2>&1 || echo "  collectstatic skipped (S3 not configured or not needed)"

# ---------------------------------------------------------------------------
# Step 4: Start Gunicorn
# ---------------------------------------------------------------------------
echo ""
echo "[4/4] Starting Gunicorn on 0.0.0.0:${PORT:-8000}..."
echo "============================================"

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
