# AirAd — Product Manager Codebase Review Prompt
### Purpose: Determine WHAT is fully implemented E2E vs partially implemented vs missing
### Authority Documents: DOC-1 · DOC-2 · DOC-4 (listed below)
### Target: @product-manager (static code review only — no test execution)

---

> **YOUR ROLE:** You are the Product Manager reviewing the AirAd codebase.
>
> **YOUR GOAL:** Produce a definitive **Implementation Status Report** that answers:
> 1. Which modules/features are **fully implemented end-to-end** (backend + frontend + tests)?
> 2. Which are **partially implemented** (some layers missing)?
> 3. Which are **not implemented at all**?
> 4. Where does the implementation **deviate from the 3 specification documents**?
>
> **RULES:**
> - Read source code files only — do NOT run any commands
> - Do NOT read any audit reports, status files, or prior review documents
> - Do NOT assume anything is implemented — verify it exists in the actual code
> - Mark each item as: ✅ FULL · ⚠️ PARTIAL · ❌ MISSING · 🔴 SPEC DEVIATION
> - Every PARTIAL and MISSING item needs a one-line gap description
> - Every SPEC DEVIATION needs the exact spec reference it violates

---

## AUTHORITY DOCUMENTS (Ground Truth for all checks)

| Ref | File | What it defines |
|-----|------|-----------------|
| **[DOC-1]** | `01_AirAd_Data_Collection_and_Seed_Data.docx` | Geographic hierarchy, vendor data model, tag system (5 layers), GPS validation rules, seed data requirements, QA thresholds |
| **[DOC-2]** | `02_AirAd_Vendor_Functional_Document.md` | Vendor types, claim workflow, subscription tiers (Phase B), business profile fields, CSV import columns |
| **[DOC-4]** | `04_AirAd_Admin_Operations_and_Governance_Document.md` | 6 admin roles + access matrix, vendor verification workflow, tag governance, fraud detection, analytics dashboards, audit log retention |

---

## STEP 1 — READ THE CODEBASE (in this exact order)

Read all files listed below before writing a single status line. Understand the full picture first.

### Backend — Read these files:
```
requirements/base.txt
requirements/production.txt
config/settings/base.py
config/settings/production.py
config/urls.py
celery_app.py

core/encryption.py
core/geo_utils.py
core/middleware.py
core/pagination.py
core/exceptions.py
core/schemas.py
core/storage.py
core/utils.py

apps/accounts/models.py
apps/accounts/permissions.py
apps/accounts/serializers.py
apps/accounts/services.py
apps/accounts/views.py
apps/accounts/urls.py

apps/geo/models.py
apps/geo/serializers.py
apps/geo/services.py
apps/geo/views.py
apps/geo/urls.py
apps/geo/migrations/ (scan for RunSQL GiST index)

apps/vendors/models.py
apps/vendors/serializers.py
apps/vendors/services.py
apps/vendors/views.py
apps/vendors/urls.py

apps/tags/models.py
apps/tags/serializers.py
apps/tags/services.py
apps/tags/views.py
apps/tags/urls.py

apps/imports/models.py
apps/imports/parsers.py
apps/imports/tasks.py
apps/imports/serializers.py
apps/imports/views.py
apps/imports/urls.py

apps/field_ops/models.py
apps/field_ops/services.py
apps/field_ops/views.py
apps/field_ops/urls.py

apps/qa/models.py
apps/qa/tasks.py
apps/qa/services.py
apps/qa/views.py
apps/qa/urls.py

apps/analytics/views.py
apps/analytics/serializers.py
apps/analytics/urls.py

apps/audit/models.py
apps/audit/middleware.py
apps/audit/utils.py
apps/audit/views.py
apps/audit/urls.py

management/commands/seed_data.py (or wherever seed command lives)

tests/ (scan all test files — check what is actually tested)
```

