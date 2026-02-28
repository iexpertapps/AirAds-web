# AirAd — GitLab Migration Guide

> Migrated from GitHub Actions to GitLab CI/CD on Feb 28, 2026.

---

## 1. What Was Migrated

| GitHub Actions | GitLab CI/CD |
|---|---|
| `.github/workflows/ci.yml` (687 lines) | `.gitlab-ci.yml` — stages: lint → security → test → integration → review → quality-gate |
| `.github/workflows/deploy-development.yml` | `.gitlab-ci.yml` — `deploy-dev` + `verify-dev` + `notify-dev` jobs |
| `.github/workflows/deploy-staging.yml` | `.gitlab-ci.yml` — `deploy-staging` + `verify-staging` + `notify-staging` jobs |
| `.github/workflows/deploy-production.yml` | `.gitlab-ci.yml` — `deploy-prod` + `verify-prod` + `rollback-prod` + `notify-prod` jobs |
| GitHub Environments (3) | GitLab Environments: `development`, `staging`, `production` |
| GitHub Secrets (22) | GitLab CI/CD Variables (see §3 below) |
| Railway (backend) + Vercel (frontend) | DigitalOcean App Platform (both) |
| PR templates | `.gitlab/merge_request_templates/Default.md` |

## 2. Pipeline Architecture

```
┌─────────────────────────────────────────────────────┐
│                   EVERY PUSH / MR                    │
├──────────┬──────────┬───────────┬───────────────────┤
│  LINT    │ SECURITY │           │                   │
│ backend  │ backend  │           │                   │
│ frontend │ frontend │           │                   │
│          │ secrets  │           │                   │
├──────────┴──────────┤           │                   │
│       TEST          │           │                   │
│ migrations          │           │                   │
│ backend-test (≥79%) │           │                   │
│ rbac-test           │           │                   │
│ frontend-build      │           │                   │
├─────────────────────┤           │                   │
│    INTEGRATION      │           │                   │
│ backend-docker      │           │                   │
│ backend-e2e         │           │                   │
│ frontend-e2e        │           │                   │
├─────────────────────┼───────────┤                   │
│   MR-ONLY           │  BRANCH-SPECIFIC              │
│ semgrep             │  deploy-{env} (DO App Platform) │
│ ai-review           │  verify-{env}                  │
│ quality-gate        │  rollback-prod (on_failure)     │
│                     │  notify-{env}                   │
│                     │                                 │
└─────────────────────┴───────────────────────────────┘
```

### Branch → Environment Mapping

| Branch | Environment | Deploy Trigger | Notes |
|--------|-------------|----------------|-------|
| `develop` | development | Automatic on push | Auto-deploy after CI passes |
| `staging` | staging | Automatic on push | Code reaches staging via MR from develop |
| `main` | production | **Manual** trigger | Requires clicking ▶ in pipeline UI |

### Key Differences from GitHub Actions

| Feature | GitHub Actions | GitLab CI |
|---------|---------------|-----------|
| Trigger | `workflow_run` (separate pipeline) | Single pipeline with `rules:` |
| Concurrency | `concurrency` groups | `resource_group:` |
| Services | `services:` at job level (localhost) | `services:` with alias (hostname = alias) |
| Secrets | `${{ secrets.X }}` | `$X` (CI/CD Variables) |
| Artifacts | `actions/upload-artifact` | `artifacts:` keyword |
| Caching | `actions/cache` | `cache:` keyword |
| Manual gate | Not built-in | `when: manual` |
| Auto-rollback | Separate job with `if: failure()` | `when: on_failure` |

## 3. CI/CD Variables to Configure

Go to **Settings → CI/CD → Variables** in your GitLab project.

### Required — DigitalOcean App Platform

