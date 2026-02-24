# AirAd — Deployment Guide

Complete deployment pipeline documentation covering three environments
across Railway (backend) and Vercel (frontend).

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Git Branch Structure](#git-branch-structure)
3. [Branch Protection Rules](#branch-protection-rules)
4. [Railway — Backend Deployment](#railway--backend-deployment)
5. [Vercel — Frontend Deployment](#vercel--frontend-deployment)
6. [GitHub Actions CI/CD Pipeline](#github-actions-cicd-pipeline)
7. [GitHub Secrets Reference](#github-secrets-reference)
8. [Environment Variables — Complete Reference](#environment-variables--complete-reference)
9. [First-Time Setup Checklist](#first-time-setup-checklist)
10. [Verification Guide](#verification-guide)
11. [Rollback Procedures](#rollback-procedures)

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────────────┐
                    │               GitHub Repository                 │
                    │                                                 │
                    │  develop ──► staging ──► main                   │
                    │     │           │          │                    │
                    └─────┼───────────┼──────────┼────────────────────┘
                          │           │          │
                    ┌─────▼─────┐ ┌──▼────┐ ┌──▼──────┐
                    │  CI Tests │ │  CI   │ │  CI     │
                    │  + Lint   │ │ Tests │ │  Tests  │
                    │  + Build  │ │ +Lint │ │  +Lint  │
                    └─────┬─────┘ └──┬────┘ └──┬──────┘
                          │          │          │
              ┌───────────┼──────────┼──────────┼───────────────┐
              │           │          │          │               │
         ┌────▼────┐ ┌───▼────┐ ┌──▼────┐ ┌──▼──────┐       │
         │ Railway │ │Railway │ │Railway│ │ Railway │       │
         │  DEV    │ │STAGING │ │ PROD  │ │  PROD   │       │
         │Backend  │ │Backend │ │Backend│ │ Celery  │       │
         └─────────┘ └────────┘ └───────┘ └─────────┘       │
              │           │          │                        │
         ┌────▼────┐ ┌───▼────┐ ┌──▼──────┐                │
         │ Vercel  │ │ Vercel │ │ Vercel  │                 │
         │  DEV    │ │STAGING │ │  PROD   │                 │
         │Frontend │ │Frontend│ │Frontend │                 │
         └─────────┘ └────────┘ └─────────┘                 │
              │           │          │                        │
              ▼           ▼          ▼                        │
          DEV URL    STAGING URL  PROD URL                   │
              └───────────┼──────────┘                        │
                          │                                   │
                   All environments                           │
                   are completely                             │
                   independent                                │
              └───────────────────────────────────────────────┘
```

### Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | React 18 + Vite + TypeScript |
| **Backend** | Django 5.x + DRF + Celery |
| **Database** | PostgreSQL 16 + PostGIS |
| **Cache/Queue** | Redis 7 |
| **Backend Hosting** | Railway |
| **Frontend Hosting** | Vercel |
| **CI/CD** | GitHub Actions |
| **Containers** | Docker (multi-stage) |

---

## Git Branch Structure

| Branch | Environment | Auto-Deploy Target |
|--------|------------|-------------------|
| `develop` | Development | Railway DEV + Vercel DEV |
| `staging` | Staging | Railway STAGING + Vercel STAGING |
| `main` | Production | Railway PROD + Vercel PROD |

### Flow

```
feature/* ──PR──► develop ──PR──► staging ──PR──► main
                     │               │              │
                  DEV deploy    STAGING deploy   PROD deploy
```

### Rules

- **Feature branches** merge to `develop` via PR
- **`develop`** merges to `staging` via reviewed PR
- **`staging`** merges to `main` via reviewed and tested PR
- **Hotfixes** branch from `main`, merge to both `main` and `develop`
- **Never** force-push to `staging` or `main`
- **Never** push directly to `staging` or `main`

---

## Branch Protection Rules

Configure these in **GitHub → Settings → Branches → Branch protection rules**:

### `main` (Production)

| Setting | Value |
|---------|-------|
| Require a pull request before merging | ✅ |
| Required approving reviews | 1 (minimum) |
| Dismiss stale PR reviews when new commits are pushed | ✅ |
| Require status checks to pass before merging | ✅ |
| Required status checks | `Test Suite`, `Frontend Build`, `Backend Docker Build` |
| Require branches to be up to date before merging | ✅ |
| Restrict who can push to matching branches | ✅ (admin only) |
| Do not allow force pushes | ✅ |
| Do not allow deletions | ✅ |

### `staging`

| Setting | Value |
|---------|-------|
| Require a pull request before merging | ✅ |
| Required approving reviews | 1 (minimum) |
| Require status checks to pass before merging | ✅ |
| Required status checks | `Test Suite`, `Frontend Build` |
| Do not allow force pushes | ✅ |
| Do not allow deletions | ✅ |

### `develop`

| Setting | Value |
|---------|-------|
| Require status checks to pass before merging | ✅ |
| Required status checks | `Test Suite`, `Frontend Build` |
| Do not allow force pushes | ✅ |

---

## Railway — Backend Deployment

### Three Separate Railway Projects

| Environment | Railway Project Name | Django Settings |
|------------|---------------------|-----------------|
| Development | `airaad-dev` | `config.settings.development` |
| Staging | `airaad-staging` | `config.settings.staging` |
| Production | `airaad-prod` | `config.settings.production` |

### Services Per Project

Each Railway project must contain:

```
Railway Project: airaad-{env}
├── Service: backend      (Django + Gunicorn)
├── Service: celery       (Celery worker)
├── Plugin: PostgreSQL    (with PostGIS extension)
└── Plugin: Redis
```

### Setup Steps (Per Environment)

#### 1. Create Railway Project

```bash
# Install Railway CLI
npm i -g @railway/cli
railway login

# Create project (repeat for dev, staging, prod)
railway init --name airaad-dev
```

#### 2. Add PostgreSQL Plugin

- Railway Dashboard → Project → **+ New** → **Database** → **PostgreSQL**
- After provisioning, enable PostGIS:

```bash
railway run --service <postgres-service> psql
# Then in psql:
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
```

#### 3. Add Redis Plugin

- Railway Dashboard → Project → **+ New** → **Database** → **Redis**

#### 4. Create Backend Service

- Railway Dashboard → **+ New** → **Service** → Connect GitHub repo
- Root directory: `airaad/backend`
- Watch path: `airaad/backend/**`

#### 5. Create Celery Worker Service

- Railway Dashboard → **+ New** → **Service** → Connect GitHub repo
- Root directory: `airaad/backend`
- Start command: `celery -A celery_app worker --loglevel=info --concurrency=2`

#### 6. Set Environment Variables

See [Environment Variables](#environment-variables--complete-reference) section.

### Railway Backend Environment Variables

| Variable | Dev | Staging | Prod | Source |
|----------|-----|---------|------|--------|
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` | `config.settings.staging` | `config.settings.production` | Manual |
| `SECRET_KEY` | Generate unique | Generate unique | Generate unique | Manual |
| `ENCRYPTION_KEY` | Generate unique | Generate unique | Generate unique | Manual |
| `DATABASE_URL` | Auto-injected | Auto-injected | Auto-injected | PostgreSQL plugin |
| `REDIS_URL` | Auto-injected | Auto-injected | Auto-injected | Redis plugin |
| `ALLOWED_HOSTS` | `airaad-dev-backend.up.railway.app` | `airaad-staging-backend.up.railway.app` | `airaad-backend.up.railway.app` | Manual |
| `CORS_ALLOWED_ORIGINS` | `https://airaad-dev.vercel.app` | `https://airaad-staging.vercel.app` | `https://airaad.vercel.app` | Manual |
| `FRONTEND_URL` | `https://airaad-dev.vercel.app` | `https://airaad-staging.vercel.app` | `https://airaad.vercel.app` | Manual |
| `DEBUG` | `True` | `False` | `False` | Manual |
| `AWS_ACCESS_KEY_ID` | Dev key | Staging key | Prod key | Manual |
| `AWS_SECRET_ACCESS_KEY` | Dev secret | Staging secret | Prod secret | Manual |
| `AWS_STORAGE_BUCKET_NAME` | `airaad-dev` | `airaad-staging` | `airaad-prod` | Manual |
| `AWS_S3_REGION_NAME` | `us-east-1` | `us-east-1` | `us-east-1` | Manual |
| `CELERY_BROKER_URL` | `${{Redis.REDIS_URL}}` | `${{Redis.REDIS_URL}}` | `${{Redis.REDIS_URL}}` | Redis plugin ref |
| `CELERY_RESULT_BACKEND` | `${{Redis.REDIS_URL}}` | `${{Redis.REDIS_URL}}` | `${{Redis.REDIS_URL}}` | Redis plugin ref |
| `PORT` | Auto-injected | Auto-injected | Auto-injected | Railway |

### Generate Secrets

```bash
# Django SECRET_KEY (run once per environment)
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# AES-256-GCM ENCRYPTION_KEY (32 bytes, base64-encoded)
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

---

## Vercel — Frontend Deployment

### Three Environments

| Environment | Vercel Project | Connected Branch | Backend URL |
|------------|---------------|-----------------|-------------|
| Development | `airaad-dev` | `develop` | `https://airaad-dev-backend.up.railway.app` |
| Staging | `airaad-staging` | `staging` | `https://airaad-staging-backend.up.railway.app` |
| Production | `airaad` | `main` | `https://airaad-backend.up.railway.app` |

### Setup Steps

#### 1. Install Vercel CLI

```bash
npm i -g vercel
vercel login
```

#### 2. Create Vercel Projects

For each environment, either:
- **Dashboard**: Import GitHub repo → Set root directory to `airaad/frontend`
- **CLI**: `cd airaad/frontend && vercel`

#### 3. Configure Build Settings (Per Project)

| Setting | Value |
|---------|-------|
| Framework Preset | Other (Vite) |
| Root Directory | `airaad/frontend` |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Install Command | `npm ci` |

#### 4. Set Environment Variables (Per Project)

| Variable | Dev | Staging | Prod |
|----------|-----|---------|------|
| `VITE_API_BASE_URL` | `https://airaad-dev-backend.up.railway.app` | `https://airaad-staging-backend.up.railway.app` | `https://airaad-backend.up.railway.app` |
| `VITE_APP_ENV` | `development` | `staging` | `production` |

> **CRITICAL**: Never put API secrets in Vercel env vars — `VITE_` prefixed vars are bundled into the public JS bundle.

### `vercel.json`

Already configured at `airaad/frontend/vercel.json` with:
- SPA rewrite for client-side routing
- Immutable cache headers on `/assets/` (Vite hashed filenames)
- Security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy)

---

## GitHub Actions CI/CD Pipeline

### Workflow Files

| File | Trigger | Purpose |
|------|---------|--------|
| `ci.yml` | Push to any branch + PRs | All CI checks (lint, test, security, build, E2E) |
| `deploy-development.yml` | `ci.yml` passes on `develop` | Auto-deploy to dev + health check |
| `deploy-staging.yml` | `ci.yml` passes on `staging` | Deploy to staging + smoke tests |
| `deploy-production.yml` | `ci.yml` passes on `main` | Deploy to prod + rollback safety |

### CI Pipeline Architecture (ci.yml)

```
┌─── LAYER 1: Parallel fast checks (no DB) ───────────────────────┐
│  backend-lint    frontend-lint    backend-security               │
│  frontend-security               secret-scan (ALL pushes)       │
└──────────┬──────────┬────────────────────────────────────────────┘
           │          │
┌─── LAYER 2: DB-dependent checks (parallel) ─────────────────────┐
│  migration-check   backend-test (≥80% cov)   rbac-test          │
│                    frontend-build                                │
└──────────┬──────────┬────────────────────────────────────────────┘
           │          │
┌─── LAYER 3: Integration & E2E ──────────────────────────────────┐
│  backend-docker (Buildx cached)   backend-e2e   frontend-e2e    │
└──────────┬──────────┬────────────────────────────────────────────┘
           │          │
┌─── LAYER 4: PR-only gates ──────────────────────────────────────┐
│  semgrep → ai-review    quality-gate                            │
└─────────────────────────────────────────────────────────────────┘
```

### Deploy Pipelines (triggered via `workflow_run`)

```
┌─── Development (deploy-development.yml) ────────────────────────┐
│  CI passes on develop →                                         │
│    deploy-backend → deploy-celery (sequential)                  │
│    deploy-frontend (parallel with backend)                      │
│    health-check → notify                                        │
└─────────────────────────────────────────────────────────────────┘

┌─── Staging (deploy-staging.yml) ────────────────────────────────┐
│  CI passes on staging →                                         │
│    deploy-backend → deploy-celery                               │
│    deploy-frontend                                              │
│    smoke-test (DEBUG off, auth enforced, security headers)      │
│    notify                                                       │
└─────────────────────────────────────────────────────────────────┘

┌─── Production (deploy-production.yml) ──────────────────────────┐
│  CI passes on main →                                            │
│    create git tag (rollback save point)                         │
│    deploy-backend → deploy-celery                               │
│    deploy-frontend                                              │
│    verify (health + DEBUG + auth + HTTPS + security headers)    │
│    auto-rollback (if verify fails)                              │
│    notify (ALWAYS — success, failure, or rollback)              │
└─────────────────────────────────────────────────────────────────┘
```

### Migration Safety

Migrations run as a **separate step AFTER deploy** completes:

```yaml
# 1. Deploy new code
- run: railway up --service $SERVICE_ID --detach

# 2. Wait for health check
- run: sleep 30

# 3. Run migrations (separate step)
- run: railway run --service $SERVICE_ID python manage.py migrate --noinput
```

---

## GitHub Secrets Reference

Configure all secrets in **GitHub → Settings → Secrets and variables → Actions**.

### Railway Secrets (Per Environment)

| Secret Name | Description |
|-------------|-------------|
| `RAILWAY_DEV_TOKEN` | Railway API token for development project |
| `RAILWAY_DEV_SERVICE_ID_BACKEND` | Railway service ID for dev backend |
| `RAILWAY_DEV_SERVICE_ID_CELERY` | Railway service ID for dev Celery worker |
| `RAILWAY_DEV_BACKEND_URL` | Full URL of dev backend (e.g., `https://airaad-dev-backend.up.railway.app`) |
| `RAILWAY_STAGING_TOKEN` | Railway API token for staging project |
| `RAILWAY_STAGING_SERVICE_ID_BACKEND` | Railway service ID for staging backend |
| `RAILWAY_STAGING_SERVICE_ID_CELERY` | Railway service ID for staging Celery worker |
| `RAILWAY_STAGING_BACKEND_URL` | Full URL of staging backend |
| `RAILWAY_PROD_TOKEN` | Railway API token for production project |
| `RAILWAY_PROD_SERVICE_ID_BACKEND` | Railway service ID for prod backend |
| `RAILWAY_PROD_SERVICE_ID_CELERY` | Railway service ID for prod Celery worker |
| `RAILWAY_PROD_BACKEND_URL` | Full URL of prod backend |

### Vercel Secrets

| Secret Name | Description |
|-------------|-------------|
| `VERCEL_TOKEN` | Vercel API token (one token works for all projects) |
| `VERCEL_ORG_ID` | Vercel organization/team ID |
| `VERCEL_DEV_PROJECT_ID` | Vercel project ID for development |
| `VERCEL_STAGING_PROJECT_ID` | Vercel project ID for staging |
| `VERCEL_PROD_PROJECT_ID` | Vercel project ID for production |
| `VERCEL_DEV_URL` | Full URL of dev frontend |
| `VERCEL_STAGING_URL` | Full URL of staging frontend |
| `VERCEL_PROD_URL` | Full URL of prod frontend |

### Notification Secrets

| Secret Name | Description |
|-------------|-------------|
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL for deploy notifications (optional but recommended) |

### Other Secrets

| Secret Name | Description |
|-------------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key for AI code review (optional) |

> `GITHUB_TOKEN` is automatically provided by GitHub Actions — do not add manually.

### How to Get Railway Service IDs and Tokens

```bash
# Login to Railway
railway login

# List projects
railway list

# Link to a project
railway link

# Get service IDs — visible in Railway Dashboard URL:
# https://railway.app/project/{PROJECT_ID}/service/{SERVICE_ID}
# Or via CLI:
railway service list

# Generate API token:
# Railway Dashboard → Account Settings → Tokens → Create Token
```

### How to Get Vercel IDs and Tokens

```bash
# Login to Vercel
vercel login

# Link to project (creates .vercel/project.json with orgId and projectId)
vercel link

# Token: Vercel Dashboard → Settings → Tokens → Create
```

---

## Environment Variables — Complete Reference

### Development Environment

**Railway (Backend)**:
```
DJANGO_SETTINGS_MODULE=config.settings.development
SECRET_KEY=<unique-dev-key>
ENCRYPTION_KEY=<unique-dev-key>
DEBUG=True
ALLOWED_HOSTS=airaad-dev-backend.up.railway.app
CORS_ALLOWED_ORIGINS=https://airaad-dev.vercel.app
FRONTEND_URL=https://airaad-dev.vercel.app
DATABASE_URL=<auto-injected-by-railway>
REDIS_URL=<auto-injected-by-railway>
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}
AWS_ACCESS_KEY_ID=<dev-aws-key>
AWS_SECRET_ACCESS_KEY=<dev-aws-secret>
AWS_STORAGE_BUCKET_NAME=airaad-dev
AWS_S3_REGION_NAME=us-east-1
```

**Vercel (Frontend)**:
```
VITE_API_BASE_URL=https://airaad-dev-backend.up.railway.app
VITE_APP_ENV=development
```

### Staging Environment

**Railway (Backend)**:
```
DJANGO_SETTINGS_MODULE=config.settings.staging
SECRET_KEY=<unique-staging-key>
ENCRYPTION_KEY=<unique-staging-key>
DEBUG=False
ALLOWED_HOSTS=airaad-staging-backend.up.railway.app
CORS_ALLOWED_ORIGINS=https://airaad-staging.vercel.app
FRONTEND_URL=https://airaad-staging.vercel.app
DATABASE_URL=<auto-injected-by-railway>
REDIS_URL=<auto-injected-by-railway>
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}
AWS_ACCESS_KEY_ID=<staging-aws-key>
AWS_SECRET_ACCESS_KEY=<staging-aws-secret>
AWS_STORAGE_BUCKET_NAME=airaad-staging
AWS_S3_REGION_NAME=us-east-1
```

**Vercel (Frontend)**:
```
VITE_API_BASE_URL=https://airaad-staging-backend.up.railway.app
VITE_APP_ENV=staging
```

### Production Environment

**Railway (Backend)**:
```
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<unique-prod-key>
ENCRYPTION_KEY=<unique-prod-key>
DEBUG=False
ALLOWED_HOSTS=airaad-backend.up.railway.app
CORS_ALLOWED_ORIGINS=https://airaad.vercel.app
FRONTEND_URL=https://airaad.vercel.app
DATABASE_URL=<auto-injected-by-railway>
REDIS_URL=<auto-injected-by-railway>
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}
AWS_ACCESS_KEY_ID=<prod-aws-key>
AWS_SECRET_ACCESS_KEY=<prod-aws-secret>
AWS_STORAGE_BUCKET_NAME=airaad-prod
AWS_S3_REGION_NAME=us-east-1
SECURE_SSL_REDIRECT=True
```

**Vercel (Frontend)**:
```
VITE_API_BASE_URL=https://airaad-backend.up.railway.app
VITE_APP_ENV=production
```

---

## First-Time Setup Checklist

### Prerequisites

- [ ] GitHub repository access with admin permissions
- [ ] Railway account with billing enabled
- [ ] Vercel account
- [ ] AWS account with S3 buckets created (3 separate buckets)

### Step-by-Step

#### 1. Git Branches

- [ ] `develop` branch exists
- [ ] `staging` branch exists
- [ ] `main` branch exists
- [ ] Branch protection rules configured (see [Branch Protection Rules](#branch-protection-rules))

#### 2. Railway Setup (Repeat for Each Environment)

- [ ] Create Railway project: `airaad-dev`
- [ ] Add PostgreSQL plugin → enable PostGIS extension
- [ ] Add Redis plugin
- [ ] Create backend service (root: `airaad/backend`)
- [ ] Create Celery worker service (root: `airaad/backend`)
- [ ] Set all environment variables
- [ ] Verify health check: `GET /api/v1/health/` returns `{"status": "ok"}`

- [ ] Create Railway project: `airaad-staging`
- [ ] (Repeat all steps above)

- [ ] Create Railway project: `airaad-prod`
- [ ] (Repeat all steps above)

#### 3. Vercel Setup (Repeat for Each Environment)

- [ ] Create Vercel project: `airaad-dev` (root: `airaad/frontend`)
- [ ] Set `VITE_API_BASE_URL` and `VITE_APP_ENV`
- [ ] Verify SPA routing works

- [ ] Create Vercel project: `airaad-staging`
- [ ] (Repeat steps above)

- [ ] Create Vercel project: `airaad`
- [ ] (Repeat steps above)

#### 4. GitHub Secrets

- [ ] Add all 12 Railway secrets (see [GitHub Secrets Reference](#github-secrets-reference))
- [ ] Add all 8 Vercel secrets
- [ ] Add `ANTHROPIC_API_KEY` (optional, for AI code review)

#### 5. First Deployment

```bash
# Push develop branch
git push origin develop

# Verify CI passes and dev deploys
# Then create PR: develop → staging
# Merge after review → staging deploys

# Then create PR: staging → main
# Merge after review → production deploys
```

---

## Verification Guide

### Quick Health Checks

```bash
# Development
curl https://airaad-dev-backend.up.railway.app/api/v1/health/
# Expected: {"status": "ok"}

# Staging
curl https://airaad-staging-backend.up.railway.app/api/v1/health/
# Expected: {"status": "ok"}

# Production
curl https://airaad-backend.up.railway.app/api/v1/health/
# Expected: {"status": "ok"}
```

### Frontend-to-Backend Connectivity

1. Open each frontend URL in a browser
2. Open browser DevTools → Network tab
3. Verify API calls go to the correct backend URL
4. Verify login/auth flow works end-to-end

### Environment Isolation Verification

1. Create a test vendor in **development** → Verify it does NOT appear in staging or production
2. Check `DJANGO_SETTINGS_MODULE` on each Railway service:
   ```bash
   # Via Railway CLI
   railway variables list --service <service-id>
   ```
3. Verify `DEBUG=False` on staging and production:
   ```bash
   curl -I https://airaad-staging-backend.up.railway.app/nonexistent/
   # Should return 404 with no debug page
   ```

### Deployment Independence

1. Push a commit to `develop` → Verify only dev environment redeploys
2. Push a commit to `staging` → Verify only staging environment redeploys
3. Push a commit to `main` → Verify only production environment redeploys

---

## Rollback Procedures

### Railway (Backend)

```bash
# View recent deployments
railway deployments list --service <service-id>

# Rollback to previous deployment
railway rollback --service <service-id> --deployment <deployment-id>
```

### Vercel (Frontend)

```bash
# View recent deployments
vercel ls

# Promote a previous deployment to production
vercel promote <deployment-url>
```

### Database Rollback

```bash
# Reverse last migration (be cautious)
railway run --service <service-id> python manage.py migrate <app_name> <previous_migration_number>
```

> **WARNING**: Always make migrations backward-compatible. Never drop columns in the same deploy that removes code using them.

---

## URL Reference

| Environment | Frontend URL | Backend URL | Backend Health |
|------------|-------------|-------------|----------------|
| Development | `https://airaad-dev.vercel.app` | `https://airaad-dev-backend.up.railway.app` | `/api/v1/health/` |
| Staging | `https://airaad-staging.vercel.app` | `https://airaad-staging-backend.up.railway.app` | `/api/v1/health/` |
| Production | `https://airaad.vercel.app` | `https://airaad-backend.up.railway.app` | `/api/v1/health/` |

> **Note**: Actual Railway URLs will be assigned when projects are created. Update this table with real URLs after setup.

---

## Security Checklist

- [ ] No `.env` files in git (verify with `git ls-files | grep .env`)
- [ ] `DEBUG=False` in staging and production
- [ ] `ALLOWED_HOSTS` set to exact Railway domain (no wildcards)
- [ ] `CORS_ALLOWED_ORIGINS` set to exact Vercel domain
- [ ] `SECURE_SSL_REDIRECT=True` in production
- [ ] `SESSION_COOKIE_SECURE=True` in staging and production
- [ ] `CSRF_COOKIE_SECURE=True` in staging and production
- [ ] Each environment has its own unique `SECRET_KEY`
- [ ] Each environment has its own unique `ENCRYPTION_KEY`
- [ ] Each environment has its own separate database
- [ ] No secrets in Vercel env vars (only `VITE_` prefixed public vars)
- [ ] `.dockerignore` excludes `.env` files