### Frontend — Read these files:
```
frontend/src/styles/dls-tokens.css
frontend/src/main.tsx
frontend/src/App.tsx (or router file)

frontend/src/components/dls/Button.tsx
frontend/src/components/dls/Badge.tsx
frontend/src/components/dls/Table.tsx
frontend/src/components/dls/Modal.tsx
frontend/src/components/dls/Drawer.tsx
frontend/src/components/dls/Toast.tsx
frontend/src/components/dls/Sidebar.tsx
frontend/src/components/dls/Input.tsx
frontend/src/components/shared/EmptyState.tsx
frontend/src/components/shared/SkeletonTable.tsx

frontend/src/pages/Dashboard.tsx
frontend/src/pages/Geography.tsx  (or /geo)
frontend/src/pages/Tags.tsx
frontend/src/pages/Vendors.tsx
frontend/src/pages/VendorDetail.tsx
frontend/src/pages/Imports.tsx
frontend/src/pages/FieldOps.tsx
frontend/src/pages/QA.tsx
frontend/src/pages/AuditLog.tsx
frontend/src/pages/Users.tsx

frontend/src/api/ (all files)
frontend/src/stores/ (all files)
frontend/package.json

docker-compose.yml
backend/Dockerfile
frontend/Dockerfile
.github/workflows/ci.yml
```

---

## STEP 2 — PRODUCE THE IMPLEMENTATION STATUS REPORT

Write your report in the exact structure below. Do not skip any section.

---

# AirAd Implementation Status Report
**Reviewed by:** @product-manager
**Date:** [today]
**Codebase state:** [describe in 1 sentence what you found — e.g., "Backend mostly complete, frontend has 3 pages missing"]

---

## MODULE 1: Authentication & User Management

### Spec Requirements ([DOC-4] §2.1–2.2)
[DOC-4] defines 6 admin roles: Super Admin, Operations Manager, Content Moderator, Data Quality Analyst, Support Agent, Analytics Observer.
[Master Prompt] implements 7 roles: SUPER_ADMIN, DATA_MANAGER, QC_REVIEWER, FIELD_AGENT, CONTENT_MODERATOR, ANALYTICS_VIEWER, IMPORT_OPERATOR.

| Feature | Status | Gap / Deviation |
|---------|--------|-----------------|
| AdminUser model with UUID PK | | |
| Exactly 7 admin roles in code match spec intent | | |
| Role names in code vs [DOC-4] §2.1 — do they map correctly? | | |
| Account lockout after 5 failed attempts | | |
| locked_until field + 30-minute window | | |
| HTTP 429 with Retry-After header on lockout | | |
| Successful login resets failed_login_count | | |
| JWT access token 15min / refresh 7 days | | |
| ROTATE_REFRESH_TOKENS = True in settings | | |
| JWT custom claims: role, email, full_name | | |
| Login creates AuditLog entry | | |
| Users page in frontend (SUPER_ADMIN only) | | |
| Create user with auto-generated password shown once | | |
| Unlock Account button with confirmation modal in UI | | |

**[DOC-4] §2.2 Access Control Matrix — Role Mapping Verification:**

Describe in 2–3 sentences: do the 7 implemented roles cover all responsibilities defined in [DOC-4]'s 6-role matrix? Any responsibilities uncovered?

---

## MODULE 2: Geographic Hierarchy

### Spec Requirements ([DOC-1] §2.1–2.4)
[DOC-1] defines a strict 4-level hierarchy: Country → City → Area → Landmark.
Aliases are mandatory (min 3 per landmark). GPS is stored as coordinates. Boundary polygons for Areas. AR anchor points for Landmarks.

| Feature | Status | Gap / Deviation |
|---------|--------|-----------------|
| Country model with UUID PK | | |
| City model with centroid (PointField), aliases (JSONField), bounding_box (PolygonField) | | |
| Area model with parent_area self-FK | | |
| Landmark model with aliases (min 3), location (PointField) | | |
| ar_anchor_points field on Landmark ([DOC-1] §2.2) | | |
| GiST spatial index via RunSQL migration (NOT models.Index) | | |
| Slug auto-generated on create, immutable after | | |
| GET /api/v1/geo/tree/?city={id} endpoint | | |
| GET /api/v1/geo/cities/{id}/launch-readiness/ endpoint | | |
| Launch readiness checks: vendors ≥500, tags configured, QC ≥80% ([DOC-1] §9) | | |
| Alias warning when landmark has <3 aliases ([DOC-1] §2.3) | | |
| All geo mutations create AuditLog | | |
| Seed data: Pakistan + 3 cities (Islamabad, Lahore, Karachi) ([DOC-1] seed) | | |
| Seed data: Islamabad areas (F-10, F-7, Blue Area, etc.) | | |
| Seed data: Landmarks with ≥3 aliases each (The Centaurus, Jinnah Super, etc.) | | |
| Frontend: Geography page with collapsible Country→City→Area→Landmark tree | | |
| Frontend: Leaflet map showing city centroid + bounding box | | |
| Frontend: Launch Readiness checklist + Launch City button (disabled until ready) | | |
| Frontend: Alias count warning displayed in UI | | |

