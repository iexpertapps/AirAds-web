# AirAd — BACKEND MASTER PLAN
## Enterprise-Grade, Production-Ready Django Backend
### Complete Rebuild — Phase A (Admin/Data) → Phase B (Public Platform) → Phase C (Vendor Portal APIs)

**Version:** 2.0 — Full Rebuild  
**Date:** February 2026  
**Status:** AUTHORITATIVE — Supersedes `01_BACKEND_PLAN.md`  
**DB Strategy:** SQLite for local dev, PostgreSQL + PostGIS for staging/production
**Subscription Ref:** `requirements/AirAd Phase-1 – Tiered Vendor Subscription Architecture-2.md`
**Value Ladder:** Visibility (Silver) → Control (Gold) → Automation (Diamond) → Dominance (Platinum)

---

## TABLE OF CONTENTS

1. [Current State Audit](#1-current-state-audit)
2. [Architecture Decisions](#2-architecture-decisions)
3. [Database Strategy](#3-database-strategy)
4. [Project Structure](#4-project-structure)
5. [Phase A — Admin & Data Collection (Existing → Stabilize)](#5-phase-a--admin--data-collection)
6. [Phase B — Public Platform APIs](#6-phase-b--public-platform-apis)
7. [Phase C — Vendor Portal APIs](#7-phase-c--vendor-portal-apis)
8. [Stripe Subscription Integration](#8-stripe-subscription-integration)
9. [Security Architecture](#9-security-architecture)
10. [Testing Strategy](#10-testing-strategy)
11. [CI/CD & Deployment](#11-cicd--deployment)
12. [Build Sequence & Sessions](#12-build-sequence--sessions)
13. [Quality Gate Checklist](#13-quality-gate-checklist)
14. [Non-Negotiable Rules](#14-non-negotiable-rules)

---

## 1. CURRENT STATE AUDIT

### What Exists (Phase A — ~80% Complete)

| App | Status | Notes |
|---|---|---|
| `accounts` | ✅ Stable | 11 RBAC roles, JWT auth, lockout, AdminUser model |
| `geo` | ✅ Stable | Country → City → Area → Landmark hierarchy, PostGIS PointFields |
| `tags` | ✅ Stable | 6 tag types, immutable slugs, SYSTEM tag protection |
| `vendors` | ✅ Stable | Vendor model with AES-256-GCM phone encryption, soft delete, M2M tags |
| `imports` | ✅ Stable | ImportBatch + CSV/Google Places import engine, S3 storage |
| `field_ops` | ✅ Stable | FieldVisit + FieldPhoto with S3 presigned URLs |
| `audit` | ✅ Stable | Immutable AuditLog, log_action() utility |
| `analytics` | ⚠️ Partial | AnalyticsEvent model exists, services.py has hardcoded values |
| `qa` | ⚠️ Partial | GPS drift scan model exists, tasks need verification |
| `governance` | ⚠️ Partial | FraudScore, Blacklist, VendorSuspension, ConsentRecord — models only, needs PostGIS migration |
| `subscriptions` | ❌ Stub | Empty app — needs full build |
| `discovery` | ❌ Stub | Empty app — needs full build |
| `health` | ✅ Stable | Health check endpoint |

### Known Issues to Fix First

1. **`analytics/services.py`** — hardcoded `"total_tags": 0` (fixed in E2E audit but verify)
2. **Governance migrations** — need PostGIS to generate (blocked without PostGIS)
3. **`/api/v1/auth/logout/`** — returns 400 (session still clears, cosmetic fix needed)
4. **Coverage at 79.02%** — needs to reach 80%+ after Phase B additions
5. **No Customer/Vendor user models** — only AdminUser exists
6. **No Discount/VoiceBotConfig/SubscriptionPackage models** — stubs only
7. **No Stripe integration** — not even stubbed
8. **No OTP authentication** — only email/password for admin

---

## 2. ARCHITECTURE DECISIONS

### Non-Negotiable Patterns (Carry Forward)

| Rule | Enforcement |
|---|---|
| PostGIS `ST_Distance` ONLY | Never degree × constant for distance |
| AES-256-GCM for all phone numbers | Encrypt/decrypt in `services.py` only |
| `for_roles()` class factory | The ONLY RBAC mechanism |
| All business logic in `services.py` | Never in views or serializers |
| AuditLog on every POST/PATCH/DELETE | Immutable, forever |
| Soft deletes only | `is_deleted=True`, never hard delete |
| CSV content never over Celery broker | Pass `batch_id` only |
| `error_log` capped at 1000 entries | In ImportBatch |
| `celery-beat` replicas: 1 always | Single scheduler instance |
| UUID PKs on all models | `default=uuid.uuid4` (callable) |
| JSONField defaults as callables | `default=list` not `default=[]` |

### New Architecture Decisions

| Decision | Rationale |
|---|---|
| **Three user types in one JWT** | `user_type` claim: ADMIN / VENDOR / CUSTOMER — single auth middleware |
| **Separate user models** | `AdminUser` (existing), `VendorUser`, `CustomerUser` — each with own auth flow |
| **Stripe webhooks via separate app** | `apps/payments/` — isolates payment logic from subscriptions |
| **Feature gating via `vendor_has_feature()`** | Single function, never scattered if-else |
| **Rule-based NLP only** | No ML in Phase 1 — keyword matching + intent classification |
| **Analytics events via Celery** | Never block API request to record analytics |
| **AnalyticsEvent partitioned by month** | High-volume table needs partition strategy |
| **SQLite for dev, Postgres for prod** | `settings/development.py` uses SQLite, `settings/production.py` uses PostGIS |

---

## 3. DATABASE STRATEGY

### Development (SQLite + SpatiaLite)

```python
# config/settings/development.py
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
SPATIALITE_LIBRARY_PATH = 'mod_spatialite'  # macOS: brew install spatialite-tools
```

**Why SpatiaLite:** Supports PointField, ST_Distance, ST_DWithin — same API as PostGIS. Zero Docker dependency for local dev.

### Staging / Production (PostgreSQL + PostGIS)

```python
# config/settings/production.py
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}
```

### Migration Compatibility Rules

1. All PointField columns use `django.contrib.gis.db.models.PointField` — works on both backends
2. GiST indexes via `migrations.RunSQL` — conditional: only apply on PostgreSQL
3. Never use PostgreSQL-specific features in migrations without `RunSQL` conditional
4. Test migrations on both SQLite (dev) and PostgreSQL (CI) before merge

---

## 4. PROJECT STRUCTURE

```
airaad/backend/
├── config/
│   ├── settings/
│   │   ├── base.py              # Shared: DRF, JWT, Celery, middleware
│   │   ├── production.py        # PostGIS, S3, DEBUG=False, Sentry
│   │   ├── development.py       # SpatiaLite/SQLite, DEBUG=True
│   │   └── test.py              # CELERY_TASK_ALWAYS_EAGER, test DB
│   ├── urls.py                  # All /api/v1/ routes
│   └── asgi.py / wsgi.py
├── celery_app.py                # Celery + Beat schedules + task_failure handler
├── apps/
│   ├── accounts/                # AdminUser, JWT, lockout, RBAC [EXISTING]
│   ├── geo/                     # Country, City, Area, Landmark [EXISTING]
│   ├── tags/                    # Tag taxonomy [EXISTING]
│   ├── vendors/                 # Vendor, VendorMedia [EXISTING → EXTEND]
│   ├── imports/                 # ImportBatch, CSV/Google engine [EXISTING]
│   ├── field_ops/               # FieldVisit, FieldPhoto [EXISTING]
│   ├── audit/                   # AuditLog [EXISTING]
│   ├── analytics/               # AnalyticsEvent, KPI endpoints [EXISTING → EXTEND]
│   ├── qa/                      # GPS drift, duplicate detection [EXISTING]
│   ├── governance/              # FraudScore, Blacklist, Suspension [EXISTING → EXTEND]
│   ├── health/                  # Health check [EXISTING]
│   │
│   │   ── NEW APPS (Phase B + C) ──
│   │
│   ├── customers/               # CustomerUser, OTP auth, preferences
│   ├── vendor_auth/             # VendorUser, OTP auth, claim flow
│   ├── subscriptions/           # SubscriptionPackage, VendorSubscription
│   ├── payments/                # Stripe integration, webhooks, invoices
│   ├── discounts/               # Discount, HappyHour, Campaign engine
│   ├── voicebot/                # VoiceBotConfig, FAQ pairs, voice query
│   ├── discovery/               # Search engine, ranking, voice search
│   ├── reels/                   # VendorReel, upload, processing
│   ├── notifications/           # Push notifications, email triggers
│   └── vendor_portal/           # Vendor portal-specific aggregation APIs
├── core/
│   ├── encryption.py            # AES-256-GCM [EXISTING]
│   ├── geo_utils.py             # PostGIS wrappers [EXISTING]
│   ├── middleware.py            # RequestIDMiddleware [EXISTING]
│   ├── pagination.py            # StandardResultsPagination [EXISTING]
│   ├── exceptions.py            # custom_exception_handler [EXISTING]
│   ├── storage.py               # S3 helpers [EXISTING]
│   ├── schemas.py               # BusinessHoursSchema [EXISTING]
│   ├── utils.py                 # get_client_ip, vendor_has_feature [EXISTING → EXTEND]
│   ├── otp.py                   # OTP generation, verification, rate limiting [NEW]
│   ├── sms.py                   # SMS service abstraction (Twilio) [NEW]
│   └── stripe_utils.py          # Stripe helper functions [NEW]
├── manage.py
├── requirements/
│   ├── base.txt
│   ├── production.txt
│   ├── development.txt
│   └── test.txt
└── start.sh / Dockerfile
```

---

## 5. PHASE A — ADMIN & DATA COLLECTION

### Status: ~80% Complete — Stabilization Required

### A-FIX-1: Fix Known Bugs

| Bug | Fix |
|---|---|
| `analytics/services.py` hardcoded values | Verify Tag count fix is applied, add tests |
| `/api/v1/auth/logout/` returns 400 | Fix logout view to return 200 on token blacklist |
| Governance migrations blocked | Add conditional PostGIS check in migration |
| Coverage < 80% | Add missing test cases for analytics, governance |

### A-FIX-2: Complete Governance App

The governance models exist but need:
1. `governance/services.py` — full CRUD for FraudScore, Blacklist, VendorSuspension
2. `governance/serializers.py` — DRF serializers for all 5 models
3. `governance/views.py` — ViewSets with proper RBAC
4. `governance/urls.py` — Wire to `/api/v1/governance/`
5. Tests for all governance business logic
6. Fix migration to work without PostGIS (conditional RunSQL)

### A-FIX-3: Analytics Services Completion

- Replace all hardcoded values in `analytics/services.py`
- Wire real DB queries for: total_vendors, total_tags, total_areas, etc.
- Add vendor_views_by_day aggregation
- Add import_activity_by_day aggregation

### A-GATE: Phase A Complete When

- [ ] All 673+ existing tests pass
- [ ] Coverage ≥ 80%
- [ ] `docker-compose up` brings full stack
- [ ] Governance app fully functional with tests
- [ ] Analytics returns real data from DB
- [ ] All 10 admin pages work end-to-end (verified via Playwright)
- [ ] CI pipeline fully green

---

## 6. PHASE B — PUBLIC PLATFORM APIs

### B-1: Customer Authentication (`apps/customers/`)

**Models:**
```
CustomerUser:
  id(UUID PK), phone_number(unique, encrypted), email(nullable),
  full_name(nullable), device_token(FCM token),
  preferred_radius(int default 500), preferred_categories(JSONField[]),
  is_active, last_known_lat(float nullable), last_known_lng(float nullable),
  created_at, updated_at
```

**Endpoints:**
```
POST /api/v1/auth/customer/send-otp/     → Send OTP via SMS (Twilio)
POST /api/v1/auth/customer/verify-otp/   → Verify OTP → create/login → JWT
PATCH /api/v1/auth/customer/profile/     → Update name, email, device_token
GET  /api/v1/auth/customer/me/           → Current customer profile
POST /api/v1/auth/customer/refresh/      → Refresh JWT
DELETE /api/v1/auth/customer/account/    → GDPR data deletion request
```

**OTP Flow:**
1. Rate limit: max 3 OTPs per phone per 10 minutes
2. OTP valid for 5 minutes, 6 digits
3. 3 failed verifications → 30-minute cooldown
4. Twilio SMS abstracted via `core/sms.py` (swappable for test mock)
5. JWT payload includes: `user_type: "CUSTOMER"`, `user_id`, `phone`

### B-2: Vendor Authentication (`apps/vendor_auth/`)

**Models:**
```
VendorUser:
  id(UUID PK), phone_number(unique, encrypted), email(nullable, unique),
  full_name, vendor(FK to Vendor, OneToOne, nullable — set after claim),
  is_email_verified, device_token(FCM),
  is_active, created_at, updated_at
```

**Endpoints:**
```
POST /api/v1/auth/vendor/send-otp/       → Send OTP
POST /api/v1/auth/vendor/verify-otp/     → Verify → create/login → JWT
POST /api/v1/auth/vendor/verify-email/   → Email verification link
PATCH /api/v1/auth/vendor/profile/       → Update profile
GET  /api/v1/auth/vendor/me/             → Current vendor user + vendor details
POST /api/v1/auth/vendor/refresh/        → Refresh JWT
```

**JWT payload:** `user_type: "VENDOR"`, `user_id`, `vendor_id` (nullable until claim), `subscription_level`

### B-3: Vendor Claim Flow (`apps/vendor_auth/`)

**Endpoints:**
```
GET  /api/v1/vendors/unclaimed/nearby/?lat&lng&radius  → Nearby unclaimed listings
POST /api/v1/vendors/{id}/claim/                       → Initiate claim
POST /api/v1/vendors/{id}/claim/verify-otp/            → OTP verification for claim
POST /api/v1/vendors/{id}/claim/upload-proof/           → Manual verification upload
GET  /api/v1/vendors/{id}/claim/status/                → Check claim status
```

**Claim Flow Logic (services.py):**
1. Vendor searches nearby unclaimed listings (GPS + radius)
2. Selects a listing → "Claim This Business"
3. **Automated path:** System sends OTP to phone on file + GPS proximity check (within 100m)
4. **Manual path:** Upload storefront photo + business license → admin review queue
5. On approval: VendorUser.vendor = Vendor, Vendor.claimed_status = True, auto-assign SILVER tier
6. AuditLog for every claim action
7. Push notification on approval/rejection

**Vendor Model Extensions (new migration):**
```
Vendor (extend):
  + owner(FK VendorUser, nullable, OneToOne)
  + claimed_at(datetime nullable)
  + logo_s3_key(CharField, blank)
  + cover_photo_s3_key(CharField, blank)
  + offers_delivery(bool default False)
  + offers_pickup(bool default False)
  + is_verified(bool default False)
  + subscription_level(CharField choices: SILVER/GOLD/DIAMOND/PLATINUM, default SILVER)
  + subscription_valid_until(datetime nullable)
  + activation_stage(CharField choices: CLAIM/ENGAGEMENT/MONETIZATION/GROWTH/RETENTION, default CLAIM)
  + activation_stage_updated_at(datetime nullable)
  + total_views(PositiveIntegerField default 0)
  + total_profile_taps(PositiveIntegerField default 0)
  + total_navigation_clicks(PositiveIntegerField default 0)
  + location_pending_review(bool default False)
```

**Progressive Activation Strategy (§3.2 — Time-Based Feature Reveal):**

Vendors unlock features gradually to prevent overwhelming UI and ensure value realization.
Activation stage transitions are managed by a Celery task (`vendor_activation_check`, runs daily).

```
Stage 1: CLAIM (Day 0)
  → Basic profile editing, business hours, single reel upload
  → Dashboard shows: views count only
  → Other features greyed out: "Unlock after 3 days of activity"

Stage 2: ENGAGEMENT (Day 3+ OR first reel uploaded)
  → Unlock: view analytics, create discounts, voice intro (if Gold+)
  → Dashboard shows: full basic metrics
  → Trigger: vendor has logged in ≥3 times OR uploaded first reel

Stage 3: MONETIZATION (Day 7+ OR first discount created)
  → Unlock: upgrade prompts become visible, advanced analytics teaser
  → Show ROI data: "Your listing drove X views — see what Gold unlocks"
  → Trigger: vendor has created ≥1 discount OR 7 days since claim

Stage 4: GROWTH (post-upgrade OR Day 14+)
  → Full tier features unlocked per subscription level
  → No restrictions beyond subscription tier
  → Trigger: vendor upgraded from Silver OR 14 days active

Stage 5: RETENTION (Day 30+)
  → Monthly reports, churn prevention triggers active
  → Re-engagement flows if inactive
```

**API Support:**
```
GET /api/v1/vendor-portal/activation-stage/    → Current stage + next unlock criteria
```

**Implementation:**
- `vendor_activation_check` Celery task (daily): evaluates each vendor's activity against stage criteria, transitions stage, updates `activation_stage_updated_at`
- Frontend/mobile reads `activation_stage` from dashboard API to show/hide features progressively
- Stage transitions logged in AuditLog

### B-4: Subscription System (`apps/subscriptions/`)

**Models:**
```
SubscriptionPackage:
  id(UUID PK), level(SILVER/GOLD/DIAMOND/PLATINUM unique),
  name, price_monthly_pkr(Decimal), price_monthly_usd(Decimal nullable),
  stripe_price_id(CharField blank — set when Stripe configured),
  max_reels(int), daily_happy_hours(int, -1=unlimited),
  max_delivery_configs(int, -1=unlimited),
  has_voice_bot(bool), voice_bot_type(NONE/BASIC/DYNAMIC/ADVANCED),
  sponsored_placement_level(NONE/LIMITED_TIME/AREA_BOOST/AREA_EXCLUSIVE),
  campaign_scheduling_level(NONE/BASIC/ADVANCED/SMART_AUTOMATION),
  has_predictive_reports(bool),
  voice_search_priority(NONE/LOW/MEDIUM/HIGHEST),
  visibility_boost_weight(Decimal — 1.0/1.2/1.5/2.0),
  badge_type(CLAIMED/VERIFIED/PREMIUM/ELITE),
  support_level(COMMUNITY/EMAIL_48H/PRIORITY_24H/DEDICATED),
  analytics_level(BASIC/STANDARD/ADVANCED/PREDICTIVE),
  is_active, display_order, created_at

VendorSubscription:
  id(UUID PK), vendor(FK Vendor), package(FK SubscriptionPackage),
  status(ACTIVE/CANCELLED/EXPIRED/PAST_DUE),
  stripe_subscription_id(CharField nullable),
  stripe_customer_id(CharField nullable),
  current_period_start(datetime), current_period_end(datetime),
  cancel_at_period_end(bool default False),
  created_at, updated_at
```

**Seeded via management command (`seed_subscriptions`):**
```
SILVER:   Free,       1 reel,  0 happy hours, no voice bot,  1.0x visibility, voice_priority=NONE
GOLD:     PKR 3,000,  3 reels, 1 happy hour,  basic voice,   1.2x visibility, voice_priority=LOW
DIAMOND:  PKR 7,000,  6 reels, 3 happy hours, dynamic voice, 1.5x visibility, voice_priority=MEDIUM
PLATINUM: PKR 15,000, unlimited, unlimited,    advanced voice, 2.0x visibility, voice_priority=HIGHEST

Sponsored Placement:
SILVER: NONE, GOLD: LIMITED_TIME, DIAMOND: AREA_BOOST, PLATINUM: AREA_EXCLUSIVE

Campaign Scheduling:
SILVER: NONE, GOLD: BASIC, DIAMOND: ADVANCED, PLATINUM: SMART_AUTOMATION
```

### B-5: Feature Gating (`core/utils.py`)

```python
def vendor_has_feature(vendor: Vendor, feature: str) -> bool:
    """The ONLY gate mechanism for subscription features.
    
    Features: HAPPY_HOUR, VOICE_BOT, VOICE_BOT_DYNAMIC, VOICE_BOT_ADVANCED,
              SPONSORED_LIMITED_TIME, SPONSORED_AREA_BOOST, SPONSORED_AREA_EXCLUSIVE,
              TIME_HEATMAP, PREDICTIVE_RECOMMENDATIONS, EXTRA_REELS,
              CAMPAIGN_BASIC, CAMPAIGN_ADVANCED, CAMPAIGN_SMART_AUTOMATION,
              ITEM_SPECIFIC_DISCOUNT, FLASH_DISCOUNT, BOGO_DEAL,
              FREE_DELIVERY, COMPETITOR_BENCHMARKING, VOICE_SEARCH_PRIORITY
    """
    package = get_vendor_package(vendor)
    return FEATURE_MATRIX[package.level].get(feature, False)
```

**Every premium endpoint checks this function. No scattered if-else anywhere.**

### B-6: Discount & Campaign Engine (`apps/discounts/`)

**Models:**
```
Discount:
  id(UUID PK), vendor(FK Vendor),
  title, discount_type(FLAT/PERCENTAGE/BOGO/HAPPY_HOUR/ITEM_SPECIFIC/FLASH),
  value(Decimal — amount or percentage),
  applies_to(ALL_ITEMS/SPECIFIC_ITEMS), item_description(text, blank),
  start_time(datetime), end_time(datetime),
  is_recurring(bool), recurrence_days(JSONField — [0-6] for weekdays),
  min_order_value(Decimal nullable),
  delivery_radius_m(int nullable — for free delivery campaigns),
  free_delivery_distance_m(int nullable),
  is_active(bool — computed on save based on time window),
  ar_badge_text(CharField — "20% OFF", "Happy Hour", etc.),
  views_during_campaign(int default 0),
  taps_during_campaign(int default 0),
  navigation_clicks_during_campaign(int default 0),
  created_at, updated_at

HappyHour (extends Discount with type=HAPPY_HOUR):
  — Same model, filtered by discount_type
  — Tier limit enforcement in services.py via vendor_has_feature()
```

**Celery Tasks:**
- `discount_scheduler` (every 1 min): auto-activate/deactivate based on time windows
- `tag_auto_assigner` (every 1 hour): assign/remove PROMOTION and TIME tags
- `flash_deal_trigger` (every 30 min): System-triggered flash deals for Platinum vendors during detected slow periods (random surprise discounts — §5.1 Random Flash). Analyzes last 7 days hourly traffic → if current hour < 30% avg → creates 30-min flash deal automatically
- `auto_happy_hour_trigger` (every 1 hour): Platinum-only Smart Automation — detect historically slow time slots from past 14 days analytics → auto-create happy hour if no manual one scheduled (§5.2)
- Discount activates → auto-assign `PROMOTION:DiscountLive` tag
- Discount deactivates → remove PROMOTION tag
- Hourly: assign/remove TIME tags (Breakfast, Lunch, OpenNow, LateNight)

**Endpoints:**
```
GET    /api/v1/vendor-portal/discounts/                → List vendor's discounts
POST   /api/v1/vendor-portal/discounts/                → Create discount
PATCH  /api/v1/vendor-portal/discounts/{id}/           → Update discount
DELETE /api/v1/vendor-portal/discounts/{id}/           → Deactivate discount
GET    /api/v1/vendor-portal/discounts/{id}/analytics/ → Campaign performance
POST   /api/v1/vendor-portal/happy-hours/              → Create happy hour (tier-gated)
```

### B-7: Voice Bot (`apps/voicebot/`)

**Models:**
```
VoiceBotConfig (OneToOne with Vendor):
  id(UUID PK), vendor(OneToOne FK Vendor),
  intro_message(text blank — Gold: static intro),
  menu_items(JSONField — [{name, price, available, category}]),
  delivery_info(JSONField — {radius_km, free_within_km, charges}),
  pickup_available(bool),
  custom_qa_pairs(JSONField — [{question, answer}]),
  hours_summary(text — auto-generated from vendor.business_hours),
  active_discounts_summary(text — auto-updated when discounts change),
  is_active(bool), completeness_score(int 0-100),
  last_data_update(datetime), created_at, updated_at
```

**Endpoints:**
```
GET    /api/v1/vendor-portal/voice-bot/         → Get config
PUT    /api/v1/vendor-portal/voice-bot/         → Update config
POST   /api/v1/vendor-portal/voice-bot/test/    → Test voice query (simulator)
POST   /api/v1/vendors/{slug}/voice-query/      → Public: user asks vendor a question
```

**Voice Bot Query Logic (rule-based, no ML):**
1. Parse user question → keyword extraction
2. Match against menu_items, delivery_info, hours, active discounts, custom QA pairs
3. Generate text response from matched data
4. Return structured response + confidence score

**Celery Task — Data Freshness Validation:**
- `voicebot_freshness_check` (daily at 9 AM):
  - Menu not updated in 30 days → push notification: "Your voice bot menu is outdated. Update it to keep responses accurate."
  - Out-of-stock items persisting >7 days → push: "You have items marked unavailable for over a week. Update or remove them."
  - Completeness score < 50% → push: "Your voice bot is only X% configured. Complete setup for better customer responses."

### B-8: Discovery & Search Engine (`apps/discovery/`)

**RankingService (pure function, independently testable):**
```
Final AR Score =
  (Intent Match × 0.30) +
  (Distance Weight × 0.25) +
  (Active Promotion × 0.15) +
  (Engagement Score × 0.15) +
  (Subscription Multiplier × 0.15)

Subscription Multipliers (from Subscription Architecture doc §4):
  SILVER=1.0, GOLD=1.2, DIAMOND=1.5, PLATINUM=2.0

  NOTE: Silver gets base visibility (1.0), NOT zero.
  "Monetization enhances visibility — it does not gate basic existence."

CRITICAL: Paid tier cannot override distance relevance by more than 30%
```

**Endpoints:**
```
GET  /api/v1/discovery/search/?lat&lng&radius&q&tags     → Text search + location
GET  /api/v1/discovery/nearby/?lat&lng&radius             → Nearby vendors (AR/map)
GET  /api/v1/discovery/nearby/reels/?lat&lng&radius       → Nearby reels feed
POST /api/v1/discovery/voice-search/                      → Rule-based voice NLP
GET  /api/v1/tags/discovery/?tag_types=CATEGORY,INTENT    → Tags for browsing UI
```

**Voice Search NLP (rule-based):**
1. Tokenize query → lowercase → remove stop words
2. Match tokens against: category tags, intent tags, vendor names
3. Extract entities: category, price_intent, time_intent, location_keyword
4. Build filter query → execute RankingService
5. Return ranked vendors + interpreted tags

### B-9: Reels (`apps/reels/`)

**Models:**
```
VendorReel:
  id(UUID PK), vendor(FK Vendor),
  title(CharField), s3_key(CharField — video file),
  thumbnail_s3_key(CharField — auto-generated first frame),
  duration_seconds(int — 9 or 11 only),
  status(PROCESSING/ACTIVE/REJECTED/ARCHIVED),
  view_count(int default 0), completion_count(int default 0),
  display_order(int), is_active(bool),
  moderation_status(PENDING/APPROVED/REJECTED),
  moderation_notes(text blank),
  created_at, updated_at
```

**Tier Limits (enforced in services.py):**
- Silver: 1 reel
- Gold: 3 reels
- Diamond: 6 reels
- Platinum: unlimited

**Endpoints:**
```
GET    /api/v1/vendor-portal/reels/                → List vendor's reels
POST   /api/v1/vendor-portal/reels/                → Upload new reel (presigned URL flow)
PATCH  /api/v1/vendor-portal/reels/{id}/           → Update title, reorder
DELETE /api/v1/vendor-portal/reels/{id}/           → Archive reel
GET    /api/v1/vendors/{slug}/reels/               → Public: vendor's active reels
POST   /api/v1/reels/{id}/view/                    → Record reel view event
```

### B-10: Notifications (`apps/notifications/`)

**Models:**
```
NotificationTemplate:
  id(UUID PK), slug(unique), title_template, body_template,
  notification_type(CLAIM_STATUS/SUBSCRIPTION/PROMOTION/SYSTEM),
  is_active, created_at

NotificationLog:
  id(UUID PK), recipient_type(VENDOR/CUSTOMER),
  recipient_id(UUID), template(FK),
  title, body, data_payload(JSONField),
  channel(PUSH/EMAIL/SMS), status(SENT/FAILED/PENDING),
  sent_at, created_at
```

**Push Notification Triggers:**
- Claim approved/rejected → Vendor
- Subscription expiry reminder (7 days + 1 day) → Vendor
- New discount activated near user → Customer (proximity)
- Flash deal → Customer (visited area in past 7 days)
- New vendor in frequent area → Customer (max 1/week)
- Re-engagement (7 days inactive) → Customer

**Vendor Churn Prevention Triggers (Celery scheduled tasks):**
- `vendor_churn_check` (daily at 10 AM):
  - 7 days inactive (no login) → push: "Your listing had X views this week. Log in to see what's happening."
  - 14 days no reel uploaded → push: "Upload a reel to stay top-of-mind. Vendors with reels get 3x more views."
  - Subscription downgrade detected → trigger survey + generate 20% discount coupon code for re-upgrade (via Stripe coupon API)
  - 30 days post-claim, no upgrade → push: "You've had X views on Silver. See what Gold unlocks."
- `vendor_monthly_report` (1st of every month via Celery Beat):
  - Email report to all claimed vendors: "Your AirAd Presence Report — X AR views, Y nav clicks, Z reel views this month"
  - Uses NotificationLog with channel=EMAIL
  - Silver vendors: include upgrade CTA with ROI projection

**Implementation:**
- FCM via `firebase-admin` SDK
- Email via Django `send_mail` (SMTP configured per environment)
- Device tokens stored on CustomerUser / VendorUser
- All notifications dispatched via Celery tasks (never block API)
- Rate limits: max 2 proximity alerts/day, max 1 new vendor/week

### B-11: Analytics APIs (Phase B Extension)

**Vendor Analytics (requires IsVendorOwner permission):**
```
GET /api/v1/vendor-portal/analytics/summary/          → All tiers: views, taps, nav clicks
GET /api/v1/vendor-portal/analytics/daily/             → Gold+: daily breakdown (14 days)
GET /api/v1/vendor-portal/analytics/hourly/            → Gold+: hourly heatmap
GET /api/v1/vendor-portal/analytics/reels/             → Gold+: reel performance
GET /api/v1/vendor-portal/analytics/discounts/         → Gold+: campaign ROI
GET /api/v1/vendor-portal/analytics/recommendations/   → Platinum: rule-based insights
GET /api/v1/vendor-portal/analytics/competitors/       → Platinum: area benchmarking
```

**Admin Platform Analytics:**
```
GET /api/v1/admin/analytics/platform-overview/
GET /api/v1/admin/analytics/area-heatmap/{city_id}/
GET /api/v1/admin/analytics/search-terms/
GET /api/v1/admin/analytics/vendor-activity/
GET /api/v1/admin/analytics/subscription-distribution/
```

**Admin KPI Dashboard (Business Metrics):**
```
GET /api/v1/admin/analytics/kpis/acquisition/
  → claim_rate (% of listings claimed), verification_completion_rate (target: 80%),
    avg_time_to_first_reel, daily_new_claims, weekly_claim_trend

GET /api/v1/admin/analytics/kpis/engagement/
  → weekly_active_vendors (target: 60%), avg_reels_per_vendor (target: 4/month),
    active_campaign_rate (target: 40%), avg_logins_per_week, reel_upload_rate

GET /api/v1/admin/analytics/kpis/monetization/
  → gold_upgrade_rate (target: 10%), diamond_upgrade_rate (target: 5%),
    monthly_churn_rate (target: <10%), arpu_pkr (target: 2,500),
    mrr_total, subscription_distribution, upgrade_funnel_conversion

GET /api/v1/admin/analytics/kpis/platform-health/
  → total_ar_views_monthly, avg_vendor_views, discovery_to_navigation_rate,
    voice_search_usage_rate, content_moderation_backlog
```

**Rule: NEVER block API request to record analytics. Always dispatch Celery task.**

### B-12: Admin Management APIs (Phase B)

```
POST  /api/v1/admin/vendors/{id}/verify/               → Mark vendor verified
PATCH /api/v1/admin/vendors/{id}/suspend/               → Suspend vendor
POST  /api/v1/admin/vendors/{id}/approve-claim/         → Approve claim request
POST  /api/v1/admin/vendors/{id}/reject-claim/          → Reject with reason
POST  /api/v1/admin/vendors/{id}/approve-location/      → Approve location change
POST  /api/v1/admin/vendors/{id}/reject-location/       → Reject location change
POST  /api/v1/admin/moderation/reels/{id}/approve/      → Approve reel
POST  /api/v1/admin/moderation/reels/{id}/reject/       → Reject with reason/strike
POST  /api/v1/admin/moderation/discounts/{id}/remove/   → Remove fraudulent discount
POST  /api/v1/admin/tags/bulk-assign/                   → Bulk tag assignment
GET   /api/v1/admin/moderation/queue/                   → Moderation queue (reels + claims + reports)
```

---

## 7. PHASE C — VENDOR PORTAL APIs

The Vendor Portal is a **separate web application** with its own login. These APIs power it.

### C-1: Vendor Portal Authentication

**Completely separate from admin auth:**
- Own login page, own JWT flow, own session management
- Endpoint prefix: `/api/v1/vendor-portal/auth/`
- Uses VendorUser model (not AdminUser)
- OTP-based login (phone number)
- Email verification as optional second factor

```
POST /api/v1/vendor-portal/auth/send-otp/
POST /api/v1/vendor-portal/auth/verify-otp/
POST /api/v1/vendor-portal/auth/refresh/
POST /api/v1/vendor-portal/auth/logout/
GET  /api/v1/vendor-portal/auth/me/
```

### C-2: Vendor Portal Profile APIs

```
GET   /api/v1/vendor-portal/profile/                → Full vendor profile
PATCH /api/v1/vendor-portal/profile/                → Update business info
PATCH /api/v1/vendor-portal/profile/hours/          → Update business hours
PATCH /api/v1/vendor-portal/profile/services/       → Update delivery/pickup
POST  /api/v1/vendor-portal/profile/logo/           → Upload logo (presigned URL)
POST  /api/v1/vendor-portal/profile/cover/          → Upload cover photo
POST  /api/v1/vendor-portal/profile/request-location-change/  → Submit GPS change request
GET   /api/v1/vendor-portal/profile/completeness/   → Profile completeness score
```

### C-3: Vendor Portal Dashboard API

```
GET /api/v1/vendor-portal/dashboard/
```

Returns aggregated dashboard data:
- Profile completeness percentage
- Current subscription tier + features
- Active discounts count
- This week's views, taps, navigation clicks
- Reel count vs limit
- Upcoming scheduled discounts
- Voice bot completeness score (if applicable)
- Upgrade prompt data (if Silver/Gold)

### C-4: Landing Page Data API (Public)

```
GET /api/v1/vendor-portal/landing/stats/
```

Returns:
- Total active vendors on platform
- Total cities covered
- Average vendor view increase after claim (calculated)
- Subscription tier overview (names + prices, no sensitive data)
- Featured success stories (curated by admin)

---

## 8. STRIPE SUBSCRIPTION INTEGRATION

### Architecture

```
apps/payments/
├── models.py          # StripeEvent (idempotency log)
├── services.py        # Stripe API wrapper functions
├── webhooks.py        # Stripe webhook handler view
├── serializers.py     # Checkout session creation
├── urls.py            # /api/v1/payments/
└── tasks.py           # Async Stripe operations
```

### Models

```
StripeEvent:
  id(UUID PK), stripe_event_id(CharField unique — idempotency key),
  event_type(CharField), data(JSONField),
  processed(bool default False), created_at

StripeCustomer:
  id(UUID PK), vendor(OneToOne FK Vendor),
  stripe_customer_id(CharField unique),
  created_at, updated_at
```

### Stripe Flow

1. **Checkout:** Vendor selects plan → `POST /api/v1/payments/create-checkout/` → creates Stripe Checkout Session → redirect to Stripe
2. **Success:** Stripe redirects to Vendor Portal success page with `session_id`
3. **Webhook:** Stripe sends events to `POST /api/v1/payments/webhook/`
4. **Events handled:**
   - `checkout.session.completed` → Create VendorSubscription, upgrade vendor tier
   - `invoice.paid` → Update subscription period, log payment
   - `invoice.payment_failed` → Mark subscription PAST_DUE, notify vendor
   - `customer.subscription.updated` → Handle upgrade/downgrade
   - `customer.subscription.deleted` → Downgrade to SILVER, cancel features
5. **Idempotency:** Every webhook checks StripeEvent table — skip if already processed

### Endpoints

```
POST /api/v1/payments/create-checkout/       → Create Stripe Checkout Session
POST /api/v1/payments/create-portal-session/ → Stripe Customer Portal (manage billing)
POST /api/v1/payments/webhook/               → Stripe webhook receiver (no auth)
GET  /api/v1/payments/subscription-status/   → Current subscription status
GET  /api/v1/payments/invoices/              → Invoice history
POST /api/v1/payments/cancel/                → Cancel at period end
POST /api/v1/payments/resume/                → Resume cancelled subscription
```

### Configuration

```python
# .env (keys provided later, architecture ready now)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_SILVER_PRICE_ID=price_...     # Free tier — no Stripe price
STRIPE_GOLD_PRICE_ID=price_...
STRIPE_DIAMOND_PRICE_ID=price_...
STRIPE_PLATINUM_PRICE_ID=price_...
```

---

## 9. SECURITY ARCHITECTURE

### Authentication Matrix

| User Type | Auth Method | Token Storage | Session |
|---|---|---|---|
| Admin | Email + Password | httpOnly cookie | 15min access, 7d refresh |
| Vendor | Phone OTP | httpOnly cookie | 15min access, 30d refresh |
| Customer | Phone OTP | Secure storage (mobile) | 15min access, 30d refresh |

### Data Classification

| Field | Classification | Protection |
|---|---|---|
| Phone numbers | RESTRICTED | AES-256-GCM at rest, masked in API responses |
| Email addresses | CONFIDENTIAL | Encrypted at rest in production |
| GPS coordinates | CONFIDENTIAL | Anonymized in analytics, real in vendor profile |
| Business hours | INTERNAL | Standard DB encryption |
| Stripe keys | RESTRICTED | Environment variables only, never in code |
| JWT tokens | RESTRICTED | httpOnly, Secure, SameSite=Strict |

### API Security Rules

1. All inputs validated server-side (never trust frontend)
2. Phone numbers displayed masked: `*********4567`
3. Rate limiting: 100 req/min per IP (general), 5 req/min for auth endpoints
4. CORS: whitelist specific domains only
5. All admin actions audit-logged with IP
6. Stripe webhooks verified via signature
7. File uploads: max 50MB, allowed types only, virus scan (Phase 2)
8. SQL injection prevention via ORM (never raw SQL without parameterization)

---

## 10. TESTING STRATEGY

### Test Pyramid

```
                    ┌─────────┐
                    │  E2E    │  Playwright (10 admin pages + vendor portal)
                   ┌┴─────────┴┐
                   │Integration │  API tests: auth flows, claim flow, Stripe webhooks
                  ┌┴───────────┴┐
                  │  Unit Tests  │  Services, ranking, NLP parser, feature gating
                 ┌┴─────────────┴┐
                 │   Factories    │  factory_boy for all models
                 └───────────────┘
```

### Test Requirements

| Category | Target | Tools |
|---|---|---|
| Unit tests | ≥ 80% coverage | pytest-django, factory_boy |
| RBAC tests | Every role × every endpoint | Parametrized fixtures |
| Celery tasks | All tasks tested | CELERY_TASK_ALWAYS_EAGER |
| Stripe webhooks | All event types | Mock Stripe payloads |
| OTP flow | Send + verify + rate limit | Mock SMS service |
| Ranking service | Known inputs → expected scores | Pure function tests |
| Voice NLP | Query → expected tags | Parametrized test cases |
| Feature gating | Every tier × every feature | vendor_has_feature() tests |
| S3 operations | Upload, presigned URL | moto mock |
| Encryption | AES-256-GCM round-trip | Direct crypto tests |

### Test Rules

- No tests use real S3, Stripe, Twilio, or external APIs
- All external services mocked via dependency injection
- `CELERY_TASK_ALWAYS_EAGER=True` in test settings
- factory_boy factories for ALL models (existing + new)
- Coverage enforced: `--cov-fail-under=80`

---

## 11. CI/CD & DEPLOYMENT

### CI Pipeline (GitHub Actions)

```
Trigger: push to main, develop, staging; all PRs

Jobs (parallel where possible):
├── lint (flake8 + isort + black)
├── security (bandit + safety + npm audit + TruffleHog)
├── migration-check (makemigrations --check)
├── test (pytest --cov-fail-under=80, all 800+ tests)
├── frontend-lint
├── frontend-build
└── quality-gate (all above must pass)
```

### Deployment Environments

| Environment | Branch | Database | Stripe |
|---|---|---|---|
| Development | `develop` | SQLite (local) / Postgres (Railway) | Test keys |
| Staging | `staging` | PostgreSQL + PostGIS (Railway) | Test keys |
| Production | `main` | PostgreSQL + PostGIS (Railway) | Live keys |

### Environment Variables Required

```
# Database
DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

# Django
SECRET_KEY, ENCRYPTION_KEY, DEBUG, ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS

# JWT
JWT_ACCESS_LIFETIME_MINUTES, JWT_REFRESH_LIFETIME_DAYS

# S3
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME, AWS_S3_REGION_NAME

# Redis / Celery
REDIS_URL, CELERY_BROKER_URL

# Stripe
STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_WEBHOOK_SECRET
STRIPE_GOLD_PRICE_ID, STRIPE_DIAMOND_PRICE_ID, STRIPE_PLATINUM_PRICE_ID

# SMS (Twilio)
TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER

# FCM (Firebase)
FIREBASE_CREDENTIALS_JSON

# Sentry
SENTRY_DSN
```

---

## 12. BUILD SEQUENCE & SESSIONS

### Phase A Stabilization (2 Sessions)

| Session | Goal | Details |
|---|---|---|
| A-S1 | Fix known bugs | Logout 400, analytics hardcodes, governance migration |
| A-S2 | Complete governance + tests | services.py, serializers, views, 80%+ coverage |

### Phase B Build (8 Sessions)

| Session | Apps | Goal |
|---|---|---|
| B-S1 | `customers`, `vendor_auth` | OTP auth for both user types + claim flow |
| B-S2 | `subscriptions` | SubscriptionPackage model + seed + feature gating |
| B-S3 | `payments` | Full Stripe integration + webhooks + checkout |
| B-S4 | `discounts` | Discount model + CRUD + Celery schedulers + tag auto-assign |
| B-S5 | `voicebot` | VoiceBotConfig + rule-based query matching |
| B-S6 | `discovery` | RankingService + search + nearby + voice search NLP |
| B-S7 | `reels`, `notifications` | Reel upload/management + FCM push notifications |
| B-S8 | Analytics + Admin APIs | Vendor analytics (tier-gated) + admin moderation APIs |

### Phase B Gate

- [ ] All Phase B APIs functional and tested
- [ ] Stripe checkout → webhook → tier upgrade working end-to-end
- [ ] OTP auth flow working for both vendor and customer
- [ ] Claim flow: search → claim → verify → approve → activated
- [ ] Feature gating: every tier correctly gates every feature
- [ ] RankingService returns correct scores for known test inputs
- [ ] Voice search parses "cheap pizza near me" correctly
- [ ] All Celery tasks tested (discount scheduler, tag assigner, notifications)
- [ ] Coverage ≥ 80%
- [ ] CI fully green

### Phase C Build (2 Sessions)

| Session | Goal |
|---|---|
| C-S1 | Vendor Portal aggregation APIs (dashboard, profile, completeness) |
| C-S2 | Landing page data API + final integration tests |

---

## 13. QUALITY GATE CHECKLIST

### Every Model

- [ ] UUID PK with `default=uuid.uuid4` (callable)
- [ ] `created_at` (auto_now_add) and `updated_at` (auto_now) where appropriate
- [ ] JSONField defaults as callables (`default=list`, `default=dict`)
- [ ] Soft delete where applicable (never hard delete user-facing data)
- [ ] Appropriate indexes for query patterns
- [ ] factory_boy factory in `tests/factories.py`

### Every View/Endpoint

- [ ] `permission_classes` with `RolePermission.for_roles()` or custom permission
- [ ] No business logic — all delegated to `services.py`
- [ ] `@extend_schema` decorator for OpenAPI docs
- [ ] Returns standard JSON envelope `{success, data, message, errors}`
- [ ] AuditLog entry created for all POST/PATCH/DELETE
- [ ] Input validation in serializer (server-side, never trust frontend)

### Every Service Function

- [ ] Single Responsibility — one domain action per function
- [ ] Calls `log_action()` for mutations
- [ ] Handles errors gracefully with specific exception types
- [ ] Unit tested with factory_boy fixtures

### Security

- [ ] Phone numbers encrypted at rest (AES-256-GCM)
- [ ] Phone numbers masked in API responses (`*********4567`)
- [ ] Stripe webhook signature verified
- [ ] OTP rate-limited (3 per 10 minutes per phone)
- [ ] JWT httpOnly cookies (web) / secure storage (mobile)
- [ ] CORS restricted to known domains
- [ ] No secrets in code — all via environment variables
- [ ] Admin actions audit-logged with IP address

### Infrastructure

- [ ] `docker-compose up` brings full stack
- [ ] Health check returns 503 on DB or cache failure
- [ ] Celery Beat: exactly 1 replica
- [ ] Redis health check in Celery config
- [ ] Sentry configured for error tracking (production)
- [ ] OpenAPI schema at `/api/v1/schema/`

---

## 14. NON-NEGOTIABLE RULES

These rules MUST be followed in every line of code. Violation of any rule blocks merge.

1. **PostGIS `ST_Distance` ONLY** — never `degree × 111000` or any constant
2. **AES-256-GCM** for all phone numbers at rest — encrypt/decrypt in `services.py` only
3. **`for_roles()`** class factory — the ONLY RBAC mechanism for admin endpoints
4. **All business logic in `services.py`** — views are thin wrappers, serializers validate only
5. **AuditLog on every mutation** — POST, PATCH, DELETE must create immutable log entry
6. **Soft deletes only** — `is_deleted=True`, never `Model.objects.delete()`
7. **CSV content never over Celery broker** — pass `batch_id`, read from S3 in task
8. **`vendor_has_feature()`** — the ONLY subscription gate mechanism
9. **Analytics events via Celery** — never block API response to record events
10. **No hardcoded secrets** — all configuration via environment variables
11. **Phone masked in responses** — `*********4567` format always
12. **UUID PKs everywhere** — `default=uuid.uuid4` (callable, not evaluated)
13. **Stripe webhooks idempotent** — check StripeEvent table before processing
14. **OTP rate-limited** — 3 per 10 min per phone, 3 failed verifications → 30 min cooldown
15. **Rule-based NLP only** — no ML models in Phase 1

---

**— End of Backend Master Plan —**