| Variable | Description | Protected | Masked | Environment |
|----------|-------------|-----------|--------|-------------|
| `DIGITALOCEAN_ACCESS_TOKEN` | DO API token (Personal Access Token) | ✅ | ✅ | All |
| `DO_APP_ID_DEV` | App ID for development app | ✅ | ❌ | development |
| `DO_APP_ID_STAGING` | App ID for staging app | ✅ | ❌ | staging |
| `DO_APP_ID_PROD` | App ID for production app | ✅ | ❌ | production |
| `DO_APP_URL_DEV` | e.g. `https://airaad-dev-xxxxx.ondigitalocean.app` | ✅ | ❌ | development |
| `DO_APP_URL_STAGING` | e.g. `https://airaad-staging-xxxxx.ondigitalocean.app` | ✅ | ❌ | staging |
| `DO_APP_URL_PROD` | e.g. `https://airaad-xxxxx.ondigitalocean.app` | ✅ | ❌ | production |

### Optional — Notifications & AI Review

| Variable | Description | Protected | Masked |
|----------|-------------|-----------|--------|
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL | ✅ | ✅ |
| `ANTHROPIC_API_KEY` | For AI code review in MRs | ✅ | ✅ |

### Already Set in Pipeline (Non-Secret)

These are hardcoded in `.gitlab-ci.yml` as test-only values:

- `DJANGO_SETTINGS_MODULE=config.settings.test`
- `SECRET_KEY=ci-test-secret-key-not-for-production`
- `ENCRYPTION_KEY=...` (test base64 key)
- `DATABASE_URL=postgis://airaad:airaad@postgis:5432/test_airaad_db`
- `REDIS_URL=redis://redis:6379/0`
- `AWS_ACCESS_KEY_ID=test-key` / `AWS_SECRET_ACCESS_KEY=test-secret`

## 4. Setup Steps

### Step 1: Create GitLab Project

```bash
# Already done — remote added and pushed:
git remote add gitlab https://gitlab.com/iexpertapps-group/AirAds-web.git
git push gitlab --all
git push gitlab --tags
```

### Step 2: Configure Branch Protection

Go to **Settings → Repository → Protected Branches**:

| Branch | Allowed to merge | Allowed to push | Require MR |
|--------|-----------------|-----------------|------------|
| `main` | Maintainers | No one | ✅ |
| `staging` | Maintainers + Developers | No one | ✅ |
| `develop` | Maintainers + Developers | Maintainers | Optional |

### Step 3: Create Environments

Go to **Operate → Environments** → New Environment:

1. `development` — no approval required
2. `staging` — no approval required
3. `production` — enable **Required approval** (at least 1 approver)

### Step 4: Add CI/CD Variables

Go to **Settings → CI/CD → Variables** and add all variables from §3 above.

**Tips:**
- Use **Environment scope** to limit variables to specific environments
- Mark sensitive values as **Masked** so they don't appear in logs
- Mark deploy variables as **Protected** so they only work on protected branches

### Step 5: Enable GitLab CI/CD Features

Go to **Settings → CI/CD → General pipelines**:

- ✅ Auto-cancel redundant pipelines
- ✅ Enable pipeline badges
- Set coverage regex: `TOTAL.*\s+(\d+%)`

Go to **Settings → Merge requests**:

- ✅ Pipelines must succeed
- ✅ All threads must be resolved
- ✅ Require approval (1+ for main, optional for others)

### Step 6: (Optional) Disable GitHub Actions

If fully migrating away from GitHub, you can either:
- Delete `.github/workflows/` directory
- Or keep it as a backup and disable Actions in GitHub repo settings

## 5. GitLab Runner Requirements

If using **GitLab.com SaaS** (gitlab.com), shared runners are provided — no setup needed.

If **self-hosted GitLab**, ensure runners have:
- Docker executor (required for all jobs)
- Docker-in-Docker capability (for `backend-docker` job)
- At least 4GB RAM (for PostGIS + test suite)
- Network access to DigitalOcean API and Slack API

## 6. Monitoring

### Pipeline Badges

Add to your `README.md`:

```markdown
[![pipeline status](https://gitlab.com/iexpertapps-group/AirAds-web/badges/main/pipeline.svg)](https://gitlab.com/iexpertapps-group/AirAds-web/-/pipelines)
[![coverage report](https://gitlab.com/iexpertapps-group/AirAds-web/badges/main/coverage.svg)](https://gitlab.com/iexpertapps-group/AirAds-web/-/commits/main)
```