**[DOC-1] §2.3 Alias System — Spec Alignment:**

Describe: does the alias implementation match [DOC-1]'s requirements for voice discovery? (min 3, case-insensitive, no duplicates within same city)

---

## MODULE 3: Vendor Data Model & Management

### Spec Requirements ([DOC-1] §3, [DOC-2] §2–4, [DOC-4] §3)
[DOC-1] §3 defines the pre-seed vendor data model (unclaimed + claimed states).
[DOC-2] §2 defines 4 vendor types: Food, Retail, Service, Micro-Vendor.
[DOC-4] §3 defines the verification workflow (auto + manual) with SLA targets.

| Feature | Status | Gap / Deviation |
|---------|--------|-----------------|
| Vendor model UUID PK | | |
| gps_point as PostGIS PointField (NOT separate lat/lng floats) | | |
| phone_number_encrypted as BinaryField | | |
| qc_status: PENDING, APPROVED, REJECTED, NEEDS_REVIEW | | |
| qc_reviewed_by as FK to AdminUser (NOT raw UUIDField) | | |
| is_deleted = True soft delete (default False, db_index=True) | | |
| data_source: CSV_IMPORT, GOOGLE_PLACES, MANUAL_ENTRY, FIELD_AGENT | | |
| business_hours as JSONField validated by BusinessHoursSchema | | |
| updated_at = auto_now=True | | |
| Vendor types match [DOC-2] §2.1 (Food, Retail, Service, Micro-Vendor)? | | |
| Pre-seeded "unclaimed" state represented in model ([DOC-1] §3.1) | | |
| GPS accuracy field (gps_accuracy_m) for validation ([DOC-1] §4.1) | | |
| gps_validated boolean field | | |
| GiST spatial index via RunSQL on gps_point | | |
| Vendor CRUD endpoints (GET/POST/PATCH/DELETE) | | |
| Phone decrypted on read, encrypted on write | | |
| DELETE is soft (is_deleted=True) — never hard delete | | |
| is_deleted=True excluded from all list queries by default | | |
| business_hours validated via BusinessHoursSchema on every write | | |
| All vendor mutations create AuditLog with before+after state | | |
| QC approve endpoint — role-gated (QC_REVIEWER, DATA_MANAGER, SUPER_ADMIN) | | |
| QC reject endpoint — requires non-empty qc_notes ([DOC-4] §3.2) | | |
| QC flag endpoint — sets qc_status=NEEDS_REVIEW | | |
| Vendor audit trail endpoint: GET /api/v1/vendors/{id}/audit-trail/ | | |
| Vendor field photos endpoint: GET /api/v1/vendors/{id}/photos/ | | |
| Frontend: Vendor list with search + filters (qc_status, city, area, data_source) | | |
| Frontend: Phone number masked in vendor list | | |
| Frontend: QC Queue view (PENDING + NEEDS_REVIEW only, oldest first) | | |
| Frontend: QC Queue count badge in sidebar | | |
| Frontend: Vendor detail is FULL PAGE (not a modal) | | |
| Frontend: Vendor detail has exactly 6 tabs (Overview, Photos, Visits, Tags, Analytics, Internal Notes) | | |
| Frontend: Internal Notes tab hidden from non-SUPER_ADMIN/QC_REVIEWER | | |
| Frontend: Approve/Reject/Flag buttons with proper role visibility | | |
| Frontend: Reject modal requires qc_notes before submit | | |

**[DOC-4] §3.2 Manual Verification SLA — Spec Alignment:**

Describe: does the QC workflow support the SLA targets in [DOC-4]? (<24hr standard, <6hr priority). Is there any queue prioritization implemented?

**[DOC-4] §3.3 Duplicate Claim Handling — Spec Alignment:**

Describe: is the duplicate claim resolution workflow implemented as per [DOC-4]?

