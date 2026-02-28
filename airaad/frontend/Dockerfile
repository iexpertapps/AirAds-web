# =============================================================================
# AirAd Frontend — Multi-Stage Dockerfile
# =============================================================================
# Stage 1 (builder): Installs deps and builds production bundle
# Stage 2 (production): Serves static files via nginx:alpine
#
# Used by docker-compose.yml for local production-like setup.
# On DigitalOcean App Platform, the frontend is deployed as a static site
# (no Docker needed — DO builds via npm and serves from CDN).
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1 — Builder
# -----------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first for layer caching
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build production bundle
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_APP_ENV=production
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_APP_ENV=${VITE_APP_ENV}

RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2 — Production (nginx serving static files)
# -----------------------------------------------------------------------------
FROM nginx:1.25-alpine AS production

# Copy custom nginx config for SPA routing
COPY --from=builder /app/dist /usr/share/nginx/html

# SPA fallback: all routes serve index.html
RUN printf 'server {\n\
    listen 80;\n\
    server_name _;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
\n\
    # Gzip compression\n\
    gzip on;\n\
    gzip_vary on;\n\
    gzip_proxied any;\n\
    gzip_comp_level 6;\n\
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss image/svg+xml;\n\
\n\
    # Cache static assets aggressively\n\
    location /assets/ {\n\
        expires 1y;\n\
        add_header Cache-Control "public, immutable";\n\
    }\n\
\n\
    # SPA fallback — serve index.html for all routes\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
\n\
    # Health check\n\
    location /health {\n\
        access_log off;\n\
        return 200 "healthy\\n";\n\
        add_header Content-Type text/plain;\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
