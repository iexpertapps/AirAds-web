# BACKEND FIX PLAN

## Source: BACKEND MASTER PLAN — DEEP AUDIT REPORT (Feb 26, 2026)
## Status: AUTHORITATIVE — Every item from the audit is listed here with solution.
## Rule: No item skipped, no placeholder, no TODO — every fix is production-ready.

---

## TABLE OF CONTENTS

- [P0 — Critical Bugs (Runtime Errors)](#p0--critical-bugs)
- [P1 — Missing Features (Entire Apps/Modules)](#p1--missing-features)
- [P2 — Missing Model Fields](#p2--missing-model-fields)
- [P3 — Missing Endpoints](#p3--missing-endpoints)
- [P4 — Missing Celery Tasks](#p4--missing-celery-tasks)
- [P5 — Infrastructure & Production Readiness](#p5--infrastructure--production-readiness)

---

## P0 — CRITICAL BUGS

### P0-1: VoiceBotConfig field references in vendor_portal/services.py

**Problem:** `apps/vendor_portal/services.py` lines 649-656 reference 3 fields that do NOT exist on the `VoiceBotConfig` model:
- `vb.greeting_text` → field does not exist
- `vb.faq_pairs` → field does not exist (actual field: `custom_qa_pairs`)
- `vb.operating_info` → field does not exist (actual field: `opening_hours_summary`)

This causes `AttributeError` at runtime when the dashboard endpoint is called for a vendor with a VoiceBotConfig.

**Solution:** Update the field references to use the actual model field names:
- `vb.greeting_text` → `vb.opening_hours_summary` (closest match — voice bot intro)
- `vb.faq_pairs` → `vb.custom_qa_pairs`
- `vb.operating_info` → `vb.delivery_info`

**Files affected:** `apps/vendor_portal/services.py`

---

## P1 — MISSING FEATURES

### P1-1: Create `apps/reels/` App (Plan §B-9)

**Problem:** The entire Reels feature is missing. No `VendorReel` model, no upload/management endpoints, no reel moderation, no tier-limit enforcement.

**Solution:** Create the full `apps/reels/` Django app:

**Models (`apps/reels/models.py`):**
```
VendorReel:
  id(UUID PK), vendor(FK Vendor),
  title(CharField max 255), s3_key(CharField max 500),
  thumbnail_s3_key(CharField max 500, blank),
  duration_seconds(PositiveIntegerField),
  status(PROCESSING/ACTIVE/REJECTED/ARCHIVED, default PROCESSING),
  view_count(PositiveIntegerField default 0),
  completion_count(PositiveIntegerField default 0),
  display_order(PositiveIntegerField default 0),
  is_active(BooleanField default True),
  moderation_status(PENDING/APPROVED/REJECTED, default PENDING),
  moderation_notes(TextField blank),
  created_at, updated_at
```

**Services (`apps/reels/services.py`):**
- `create_reel(vendor_id, title, s3_key, duration)` — enforce tier limit via `vendor_has_feature()` + SubscriptionPackage.max_videos
- `list_vendor_reels(vendor_id)` — vendor's own reels
- `update_reel(reel_id, vendor_id, data)` — update title/display_order
- `archive_reel(reel_id, vendor_id)` — soft-archive
- `list_public_reels(vendor_slug)` — ACTIVE + APPROVED only
- `record_reel_view(reel_id)` — increment view_count, dispatch analytics event
- `moderate_reel(reel_id, status, notes, admin_user)` — admin moderation

**Views (`apps/reels/views.py`):**
- `VendorReelListCreateView` — GET/POST (IsAuthenticated, vendor owner)
- `VendorReelDetailView` — PATCH/DELETE (IsAuthenticated, vendor owner)
- `PublicVendorReelsView` — GET (AllowAny, by vendor slug)
- `ReelViewEventView` — POST (AllowAny, record view)

**URLs (`apps/reels/urls.py`):** 4 URL patterns

**Additional URLs in `config/urls.py`:**
- `api/v1/vendors/<str:slug>/reels/` → PublicVendorReelsView
- `api/v1/reels/<str:reel_id>/view/` → ReelViewEventView

**Vendor Portal URLs in `apps/vendor_portal/urls.py`** (or standalone under reels):
- `api/v1/vendor-portal/reels/` → VendorReelListCreateView
- `api/v1/vendor-portal/reels/<str:reel_id>/` → VendorReelDetailView

**Files to create:** `apps/reels/__init__.py`, `apps/reels/apps.py`, `apps/reels/models.py`, `apps/reels/services.py`, `apps/reels/views.py`, `apps/reels/urls.py`
**Files to modify:** `config/settings/base.py` (INSTALLED_APPS), `config/urls.py` (register URLs)
**Migration:** `apps/reels/migrations/0001_initial.py`

---

### P1-2: Create `apps/notifications/` App (Plan §B-10)

**Problem:** The entire Notifications feature is missing. No models, no FCM, no push triggers, no churn prevention.

**Solution:** Create the full `apps/notifications/` Django app:

**Models (`apps/notifications/models.py`):**
```
NotificationTemplate:
  id(UUID PK), slug(CharField unique),
  title_template(CharField max 500),
  body_template(TextField),
  notification_type(CLAIM_STATUS/SUBSCRIPTION/PROMOTION/SYSTEM),
  is_active(BooleanField default True),
  created_at

NotificationLog:
  id(UUID PK), recipient_type(VENDOR/CUSTOMER),
  recipient_id(UUID), template(FK NotificationTemplate, nullable),
  title(CharField max 500), body(TextField),
  data_payload(JSONField default dict),
  channel(PUSH/EMAIL/SMS),
  status(SENT/FAILED/PENDING, default PENDING),
  sent_at(DateTimeField nullable),
  created_at
```

**Services (`apps/notifications/services.py`):**
- `send_push_notification(recipient_type, recipient_id, title, body, data)` — FCM dispatch via Celery
- `send_email_notification(recipient_id, subject, body)` — Django send_mail via Celery
- `send_sms_notification(phone_hash, message)` — via core/sms.py
- `create_from_template(slug, recipient_type, recipient_id, context)` — render template + dispatch
- `log_notification(...)` — create NotificationLog entry

**Celery Tasks (`apps/notifications/tasks.py`):**
- `send_push_task(recipient_type, recipient_id, title, body, data)` — async FCM
- `send_email_task(email, subject, body)` — async email

**Views:** None initially (notifications are system-triggered, not API-driven).

**Files to create:** `apps/notifications/__init__.py`, `apps/notifications/apps.py`, `apps/notifications/models.py`, `apps/notifications/services.py`, `apps/notifications/tasks.py`
**Files to modify:** `config/settings/base.py` (INSTALLED_APPS)
**Migration:** `apps/notifications/migrations/0001_initial.py`

---

### P1-3: Vendor Portal Discount CRUD Endpoints (Plan §B-6)

**Problem:** Discount model exists in `apps/vendors/models.py` but there are ZERO API endpoints for vendors to manage their discounts. All 6 endpoints are missing.

**Solution:** Create discount management views/URLs:

**Views (add to `apps/vendors/discount_views.py`):**
- `VendorDiscountListCreateView` — GET list / POST create (IsAuthenticated, vendor owner)
- `VendorDiscountDetailView` — PATCH update / DELETE deactivate (IsAuthenticated, vendor owner)
- `VendorDiscountAnalyticsView` — GET campaign performance (IsAuthenticated, vendor owner)
- `VendorHappyHourCreateView` — POST create happy hour (tier-gated via vendor_has_feature)

**Services (add to `apps/vendors/discount_services.py`):**
- `list_vendor_discounts(vendor_id)` — all discounts for vendor
- `create_discount(vendor_id, data, request)` — validate, create, audit log
- `update_discount(discount_id, vendor_id, data, request)` — partial update
- `deactivate_discount(discount_id, vendor_id, request)` — soft-deactivate
- `get_discount_analytics(discount_id, vendor_id)` — views/taps/clicks during campaign
- `create_happy_hour(vendor_id, data, request)` — tier-gated, enforce daily limit

**URLs in `apps/vendor_portal/urls.py` (add):**
```
vendor-portal/discounts/                     → VendorDiscountListCreateView
vendor-portal/discounts/<str:discount_id>/   → VendorDiscountDetailView
vendor-portal/discounts/<str:discount_id>/analytics/ → VendorDiscountAnalyticsView
vendor-portal/happy-hours/                   → VendorHappyHourCreateView
```

**Files to create:** `apps/vendors/discount_views.py`, `apps/vendors/discount_services.py`
**Files to modify:** `apps/vendor_portal/urls.py`

---

### P1-4: Vendor Portal Voice Bot CRUD Endpoints (Plan §B-7)

**Problem:** VoiceBotConfig model exists but there are ZERO vendor-portal endpoints for managing voice bot config. The 3 portal endpoints are all missing.

**Solution:** Create voice bot management views/URLs:

**Views (add to `apps/vendors/voicebot_views.py`):**
- `VendorVoiceBotView` — GET config / PUT update (IsAuthenticated, vendor owner)
- `VendorVoiceBotTestView` — POST test query (IsAuthenticated, vendor owner)

**Services (add to `apps/vendors/voicebot_services.py`):**
- `get_voicebot_config(vendor_id)` — get or create config
- `update_voicebot_config(vendor_id, data, request)` — update, auto-generate hours_summary
- `test_voice_query(vendor_id, query)` — run rule-based query matching against vendor's config

**URLs in `apps/vendor_portal/urls.py` (add):**
```
vendor-portal/voice-bot/      → VendorVoiceBotView
vendor-portal/voice-bot/test/ → VendorVoiceBotTestView
```

**Files to create:** `apps/vendors/voicebot_views.py`, `apps/vendors/voicebot_services.py`
**Files to modify:** `apps/vendor_portal/urls.py`

---

### P1-5: Vendor Portal Analytics Endpoints (Plan §B-11)

**Problem:** 4 vendor-portal analytics endpoints and 3 admin analytics endpoints are missing.

**Solution:** Add remaining analytics endpoints:

**Missing vendor analytics views (add to `apps/analytics/views.py`):**
- `VendorAnalyticsDailyView` — GET daily breakdown 14 days (Gold+ tier-gated)
- `VendorAnalyticsCompetitorsView` — GET area benchmarking (Platinum tier-gated)

**Missing admin analytics views (add to `apps/analytics/views.py`):**
- `AdminVendorActivityView` — GET vendor activity stats
- `AdminSubscriptionDistributionView` — GET subscription tier distribution
- `AdminKPIPlatformHealthView` — GET platform health KPIs

**Services (add to `apps/analytics/services.py`):**
- `get_vendor_daily_analytics(vendor_id, days=14)` — daily views/taps/nav breakdown
- `get_vendor_competitors(vendor_id)` — area-level benchmarking
- `get_admin_vendor_activity()` — aggregate vendor activity
- `get_admin_subscription_distribution()` — tier counts
- `get_admin_platform_health_kpis()` — total AR views, avg vendor views, discovery rate, voice usage, moderation backlog

**URLs to add to `apps/analytics/urls.py`:**
```
vendors/<str:vendor_id>/daily/                → VendorAnalyticsDailyView
vendors/<str:vendor_id>/competitors/          → VendorAnalyticsCompetitorsView
admin/vendor-activity/                        → AdminVendorActivityView
admin/subscription-distribution/              → AdminSubscriptionDistributionView
admin/kpi/platform-health/                    → AdminKPIPlatformHealthView
```

**Files to modify:** `apps/analytics/views.py`, `apps/analytics/services.py`, `apps/analytics/urls.py`

---

### P1-6: Admin Moderation Endpoints (Plan §B-12)

**Problem:** 4 admin moderation endpoints are missing — reel approve/reject, discount removal, and moderation queue.

**Solution:** Create admin moderation views:

**Views (add to `apps/vendors/admin_views.py`):**
- `AdminModerateReelApproveView` — POST approve reel
- `AdminModerateReelRejectView` — POST reject reel with reason/strike
- `AdminRemoveDiscountView` — POST remove fraudulent discount
- `AdminModerationQueueView` — GET combined queue (pending reels + pending claims + reports)

**Services:**
- Reel moderation → `apps/reels/services.py:moderate_reel()`
- Discount removal → `apps/vendors/discount_services.py:admin_remove_discount()`
- Moderation queue → `apps/vendors/admin_services.py:get_moderation_queue()`

**URLs to add to `config/urls.py`:**
```
api/v1/admin/moderation/reels/<str:reel_id>/approve/ → AdminModerateReelApproveView
api/v1/admin/moderation/reels/<str:reel_id>/reject/  → AdminModerateReelRejectView
api/v1/admin/moderation/discounts/<str:discount_id>/remove/ → AdminRemoveDiscountView
api/v1/admin/moderation/queue/ → AdminModerationQueueView
```

**Files to modify:** `apps/vendors/admin_views.py`, `config/urls.py`

---

### P1-7: Missing Claim Flow Endpoints (Plan §B-3)

**Problem:** 3 claim flow endpoints are missing:
- `POST /api/v1/vendors/{id}/claim/verify-otp/` — OTP verification for claim
- `POST /api/v1/vendors/{id}/claim/upload-proof/` — Manual verification upload
- `GET /api/v1/vendors/{id}/claim/status/` — Check claim status

**Solution:** Add to existing claim views:

**Views (add to `apps/vendors/claim_views.py`):**
- `ClaimVerifyOTPView` — POST verify OTP for claim (automated path)
- `ClaimUploadProofView` — POST upload storefront photo + business license (manual path)
- `ClaimStatusView` — GET current claim status

**Services (add to `apps/vendors/claim_services.py`):**
- `verify_claim_otp(vendor_id, otp_code, user)` — verify OTP + GPS proximity check
- `upload_claim_proof(vendor_id, proof_s3_key, license_s3_key, user)` — store proof, set CLAIM_PENDING
- `get_claim_status(vendor_id)` — return current claim status + timestamp

**URLs to add to `apps/vendors/urls.py`:**
```
<str:vendor_id>/claim/verify-otp/   → ClaimVerifyOTPView
<str:vendor_id>/claim/upload-proof/ → ClaimUploadProofView
<str:vendor_id>/claim/status/       → ClaimStatusView
```

**Files to modify:** `apps/vendors/claim_views.py`, `apps/vendors/claim_services.py`, `apps/vendors/urls.py`

---

### P1-8: Missing Discovery Endpoints (Plan §B-8)

**Problem:** 2 discovery endpoints missing:
- `GET /api/v1/discovery/nearby/reels/` — Nearby reels feed
- `GET /api/v1/tags/discovery/` — Tags for browsing UI

**Solution:**

**Views:**
- `NearbyReelsView` (add to `apps/discovery/views.py`) — GET nearby reels feed (lat, lng, radius params)
- `TagDiscoveryView` (add to `apps/tags/views.py`) — GET tags filtered by tag_types for browsing UI

**Services:**
- `get_nearby_reels(lat, lng, radius)` — query VendorReel joined with Vendor location
- Tags endpoint uses existing Tag queryset with type filter

**URLs:**
- `api/v1/discovery/nearby/reels/` → NearbyReelsView (add to `apps/discovery/urls.py`)
- `api/v1/tags/discovery/` → TagDiscoveryView (add to `apps/tags/urls.py`)

**Files to modify:** `apps/discovery/views.py`, `apps/discovery/urls.py`, `apps/tags/views.py`, `apps/tags/urls.py`

---

### P1-9: Vendor Portal Activation Stage Endpoint (Plan §B-3)

**Problem:** `GET /api/v1/vendor-portal/activation-stage/` is missing.

**Solution:**

**View (add to `apps/vendor_portal/views.py`):**
- `VendorPortalActivationStageView` — GET current stage + next unlock criteria

**Service (add to `apps/vendor_portal/services.py`):**
- `get_activation_stage(vendor_id)` — return current stage, criteria met, next stage criteria

**URL to add to `apps/vendor_portal/urls.py`:**
```
activation-stage/ → VendorPortalActivationStageView
```

**Files to modify:** `apps/vendor_portal/views.py`, `apps/vendor_portal/services.py`, `apps/vendor_portal/urls.py`

---

## P2 — MISSING MODEL FIELDS

### P2-1: CustomerUser Missing Fields

**Problem:** 4 fields from Plan §B-1 are missing on `CustomerUser` in `apps/accounts/models.py`:
- `preferred_radius(int default 500)`
- `preferred_categories(JSONField default list)`
- `last_known_lat(FloatField nullable)`
- `last_known_lng(FloatField nullable)`

**Solution:** Add the 4 fields to `CustomerUser` model. Generate migration.

**Files affected:** `apps/accounts/models.py`
**Migration:** New migration in `apps/accounts/migrations/`

---

### P2-2: Vendor Model Missing Fields

**Problem:** 2 fields from Plan §B-3 are missing on `Vendor` in `apps/vendors/models.py`:
- `total_navigation_clicks(PositiveIntegerField default 0)`
- `activation_stage_updated_at(DateTimeField nullable)`

**Solution:** Add the 2 fields to `Vendor` model. Generate migration.

**Files affected:** `apps/vendors/models.py`
**Migration:** New migration in `apps/vendors/migrations/`

---

### P2-3: SubscriptionPackage Missing Fields

**Problem:** 9 fields from Plan §B-4 are missing on `SubscriptionPackage` in `apps/subscriptions/models.py`:
- `price_monthly_usd(DecimalField nullable)` — USD pricing
- `stripe_price_id(CharField blank)` — link to Stripe
- `max_delivery_configs(IntegerField, default 0)` — delivery config limit
- `voice_bot_type(CharField choices NONE/BASIC/DYNAMIC/ADVANCED, default NONE)`
- `badge_type(CharField choices CLAIMED/VERIFIED/PREMIUM/ELITE, default CLAIMED)`
- `support_level(CharField choices COMMUNITY/EMAIL_48H/PRIORITY_24H/DEDICATED, default COMMUNITY)`
- `analytics_level(CharField choices BASIC/STANDARD/ADVANCED/PREDICTIVE, default BASIC)`
- `display_order(PositiveIntegerField default 0)`
- Note: `max_reels` vs `max_videos` is a naming mismatch — plan says `max_reels`, code says `max_videos`. Leave as `max_videos` (no rename needed, it works).

**Solution:** Add the 8 new fields (keeping max_videos as-is). Update seed command to set values for each tier. Generate migration.

**Files affected:** `apps/subscriptions/models.py`, seed management command
**Migration:** New migration in `apps/subscriptions/migrations/`

---

### P2-4: VoiceBotConfig Missing Fields

**Problem:** 4 fields from Plan §B-7 are missing on `VoiceBotConfig` in `apps/vendors/models.py`:
- `intro_message(TextField blank)` — Gold: static intro
- `pickup_available(BooleanField default False)`
- `is_active(BooleanField default True)`
- `completeness_score(PositiveIntegerField default 0)` — 0-100

**Solution:** Add the 4 fields. Generate migration.

**Files affected:** `apps/vendors/models.py`
**Migration:** New migration in `apps/vendors/migrations/`

---

### P2-5: Discount Model Missing Fields

**Problem:** 6 fields from Plan §B-6 are missing on `Discount` in `apps/vendors/models.py`:
- `delivery_radius_m(PositiveIntegerField nullable)` — for free delivery campaigns
- `free_delivery_distance_m(PositiveIntegerField nullable)`
- `ar_badge_text(CharField max 50, blank)` — e.g. "20% OFF", "Happy Hour"
- `views_during_campaign(PositiveIntegerField default 0)`
- `taps_during_campaign(PositiveIntegerField default 0)`
- `navigation_clicks_during_campaign(PositiveIntegerField default 0)`

**Solution:** Add the 6 fields. Generate migration.

**Files affected:** `apps/vendors/models.py`
**Migration:** New migration in `apps/vendors/migrations/`

---

## P3 — MISSING ENDPOINTS

### P3-1: GDPR Account Deletion (Plan §B-1)

**Problem:** `DELETE /api/v1/auth/customer/account/` is missing — GDPR data deletion request.

**Solution:** Add `CustomerAccountDeleteView` to `apps/accounts/otp_views.py`. Service function marks account as deleted, anonymizes personal data, creates audit log.

**Files affected:** `apps/accounts/otp_views.py`, `apps/accounts/otp_services.py`, `apps/accounts/urls.py`

---

## P4 — MISSING CELERY TASKS

### P4-1: vendor_activation_check (Plan §B-3)

**Problem:** The `vendor_activation_check` Celery task is missing. This task should run daily and transition vendors through the 5 Progressive Activation stages: CLAIM → ENGAGEMENT → MONETIZATION → GROWTH → RETENTION.

**Solution:** Add to `apps/vendors/tasks.py`:
- `vendor_activation_check()` — daily task
- Logic: query all claimed vendors, evaluate each against stage criteria:
  - CLAIM → ENGAGEMENT: logged in ≥3 times OR uploaded first reel, min 3 days since claim
  - ENGAGEMENT → MONETIZATION: created ≥1 discount OR 7 days since claim
  - MONETIZATION → GROWTH: upgraded from Silver OR 14 days active
  - GROWTH → RETENTION: 30+ days since claim
- Update `activation_stage` and `activation_stage_updated_at`
- Create AuditLog for each transition

**Register in `celery_app.py`:**
```python
'vendor-activation-check': {
    'task': 'apps.vendors.tasks.vendor_activation_check',
    'schedule': crontab(hour=2, minute=0),  # daily at 2 AM
},
```

**Files affected:** `apps/vendors/tasks.py`, `celery_app.py`

---

## P5 — INFRASTRUCTURE & PRODUCTION READINESS

### P5-1: SMS Service Abstraction (core/sms.py)

**Problem:** SMS sending is a logger stub in `apps/accounts/otp_services.py:_send_sms()`. No actual SMS will be sent in production. Plan specifies `core/sms.py` as a Twilio abstraction layer.

**Solution:** Create `core/sms.py` with:
- `send_sms(phone_number: str, message: str) -> bool` — dispatches via Twilio in production, logs in development
- Uses `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` from settings
- Fallback to logger if Twilio credentials not configured (graceful dev mode)
- Update `apps/accounts/otp_services.py:_send_sms()` to call `core.sms.send_sms()`

**Files to create:** `core/sms.py`
**Files to modify:** `apps/accounts/otp_services.py`, `config/settings/base.py`
**Dependency:** Add `twilio>=9.0.0` to `requirements/base.txt`

---

### P5-2: Missing Environment Variables

**Problem:** 8 env vars from Plan §11 are missing in `.env.example`:
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
- `FIREBASE_CREDENTIALS_JSON`
- `SENTRY_DSN`
- `JWT_ACCESS_LIFETIME_MINUTES`, `JWT_REFRESH_LIFETIME_DAYS`
- `STRIPE_SILVER_PRICE_ID`

**Solution:** Add all 8 to `.env.example` with clear comments. Add corresponding reads in `config/settings/base.py`.

**Files affected:** `.env.example`, `config/settings/base.py`

---

### P5-3: Analytics Stubs Still Present

**Problem:** `apps/analytics/services.py` still has Phase A stubs:
- `top_search_terms: list[dict] = []` — should aggregate AnalyticsEvent search queries
- `system_alerts: list[dict] = []` — should check for system issues

**Solution:** Replace stubs with real DB queries:
- `top_search_terms` → aggregate SEARCH events from AnalyticsEvent, group by metadata query, count, top 10
- `system_alerts` → check for: vendors with 0 views in 7 days, failed import batches, high error rate

**Files affected:** `apps/analytics/services.py`

---

### P5-4: Logout Returns 400

**Problem:** `/api/v1/auth/logout/` returns HTTP 400 (known since E2E audit). Session still clears but response code is wrong.

**Solution:** Fix logout view to return 200 on successful token blacklist/session clear.

**Files affected:** `apps/accounts/views.py` (logout view)

---

### P5-5: Landing Page featured_stories Hardcoded

**Problem:** `apps/vendor_portal/services.py:get_landing_page_stats()` returns `featured_stories: []` as a hardcoded empty list.

**Solution:** Query actual vendor success data — top 3 vendors by total_views with highest subscription tier, return their business_name, subscription_level, total_views, city.

**Files affected:** `apps/vendor_portal/services.py`

---

### P5-6: Payments App Missing tasks.py

**Problem:** Plan §8 specifies `apps/payments/tasks.py` for async Stripe operations. File does not exist.

**Solution:** Create `apps/payments/tasks.py` with:
- `sync_subscription_status(vendor_id)` — pull latest status from Stripe API, update local DB
- Used as fallback if webhook is missed

**Files to create:** `apps/payments/tasks.py`

---

## IMPLEMENTATION ORDER

The fixes must be implemented in this exact order due to dependencies:

```
Round 1 — Critical Bug Fix:
  P0-1  Fix VoiceBotConfig field references (runtime error)

Round 2 — Model Fields (needed before endpoints):
  P2-1  CustomerUser missing fields
  P2-2  Vendor missing fields
  P2-3  SubscriptionPackage missing fields
  P2-4  VoiceBotConfig missing fields
  P2-5  Discount missing fields
  → Generate + apply all migrations together

Round 3 — New Apps (models must exist first):
  P1-1  Create apps/reels/ (VendorReel model + services + views + URLs)
  P1-2  Create apps/notifications/ (NotificationTemplate + NotificationLog + services)
  → Generate + apply migrations

Round 4 — New Endpoints on Existing Apps:
  P1-3  Discount CRUD endpoints
  P1-4  Voice Bot CRUD endpoints
  P1-5  Analytics endpoints (vendor daily, competitors, admin activity/distribution/health)
  P1-6  Admin moderation endpoints
  P1-7  Claim flow endpoints (verify-otp, upload-proof, status)
  P1-8  Discovery endpoints (nearby reels, tags discovery)
  P1-9  Activation stage endpoint
  P3-1  GDPR account deletion endpoint

Round 5 — Celery Tasks:
  P4-1  vendor_activation_check task

Round 6 — Infrastructure:
  P5-1  core/sms.py (Twilio abstraction)
  P5-2  Missing env vars
  P5-3  Analytics stubs
  P5-4  Logout 400 fix
  P5-5  Landing page featured_stories
  P5-6  Payments tasks.py

Final — Verification:
  python manage.py makemigrations --check
  python manage.py check
  python manage.py check --deploy
```

---

## TOTAL ITEMS: 22

| Priority | Count | Items |
|---|---|---|
| P0 (Critical) | 1 | P0-1 |
| P1 (Missing Features) | 9 | P1-1 through P1-9 |
| P2 (Missing Fields) | 5 | P2-1 through P2-5 |
| P3 (Missing Endpoints) | 1 | P3-1 |
| P4 (Missing Tasks) | 1 | P4-1 |
| P5 (Infrastructure) | 6 | P5-1 through P5-6 |

**Estimated files to create:** ~15 new files
**Estimated files to modify:** ~20 existing files
**Estimated new migrations:** ~5

---

**— End of Backend Fix Plan —**