---

## MODULE 4: Tag System (5 Layers)

### Spec Requirements ([DOC-1] §4, [DOC-4] §5)
[DOC-1] §4 defines 5 tag layers:
- Layer 1 (Category): 50 predefined tags — Food, Pizza, Cafe, etc.
- Layer 2 (Intent): 30 tags — Cheap, BudgetUnder300, Premium, etc.
- Layer 3 (Promotion): 10 auto-generated — DiscountLive, HappyHour, etc.
- Layer 4 (Time): 8 auto-generated — Breakfast, Lunch, OpenNow, etc.
- Layer 5 (System): 6 invisible — ClaimedVendor, ARPriority, etc.
[DOC-4] §5 defines tag governance: tag addition process, monthly audit, tag deprecation rules.

| Feature | Status | Gap / Deviation |
|---------|--------|-----------------|
| Tag model covers all 5 layer types (CATEGORY, INTENT, PROMOTION, TIME, SYSTEM) | | |
| Layer 1: 50 Category tags seeded ([DOC-1] §4.1) | | |
| Layer 2: 30 Intent tags seeded ([DOC-1] §4.2) | | |
| Layer 3: Promotion tags auto-generated (not manually created) | | |
| Layer 4: Time tags auto-generated | | |
| Layer 5: System tags (ClaimedVendor, ARPriority, etc.) seeded and read-only | | |
| SYSTEM tags cannot be created/edited/deleted via API | | |
| Tag slug auto-generated, immutable | | |
| Tag soft delete (is_active=False) — vendor-tag assignments preserved | | |
| Vendor tag assignment: POST /api/v1/vendors/{id}/tags/ | | |
| Max 3 Category tags per vendor enforced ([DOC-1] §3.2 — Rule R2) | | |
| CONTENT_MODERATOR can manage CATEGORY + INTENT only ([DOC-4] §2.2) | | |
| All tag mutations create AuditLog | | |
| Tag deprecation logic ([DOC-4] §5.1: usage <1% for 3 months) | | |
| Frontend: Tags page with tag type tabs (Layer 1–5) | | |
| Frontend: SYSTEM tags in read-only section | | |
| Frontend: Tag usage sparkline chart | | |
| Frontend: Bulk tag operations with progress toast | | |
| Frontend: Tag count by type visible | | |

**[DOC-1] §4 Tag Architecture — Spec Alignment:**

Describe: are all 5 tag layers correctly represented in the data model? Are Layer 3 (Promotion) and Layer 4 (Time) auto-generated vs manually created? Is this distinction implemented?

---

## MODULE 5: CSV Import Engine

### Spec Requirements ([DOC-1] §6, [DOC-2] §4)
[DOC-1] §6 defines CSV import as primary bulk data ingestion method.
[DOC-2] §4.1 defines per-row error handling: batch must continue, errors logged.
Required CSV columns: business_name, address_text, latitude, longitude, phone_number, city_slug, area_slug, description.

| Feature | Status | Gap / Deviation |
|---------|--------|-----------------|
| ImportBatch model with UUID PK | | |
| file_key is CharField (S3 key only — NOT FileField) | | |
| status: QUEUED, PROCESSING, DONE, FAILED | | |
| total_rows, processed_rows, error_count fields | | |
| error_log is JSONField capped at 1000 entries | | |
| created_by is FK to AdminUser | | |
| Celery task accepts ONLY batch_id (not file content or path) | | |
| Task reads CSV from S3 using file_key | | |
| Idempotency guard: checks status != PROCESSING before starting | | |
| Per-row error appended to error_log, batch continues | | |
| error_log cap enforced at 1000 entries | | |
| CSV column validation: all 8 required columns present | | |
| task_failure signal handler registered in celery_app.py | | |
| POST /api/v1/imports/presigned-url/ endpoint | | |
| POST /api/v1/imports/ create ImportBatch + trigger Celery | | |
| GET /api/v1/imports/ list all jobs | | |
| GET /api/v1/imports/{id}/ detail with progress | | |
| POST /api/v1/imports/{id}/retry/ with idempotency guard | | |
| Frontend: Drag-and-drop CSV upload zone | | |
| Frontend: PapaParse client-side validation before upload | | |
| Frontend: Auto-refresh every 10s for QUEUED/PROCESSING jobs | | |
| Frontend: Progress bar (processed_rows / total_rows) | | |
| Frontend: Error log visible with row-level details | | |

