# =============================================================================
# AirAd Backend — Multi-Stage Dockerfile
# =============================================================================
# Stage 1 (builder):     Compiles psycopg2 from source — NOT psycopg2-binary
# Stage 2 (development): Dev tools, source mounted at runtime
# Stage 3 (production):  LAST stage = default build target for Railway/Docker
#
# IMPORTANT: production MUST be the last stage so that Railway, which builds
# the default (last) stage, always gets the production image with gunicorn.
# Local dev uses: docker build --target development
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1 — Builder
# Compiles Python packages that require C extensions (psycopg2, cryptography).
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install build dependencies for psycopg2 (compiled, not binary) and cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only requirements first for layer caching
COPY requirements/ requirements/

# Build wheels for production dependencies
# psycopg2 is compiled from source here — never psycopg2-binary
RUN pip install --upgrade pip wheel && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements/production.txt

# -----------------------------------------------------------------------------
# Stage 2 — Development (NOT the default target)
# Adds dev tools. Source code is mounted as a volume at runtime.
# Use: docker build --target development
# Use: docker-compose -f docker-compose.dev.yml up
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS development

# Install GDAL + build tools (psycopg2-binary acceptable in dev — see development.txt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libgdal-dev \
    gdal-bin \
    libgeos-dev \
    libproj-dev \
    build-essential \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so
ENV GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so
ENV PROJ_LIB=/usr/share/proj

WORKDIR /app

COPY requirements/ requirements/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements/test.txt

# Source code is mounted via docker-compose.dev.yml volume — not copied here

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# -----------------------------------------------------------------------------
# Stage 3 — Production (DEFAULT — last stage, built by Railway automatically)
# Minimal runtime image with gunicorn, GDAL, and compiled wheels.
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS production

# Install GDAL and runtime dependencies
# gdal-bin pulls in the correct libgdal, libgeos, libproj as dependencies
# libpq5 provides libpq.so.5 needed by compiled psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    gdal-bin \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL/GEOS/PROJ paths for GeoDjango
ENV GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so
ENV GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so
ENV PROJ_LIB=/usr/share/proj

# Set Django settings for collectstatic and runtime
ENV DJANGO_SETTINGS_MODULE=config.settings.production

# Create non-root user for security
RUN groupadd --gid 1001 airaad && \
    useradd --uid 1001 --gid airaad --no-create-home --shell /bin/false airaad

WORKDIR /app

# Install pre-built wheels from builder stage (includes gunicorn + all deps)
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* && \
    rm -rf /wheels

# Copy application source AFTER installing dependencies (layer caching)
COPY --chown=airaad:airaad . /app/

# Collect static files (fails gracefully if env vars like SECRET_KEY not set at build time)
RUN python manage.py collectstatic --noinput || true

# Switch to non-root user
USER airaad

EXPOSE 8000

# gunicorn: 2 workers, bind to $PORT (Railway injects this), 120s timeout for long CSV imports
# Shell form required for $PORT variable expansion at runtime
CMD gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120 --access-logfile - --error-logfile -
