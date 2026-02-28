# AirAd — DigitalOcean Services Required

> Document generated: Feb 28, 2026

---

## 1. App Platform (3 Apps)

Each app contains 4 components deployed together:

| Component        | Type               | What It Does                                          |
|------------------|--------------------|-------------------------------------------------------|
| **backend**      | Service (Dockerfile) | Django + Gunicorn on port 8000, serves `/api/*`      |
| **celery-worker**| Worker (Dockerfile)  | Background task processing                           |
| **celery-beat**  | Worker (Dockerfile)  | Scheduled task scheduler (exactly 1 instance)        |
| **frontend**     | Static Site          | React SPA built with Vite, served via DO CDN at `/`  |

Create **3 separate apps** from the `.do/app.yaml` template:

| App Name          | Branch    | Instance Size          | Purpose       |
|-------------------|-----------|------------------------|---------------|
| `airaad-dev`      | `develop` | `basic-xxs` ($5/mo)   | Development   |
| `airaad-staging`  | `staging` | `basic-xs` ($10/mo)   | Staging       |
| `airaad-prod`     | `main`    | `professional-xs` ($12/mo) | Production |

---

## 2. Managed PostgreSQL Database

| Setting             | Value                                                          |
|---------------------|----------------------------------------------------------------|
| **Engine**          | PostgreSQL 16                                                  |
| **Extension**       | PostGIS (run `CREATE EXTENSION IF NOT EXISTS postgis;`)        |
| **Plan**            | Basic ($15/mo dev, $50/mo prod recommended)                    |
| **Region**          | Same as App Platform (e.g. `nyc`)                              |
| **Clusters needed** | 1 per environment (or share dev/staging)                       |

---

## 3. Managed Redis

| Setting             | Value                                                     |
|---------------------|-----------------------------------------------------------|
| **Engine**          | Redis 7                                                   |
| **Purpose**         | Celery broker + result backend, caching                   |
| **Plan**            | Basic ($10/mo dev, $25/mo prod recommended)               |
| **Clusters needed** | 1 per environment (or share dev/staging)                  |

---

## 4. Spaces Object Storage (Optional)

If using DigitalOcean Spaces instead of AWS S3 for media files:

| Setting         | Value                                               |
|-----------------|-----------------------------------------------------|
| **Purpose**     | Vendor images, reels, static files                  |
| **CDN**         | Enable for faster delivery                          |
| **S3-compatible** | Works with existing Django `storages` library     |

> You can continue using AWS S3 instead. Spaces is an option if you want everything on DO.

---

## 5. Cost Estimate Summary

| #  | Service                                      | Qty          | Dev (Monthly) | Prod (Monthly) |
|----|----------------------------------------------|--------------|---------------|----------------|
| 1  | App Platform (backend + workers + frontend)  | 3 apps       | ~$15–20/app   | ~$35–50/app    |
| 2  | Managed PostgreSQL (with PostGIS)            | 1–3 clusters | ~$15/cluster  | ~$50/cluster   |
| 3  | Managed Redis                                | 1–3 clusters | ~$10/cluster  | ~$25/cluster   |
| 4  | Spaces (optional, replaces AWS S3)           | 1 bucket     | ~$5           | ~$5            |

**Development environment estimate:** ~$45–50/mo

**Production environment estimate:** ~$100–150/mo (larger instances + dedicated DB clusters)

---

## 6. Setup Order

1. Create **Managed PostgreSQL** → enable PostGIS → note connection string
2. Create **Managed Redis** → note connection string
3. Create **App Platform apps** using `doctl apps create --spec .do/app.yaml`
4. Set `DATABASE_URL`, `REDIS_URL`, and all secrets in each app's environment variables
5. Add `DO_APP_ID_*` and `DO_APP_URL_*` to GitLab CI/CD Variables

---

## 7. App Environment Variables (Secrets)

Set these in each app's **Settings → App-Level Environment Variables**:

| Secret                   | Value                                                     |
|--------------------------|-----------------------------------------------------------|
| `DATABASE_URL`           | `postgis://user:pass@host:25060/db?sslmode=require`      |
| `REDIS_URL`              | `rediss://default:pass@host:25061/0`                      |
| `CELERY_BROKER_URL`      | Same as REDIS_URL                                         |
| `CELERY_RESULT_BACKEND`  | Same as REDIS_URL                                         |
| `SECRET_KEY`             | Django secret key                                         |
| `ENCRYPTION_KEY`         | 32-byte base64 key                                        |
| `STRIPE_SECRET_KEY`      | Stripe API key                                            |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key                                    |
| `STRIPE_WEBHOOK_SECRET`  | Stripe webhook signing secret                             |
| `AWS_ACCESS_KEY_ID`      | S3 credentials                                            |
| `AWS_SECRET_ACCESS_KEY`  | S3 credentials                                            |
| `AWS_STORAGE_BUCKET_NAME`| S3 bucket name                                            |
| `TWILIO_ACCOUNT_SID`     | Twilio SMS credentials                                    |
| `TWILIO_AUTH_TOKEN`       | Twilio SMS credentials                                    |
| `CORS_ALLOWED_ORIGINS`   | Comma-separated allowed origins                           |
| `FRONTEND_URL`           | Frontend app URL                                          |

---

## 8. GitLab CI/CD Variables

Set these in **GitLab → Settings → CI/CD → Variables**:

| Variable                     | Description                        | Protected | Masked |
|------------------------------|------------------------------------|-----------|--------|
| `DIGITALOCEAN_ACCESS_TOKEN`  | DO API token (read + write)        | Yes       | Yes    |
| `DO_APP_ID_DEV`              | Dev app ID                         | Yes       | No     |
| `DO_APP_ID_STAGING`          | Staging app ID                     | Yes       | No     |
| `DO_APP_ID_PROD`             | Production app ID                  | Yes       | No     |
| `DO_APP_URL_DEV`             | Dev app URL                        | Yes       | No     |
| `DO_APP_URL_STAGING`         | Staging app URL                    | Yes       | No     |
| `DO_APP_URL_PROD`            | Production app URL                 | Yes       | No     |
| `SLACK_WEBHOOK_URL`          | Slack notifications (optional)     | Yes       | Yes    |

---

## 9. Routing (Automatic)

DO App Platform routes based on the app spec:

- `/api/*` → backend service (port 8000)
- `/*` → frontend static site (CDN)

No nginx reverse proxy needed — DigitalOcean handles routing automatically.

---

*Document: AirAd DigitalOcean Services — Prepared for iExpertApps Group*