**[DOC-1] §6 Import Spec — Alignment:**

Describe: does the import engine handle ALL required columns from [DOC-1]? Any column missing or incorrectly validated?

---

## MODULE 6: Field Operations

### Spec Requirements ([DOC-1] §4.1, [DOC-2] §7)
[DOC-1] §4.1 defines GPS validation via field teams: photo evidence + GPS stamping.
[DOC-2] §7 defines field visit workflow for vendor data collection and verification.

| Feature | Status | Gap / Deviation |
|---------|--------|-----------------|
| FieldVisit model with UUID PK | | |
| FieldVisit: vendor FK, agent FK, visited_at, visit_notes, gps_confirmed_point (PointField) | | |
| FieldPhoto model: s3_key CharField (NOT FileField or URLField) | | |
| FieldPhoto: no public S3 URL stored (presigned on read) | | |
| FIELD_AGENT queryset scoped to agent=request.user at service level | | |
| GPS drift >20m triggers qc_status=NEEDS_REVIEW via PostGIS ([DOC-1] §4.1) | | |
| Presigned S3 URL generated on read (1hr expiry) | | |
| Photo soft delete only (is_active=False) | | |
| All field ops mutations create AuditLog | | |
| CRUD endpoints for visits and photos | | |
| Frontend: Field Ops page with visit log | | |
| Frontend: Photo gallery with lightbox | | |
| Frontend: Assignment map (vendors needing field visits) | | |

---

## MODULE 7: QA & GPS Drift Detection

### Spec Requirements ([DOC-1] §8, [DOC-4] §5.3)
[DOC-1] §8.1 defines duplicate detection: ≥85% name similarity within 50m.
[DOC-1] §8.2 defines GPS drift: >20m weekly scan, flag for review.
[DOC-4] §5.3 defines GPS validation workflow: admin cross-check with Google Maps.

| Feature | Status | Gap / Deviation |
|---------|--------|-----------------|
| weekly_gps_drift_scan Celery task exists | | |
| Drift scan: scheduled Sunday 02:00 UTC in celery_app.py setup_periodic_tasks() | | |
| Drift calculation uses ST_Distance(::geography) > 20 — NOT degree×constant | | |
| Drift scan: sets qc_status=NEEDS_REVIEW on flagged vendors | | |
| Drift scan: creates AuditLog per flagged vendor | | |
| daily_duplicate_scan Celery task exists | | |
| Duplicate scan: scheduled daily 03:00 UTC | | |
| Duplicate detection: SequenceMatcher ≥ 0.85 within 50m ([DOC-1] §8.1) | | |
| Duplicate scan: capped at 100 comparisons per vendor | | |
| DriftFlag or DuplicateFlag model exists for storing flags | | |
| Both tasks have retry logic (max 3 retries, exponential backoff) | | |
| GET /api/v1/qa/drift-flags/ endpoint | | |
| POST /api/v1/qa/drift-flags/{id}/resolve/ endpoint | | |
| GET /api/v1/qa/duplicate-flags/ endpoint | | |
| POST /api/v1/qa/duplicate-flags/{id}/merge/ endpoint | | |
| POST /api/v1/qa/drift-scan/trigger/ — SUPER_ADMIN only | | |
| Frontend: QA page with GPS drift queue | | |
| Frontend: Side-by-side comparison modal for duplicates | | |
| Frontend: Merge wizard (DATA_MANAGER + SUPER_ADMIN only) | | |
| Frontend: "Run GPS Drift Scan Now" button (SUPER_ADMIN only) | | |

**[DOC-1] §9 QA Thresholds — Alignment:**

State: does the code enforce the [DOC-1] KPI targets?
- GPS accuracy: ±10m for 95% of listings
- Tag accuracy: 95% minimum
- Duplicate threshold: zero within 50m
- Pre-seed: 500+ vendors per launch area

---

## MODULE 8: Analytics & KPI Reporting

### Spec Requirements ([DOC-4] §7)
[DOC-4] §7 defines 4 analytics dashboards: Platform Health, Vendor Verification, Moderator Performance, User Behavior.