### Useful Links

- **Pipelines:** https://gitlab.com/iexpertapps-group/AirAds-web/-/pipelines
- **Environments:** https://gitlab.com/iexpertapps-group/AirAds-web/-/environments
- **Merge Requests:** https://gitlab.com/iexpertapps-group/AirAds-web/-/merge_requests
- **CI/CD Variables:** https://gitlab.com/iexpertapps-group/AirAds-web/-/settings/ci_cd
- **DO Dashboard:** https://cloud.digitalocean.com/apps

## 7. DigitalOcean App Platform Setup

### Step A: Create a DO Personal Access Token

1. Go to https://cloud.digitalocean.com/account/api/tokens
2. Create a token with **read + write** scope
3. Add it as `DIGITALOCEAN_ACCESS_TOKEN` in GitLab CI/CD Variables

### Step B: Create Managed Databases

PostGIS is required — use **Managed Database clusters**, not App Platform dev databases.

1. **PostgreSQL**: Create → Engine: PostgreSQL 16 → Enable PostGIS extension
   - After creation, connect and run: `CREATE EXTENSION IF NOT EXISTS postgis;`
2. **Redis**: Create → Engine: Redis 7
3. Note the connection strings for each (used in app env vars)

### Step C: Create Apps (one per environment)

```bash
# Install doctl
brew install doctl
doctl auth init

# Create development app
doctl apps create --spec .do/app.yaml
# Note the App ID from output → set as DO_APP_ID_DEV in GitLab

# For staging/prod, edit .do/app.yaml:
#   - name: airaad-staging (or airaad-prod)
#   - branch: staging (or main)
#   - instance sizes as needed
#   - VITE_APP_ENV: staging (or production)
doctl apps create --spec .do/app.yaml
```

### Step D: Configure App Secrets

In each app's **Settings → App-Level Environment Variables**, set:

| Secret | Value |
|--------|-------|
| `DATABASE_URL` | `postgis://user:pass@host:25060/db?sslmode=require` |
| `REDIS_URL` | `rediss://default:pass@host:25061/0` |
| `CELERY_BROKER_URL` | Same as REDIS_URL |
| `CELERY_RESULT_BACKEND` | Same as REDIS_URL |
| `SECRET_KEY` | Django secret key |
| `ENCRYPTION_KEY` | 32-byte base64 key |
| `STRIPE_SECRET_KEY` | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `AWS_ACCESS_KEY_ID` | S3 credentials |
| `AWS_SECRET_ACCESS_KEY` | S3 credentials |

### Step E: Routing

DO App Platform routes automatically based on the app spec:
- `/api/*` → backend service (port 8000)
- `/*` → frontend static site (CDN)

No nginx reverse proxy needed — DO handles routing.

## 8. Rollback Procedure

### Automatic (Production Only)

If `verify-prod` fails, `rollback-prod` triggers automatically and redeploys.

### Manual Rollback (via Dashboard)

1. Go to https://cloud.digitalocean.com/apps/\<APP_ID\>/deployments
2. Find the last healthy deployment
3. Click **Rollback** on that deployment

### Manual Rollback (via Git)

```bash
# Find the release tag
git tag --list 'release-*' --sort=-creatordate | head -5

# Revert to a specific tag
git checkout <release-tag>
git push gitlab main --force  # Requires unprotecting branch temporarily

# Or revert the commit
git revert HEAD
git push gitlab main
# Pipeline will run and deploy the reverted code
```

## 9. File Reference

| File | Purpose |
|------|---------|
| `.gitlab-ci.yml` | Main CI/CD pipeline (all stages) |
| `.do/app.yaml` | DigitalOcean App Platform spec (template for all envs) |
| `.gitlab/merge_request_templates/Default.md` | Default MR template |
| `airaad/frontend/Dockerfile` | Frontend Docker image (for docker-compose) |
| `airaad/backend/Dockerfile` | Backend Docker image (used by DO App Platform) |
| `.github/workflows/*.yml` | Legacy GitHub Actions (can be removed after migration) |
| `docs/GITLAB_MIGRATION_GUIDE.md` | This document |
