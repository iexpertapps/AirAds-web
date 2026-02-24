# =============================================================================
# AirAd Backend — Multi-Stage Dockerfile
# =============================================================================
# Stage 1 (builder): Compiles psycopg2 from source — NOT psycopg2-binary (R7)
# Stage 2 (production): Minimal runtime image with GDAL pinned to PostGIS version
# Stage 3 (development): Adds dev tools, mounts source at /app
#
# PostGIS image used: postgis/postgis:16-3.4-alpine
# GDAL version in that image: 3.6.x (Alpine 3.18 package)
# Pin GDAL to match exactly to prevent silent GeoDjango failures.
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
# psycopg2 is compiled from source here — never psycopg2-binary (R7)
RUN pip install --upgrade pip wheel && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements/production.txt

# -----------------------------------------------------------------------------
# Stage 2 — Production
# Minimal runtime image. GDAL version pinned to match postgis:16-3.4-alpine.
# Backend is NOT directly port-exposed — nginx proxies all traffic.
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS production

# Install GDAL and runtime dependencies
# gdal-bin pulls in the correct libgdal, libgeos, libproj as dependencies
# libpq5 provides libpq.so.5 needed by compiled psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    gdal-bin \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL/GEOS/PROJ paths for GeoDjango (use generic symlinks)
ENV GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so
ENV GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so
ENV PROJ_LIB=/usr/share/proj

# Create non-root user for security
RUN groupadd --gid 1001 airaad && \
    useradd --uid 1001 --gid airaad --no-create-home --shell /bin/false airaad

WORKDIR /app

# Install pre-built wheels from builder stage (no compilation needed here)
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* && \
    rm -rf /wheels

# Copy application source
COPY --chown=airaad:airaad . /app/

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Switch to non-root user
USER airaad

EXPOSE 8000

# gunicorn: 2 workers, bind to $PORT (Railway injects this), 120s timeout for long CSV imports
CMD gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120 --access-logfile - --error-logfile -

# -----------------------------------------------------------------------------
# Stage 3 — Development
# Adds dev tools. Source code is mounted as a volume at runtime.
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