| Feature | Status | Gap / Deviation |
|---------|--------|-----------------|
| GET /api/v1/analytics/overview/ | | |
| GET /api/v1/analytics/vendors/by-city/ (choropleth data) | | |
| GET /api/v1/analytics/vendors/by-qc-status/ | | |
| GET /api/v1/analytics/imports/trend/?days=N | | |
| GET /api/v1/analytics/field-ops/activity/?days=N | | |
| GET /api/v1/analytics/qa/drift-flags/trend/ | | |
| All analytics: ANALYTICS_VIEWER role or higher | | |
| All analytics: Redis cache 5 minutes | | |
| All analytics: exclude is_deleted=True vendors from counts | | |
| Frontend: Dashboard hero metric (Total Verified Vendors with % change) | | |
| Frontend: 4 metric cards (Pending QC, Import Success Rate, Drift Flags, Field Visits) | | |
| Frontend: Recharts donut chart (QC status breakdown) | | |
| Frontend: Leaflet choropleth map (vendors per city) | | |
| Frontend: Import activity line chart with 7d/14d/30d toggle | | |
| Frontend: Recent Activity Feed (last 10 AuditLog entries) | | |
| Frontend: Auto-refresh every 60 seconds | | |
| Frontend: Skeleton loaders on all chart areas | | |

**[DOC-4] §7.1–7.4 Dashboard Spec — Alignment:**

Which of the 4 dashboard types in [DOC-4] are implemented in the frontend? Which are missing?

---

## MODULE 9: Audit Trail System

### Spec Requirements ([DOC-4] §2.3, §6)
[DOC-4] §2.3: all admin actions logged with timestamp, admin ID, action type, target, IP, reason.
[DOC-4] §6 defines log retention: active 1 year, archived 5 years.

| Feature | Status | Gap / Deviation |
|---------|--------|-----------------|
| AuditLog model: UUID PK, action, actor (FK SET_NULL), actor_label | | |
| AuditLog: before_state, after_state (JSONField) | | |
| AuditLog: request_id, ip_address, created_at | | |
| AuditLog: compound index on (target_type, target_id) | | |
| AuditLog: NO update() or delete() method — fully immutable | | |
| log_action() utility function in audit/utils.py | | |
| Every POST/PATCH/DELETE creates AuditLog — verified in spot-check of 3 services | | |
| Celery/system actions: actor=None, actor_label='SYSTEM_CELERY' | | |
| GET /api/v1/audit/logs/ — SUPER_ADMIN only | | |
| GET /api/v1/audit/logs/{target_type}/{id}/ — per-object history | | |
| POST /api/v1/audit/logs/export/ — CSV export | | |
| RequestIDMiddleware attaches UUID to every request | | |
| Audit log retention policy implemented (1yr active, 5yr archive) ([DOC-4] §2.3) | | |
| Frontend: AuditLog page — SUPER_ADMIN only route | | |
| Frontend: JSON diff viewer for before/after state | | |
| Frontend: NO edit or delete buttons on AuditLog page | | |
| Frontend: Export CSV button | | |
| Frontend: Filters by actor, action, target_type, date_range | | |

---

## MODULE 10: Infrastructure & DevOps

### Spec Requirements (Master Prompt §5)

| Feature | Status | Gap / Deviation |
|---------|--------|-----------------|
| Backend Dockerfile: multi-stage, gunicorn in final CMD | | |
| Frontend Dockerfile: multi-stage, nginx:alpine in final stage | | |
| docker-compose.yml: NO source volume mounts in production | | |
| docker-compose.yml: services — postgres, redis, backend, celery-worker, celery-beat, frontend, nginx | | |
| celery-beat: deploy.replicas: 1 | | |
| postgres: using postgis/postgis:16-3.4 image | | |
| Healthchecks on postgres and redis | | |
| Backend not directly port-exposed (only nginx is) | | |
| .env.example: NO literal placeholder values | | |
| psycopg2 (compiled) — NOT psycopg2-binary in any requirements file | | |
| CI: lint job (ruff/flake8 + black + isort) | | |
| CI: migration check job (manage.py migrate --check) | | |
| CI: test job with --cov-fail-under=80 | | |
| CI: security scan (bandit + safety) | | |
| CI: frontend lint + build jobs | | |
| GET /api/v1/health/ unauthenticated, returns 503 when DB down | | |

---

## MODULE 11: Test Coverage Assessment

Read the actual test files in tests/ directory. Do not assume anything passes.

| Test Category | Status | What's actually tested | What's missing |
|---------------|--------|----------------------|----------------|
| Business Rule R1: GPS ≤10m validation | | | |
| Business Rule R2: ≥1 CategoryTag before approval | | | |
| Business Rule R3: reject requires qc_notes | | | |
| Business Rule R4: CSV per-row error continues batch | | | |
| Business Rule R5: phone AES-256-GCM encrypt/decrypt | | | |
| Business Rule R6: vendor soft delete only | | | |
| Business Rule R7: duplicate ≥85% within 50m | | | |
| Business Rule R8: all mutations create AuditLog | | | |
| Business Rule R9: field photos as S3 presigned URLs | | | |
| Business Rule R10: GPS drift >20m weekly scan | | | |
| Account lockout after 5 failures | | | |
| JWT claims include role, email, full_name | | | |
| RBAC: forbidden roles return 403 | | | |
| RBAC: permitted roles return 200/201 | | | |
| Celery import task idempotency | | | |
| factory_boy factories exist for all models | | | |
| Overall coverage level (look for .coveragerc or CI config) | | | |

---

## MODULE 12: DOC-1 Spec Alignment — Data Collection & Seed Data

Go through [DOC-1] section by section and check each against the codebase:

| [DOC-1] Section | Requirement | Status | Gap |
|-----------------|-------------|--------|-----|
| §2.1 | 4-level geo hierarchy: Country→City→Area→Landmark | | |
| §2.2 | All location fields: canonical_name, aliases, gps_coordinates, parent_id, boundary_polygon, ar_anchor_points | | |
| §2.3 | Alias system: min 3 per landmark, case-insensitive, no city-level duplicates | | |
| §3.1 | Pre-seed vendor model has unclaimed state | | |
| §3.2 | Vendor required fields: name, phone, GPS, address, city, area, category | | |
| §4.1 | GPS validation: ±10m accuracy threshold for gps_validated=True | | |
| §4.1 | Field team validation: photo evidence + GPS stamping | | |
| §4.2 | Vendor types: Food, Retail, Service, Micro-Vendor — all 4 supported | | |
| §6 | CSV import: all 8 required columns validated | | |
| §6 | Per-row import: continues on error, errors logged | | |
| §8.1 | Duplicate detection: ≥85% name similarity within 50m | | |
| §8.2 | GPS drift: >20m triggers flag, weekly scan | | |
| §9 | KPI targets: 500+ vendors/city, 95% GPS accuracy, 95% tag accuracy | | |
| Seed | Python→Pakistan seeded | | |
| Seed | 3 cities: Islamabad, Lahore, Karachi seeded | | |
| Seed | Islamabad areas ≥10 seeded (F-10, F-7, Blue Area, etc.) | | |
| Seed | Landmarks with ≥3 aliases seeded (Centaurus, Jinnah Super, etc.) | | |
| Seed | Layer 1: 50 Category tags seeded | | |
| Seed | Layer 2: 30 Intent tags seeded | | |
| Seed | Layer 5: System tags seeded (ClaimedVendor, ARPriority, etc.) | | |

---

## MODULE 13: DOC-2 Spec Alignment — Vendor Functional Document

| [DOC-2] Section | Requirement | Status | Gap |
|-----------------|-------------|--------|-----|
| §2.1 | 4 vendor types supported: Food, Retail, Service, Micro-Vendor | | |
| §4.1 | CSV import: per-row error handling, batch does not abort | | |
| §7.1 | Field visit photos: stored in S3, presigned URLs on read | | |
| Phase A scope | Vendor claim/subscription features correctly excluded from Phase A | | |
| Phase A scope | No vendor login, no vendor dashboard, no subscription tiers in codebase | | |

---

## MODULE 14: DOC-4 Spec Alignment — Admin Operations & Governance

| [DOC-4] Section | Requirement | Status | Gap |
|-----------------|-------------|--------|-----|
| §2.1 | 6 roles defined in spec — 7 implemented. Do all 6 spec roles map to implemented roles? | | |
| §2.2 | Vendor Verification Queue: SUPER_ADMIN + OPS_MANAGER access | | |
| §2.2 | Content Moderation Dashboard: SUPER_ADMIN + OPS_MANAGER + Moderator | | |
| §2.2 | Tag Taxonomy Editor: SUPER_ADMIN + Data Analyst only | | |
| §2.2 | Vendor Suspension Actions: SUPER_ADMIN + OPS_MANAGER only | | |
| §2.3 | Audit log: timestamp, admin ID, action type, target, IP, reason all stored | | |
| §2.3 | Audit log retention: 1yr active, 5yr archive policy implemented | | |
| §3.1 | Auto-verification: OTP + GPS proximity check (100m) — Phase A admin manual only? | | |
| §3.2 | Manual verification: <24hr SLA, queue prioritization for high-engagement | | |
| §3.3 | Duplicate claim: fuzzy name + GPS 10m detection, admin resolution workflow | | |
| §5.1 | Tag addition: Data Analyst proposes, Super Admin approves | | |
| §5.1 | Tag deprecation: usage <1% for 3 months triggers removal from UI | | |
| §5.2 | Monthly tag accuracy audit: 5% random sample, 95% accuracy target | | |
| §5.3 | GPS drift detection: >20m weekly scan, admin cross-check workflow | | |
| §6 | Fraud detection: duplicate claims, GPS spoofing detection | | |
| §7.1 | Platform Health Dashboard: total vendors, QC rates, import stats | | |
| §7.2 | Vendor Verification Dashboard: pending queue, approval rates, SLA compliance | | |
| §7.3 | Moderator Performance Dashboard: review time, queue backlog | | |
| §7.4 | User Behavior Dashboard: search queries, tag usage, geographic hotspots | | |
| §8.1 | GDPR: data export, deletion, minimization — any implementation? | | |

---

## STEP 3 — FINAL SUMMARY

After completing all tables above, write this summary section:

---

### ✅ FULLY IMPLEMENTED MODULES (Backend + Frontend + Tests)
List each module that is 100% complete end-to-end. For each, state:
- What is fully working
- Test coverage level

### ⚠️ PARTIALLY IMPLEMENTED MODULES
List each module with gaps. For each, state:
- What IS implemented
- What IS NOT implemented
- Which layer is missing (backend / frontend / tests)
- Which spec document is violated and which section

### ❌ NOT IMPLEMENTED
List any feature defined in DOC-1, DOC-2, or DOC-4 that has zero implementation.

### 🔴 SPEC DEVIATIONS (Implementation differs from spec)
List any place where the code exists but does it WRONG compared to the spec. Include:
- What the spec says ([DOC-X] §Y.Z)
- What the code actually does
- Severity: CRITICAL / HIGH / MEDIUM

### 📊 OVERALL IMPLEMENTATION SCORECARD

```
MODULE                          STATUS      BACKEND   FRONTEND   TESTS
─────────────────────────────────────────────────────────────────────
Auth & User Management          [xx%]       [%]       [%]        [%]
Geographic Hierarchy            [xx%]       [%]       [%]        [%]
Vendor Management               [xx%]       [%]       [%]        [%]
Tag System (5 layers)           [xx%]       [%]       [%]        [%]
CSV Import Engine               [xx%]       [%]       [%]        [%]
Field Operations                [xx%]       [%]       [%]        [%]
QA & GPS Drift Detection        [xx%]       [%]       [%]        [%]
Analytics & KPI                 [xx%]       [%]       [%]        [%]
Audit Trail                     [xx%]       [%]       [%]        [%]
Infrastructure & DevOps         [xx%]       [N/A]     [N/A]      [N/A]
─────────────────────────────────────────────────────────────────────
OVERALL PHASE A                 [xx%]
```

### 🎯 TOP 5 PRIORITY GAPS
List the 5 most critical gaps (by business impact + spec requirement) that must be fixed before Phase A can be considered production-ready. Include spec reference for each.

---

*PM Codebase Review Prompt — v1.0*
*Authority: AirAd_Master_Super_Prompt_MERGED.md (Unified Edition v3.0)*
*Spec Documents: DOC-1 (Data Collection) · DOC-2 (Vendor Functional) · DOC-4 (Admin Governance)*
*Review type: Static code review only — no test execution, no commands*
