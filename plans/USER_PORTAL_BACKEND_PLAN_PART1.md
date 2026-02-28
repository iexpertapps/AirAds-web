# USER PORTAL BACKEND PLAN — PART 1
## AirAds User Portal — Django Backend Architecture, Auth, Data Models, Discovery APIs

This plan defines the complete backend architecture required to power the AirAds User Portal — the customer-facing discovery platform — integrated into the existing Django backend at `airaad/backend/`.

---

## TABLE OF CONTENTS (Part 1)

1. [Strategic Context & Integration Philosophy](#1-strategic-context)
2. [New Django Apps Required](#2-new-django-apps)
3. [Authentication System — Customer Auth](#3-authentication-system)
4. [Database Design — All New Models](#4-database-design)
5. [Discovery Engine — Ranking Algorithm](#5-discovery-engine)
6. [API Namespace Structure](#6-api-namespace)
7. [Core API Modules — Discovery & Search](#7-core-api-modules)

> **Part 2 covers:** AR Data Serving, Voice Search Backend, Promotions Engine, Vendor Profile APIs, User Preferences, Analytics/Tracking, Performance & Caching, Security, Celery Tasks, Scaling Plan, Build Sequence, QA Checklist.

---

## 1. STRATEGIC CONTEXT & INTEGRATION PHILOSOPHY

### What This Is
The User Portal backend serves **end customers** — people who discover nearby vendors via AR, voice, map, and tag browsing. It is a **separate concern** from the Vendor Portal APIs (which serve vendors managing their listings) and Admin Portal APIs (which serve internal operations teams).

### Integration Approach: Extend Existing Backend
- **Location:** All new code lives inside `airaad/backend/` — same Django project
- **New URL namespace:** All User Portal APIs served under `/api/v1/user-portal/`
- **Existing apps reused (read-only consumer):** `vendors`, `tags`, `geo`, `subscriptions`, `analytics`, `reels`, `notifications`
- **New apps created:** `customer_auth`, `user_portal` (aggregation layer), `user_preferences`
- **Never modify existing Vendor Portal or Admin Portal views** — User Portal has its own views, serializers, and service layer

### Core Design Mandate
> "User ko 10 seconds ke andar relevant vendor milna chahiye app open karne ke baad."

Every API response must be optimized for sub-200ms latency at the discovery layer. Caching and query optimization are non-negotiable.

### Ranking Formula (Backend Must Implement Exactly)
```
Final Score = (Relevance × 0.30) + (Distance × 0.25) + (Active Offer × 0.15) + (Popularity × 0.15) + (Subscription Tier × 0.15)
```
- **Relevance:** Tag match score between user intent and vendor tags
- **Distance:** Inverse of distance (closer = higher score), PostGIS ST_Distance
- **Active Offer:** Binary 1.0 if active promotion/happy hour right now, else 0.0
- **Popularity:** Normalized navigation_clicks + profile_views in last 30 days
- **Subscription Tier:** Silver=0.25, Gold=0.50, Diamond=0.75, Platinum=1.00 (normalized 0–1 score contributing exactly 15% — NOT a global multiplier)
- **System Tags (Invisible Boost):** `new_vendor_boost` (+0.10 to final_score for first 30 days), `trending` (+0.05), `verified` (+0.03) — not visible to users, added post-scoring before sort

---

## 2. NEW DJANGO APPS REQUIRED

### App Map

| App | Purpose | Location |
|---|---|---|
| `customer_auth` | Customer registration, login (email+password + OTP), JWT tokens, guest sessions | `apps/customer_auth/` |
| `user_portal` | Aggregation layer — discovery APIs, vendor detail, deals feed, reels feed | `apps/user_portal/` |
| `user_preferences` | Per-user settings: radius, default view, category preferences, notification prefs | `apps/user_preferences/` |

### What Each App Owns

**`customer_auth`:**
- `CustomerUser` model (OneToOne to Django User)
- Registration, email verification, password reset flows
- JWT token issue/refresh/blacklist (same `djangorestframework-simplejwt` library)
- Guest session token generation (anonymous, non-persistent)
- Google OAuth integration (optional Phase-2, placeholder in plan)
- OTP fallback (phone-based, optional, for mobile)

**`user_portal`:**
- No models of its own — purely a service + view layer
- Discovery view: ranked nearby vendor list
- AR data endpoint: markers for AR overlay
- Map pins endpoint: map view data
- Deals feed endpoint: active promotions nearby
- Reels feed endpoint: nearby vendor reels (TikTok-style)
- Vendor profile detail endpoint (read-only, customer perspective)
- Voice search query processing endpoint
- Tag browser endpoint (categories + counts)
- Flash deal alert check endpoint
- Navigation click tracking endpoint

**`user_preferences`:**
- `UserPreference` model linked to `CustomerUser`
- `GuestPreference` model stored by guest_token (server-side, expires in 30 days)
- Search radius, default view, preferred categories
- Notification preferences per type
- Theme preference (dark/light/system)
- Behavioral data: search history, recent vendors viewed

---

## 3. AUTHENTICATION SYSTEM — CUSTOMER AUTH

### Design Principle
> "No signup needed to explore" — this is the brand promise. Authentication is optional and never blocks discovery.

### Auth Modes

**Mode 1: Guest Mode (Default)**
- No login required
- Backend issues a `guest_token` (UUID, 30-day TTL) on first API call
- `guest_token` stored client-side in `localStorage` / `flutter_secure_storage`
- Preferences stored server-side against `guest_token` (UserPreference with `user=null`)
- Guest tokens expire and are purged by Celery beat task

**Mode 2: Registered User (Email + Password)**
- Standard Django User + CustomerUser profile
- JWT access token (15-minute TTL) + refresh token (7-day TTL)
- Email verification required before full account access
- On login: any existing `guest_token` preferences migrated to the user account
  > **[AUDIT FIX — MEDIUM 2.8]** Guest preference migration is non-trivial. Strategy:
  > 1. Login request includes `guest_token` field (optional)
  > 2. `AuthService.login()` checks for existing `UserPreference` with that `guest_token`
  > 3. If found AND user has no prior preference: copy guest prefs to user account
  > 4. If user already has preferences: merge (take non-default guest values only)
  > 5. Nullify `guest_token` on the migrated `UserPreference` row after merge
  > 6. `FlashDealAlert` records with `guest_token` are also reassigned to `user`
- Password reset via email link

**Mode 3: Google OAuth (Phase-2 placeholder)**
- Architecture reserved; not built in Phase-1
- `social_auth_provider` field on CustomerUser for future

### API Endpoints — Authentication

| Method | URL | Purpose | Auth Required |
|---|---|---|---|
| POST | `/api/v1/user-portal/auth/guest/` | Issue guest token | None |
| POST | `/api/v1/user-portal/auth/register/` | Create account | None |
| POST | `/api/v1/user-portal/auth/verify-email/` | Confirm email link | None |
| POST | `/api/v1/user-portal/auth/login/` | Email+password login | None |
| POST | `/api/v1/user-portal/auth/token/refresh/` | Refresh JWT | Refresh token |
| POST | `/api/v1/user-portal/auth/logout/` | Blacklist token | Access token |
| POST | `/api/v1/user-portal/auth/password-reset/` | Request password reset | None |
| POST | `/api/v1/user-portal/auth/password-reset/confirm/` | Set new password | None |
| DELETE | `/api/v1/user-portal/auth/account/` | Delete account + data (GDPR) | Access token |
| GET | `/api/v1/user-portal/auth/me/` | Current user profile | Access token |
| GET | `/api/v1/user-portal/auth/account/export/` | Export all user data | Access token |

### JWT Strategy
- Same `djangorestframework-simplejwt` library as Admin/Vendor Portal
- **Separate token audience claim:** `"aud": "user-portal"` — tokens NOT cross-compatible with admin or vendor tokens
- Custom `CustomerUserAuthentication` class that validates audience
- Guest requests: header `X-Guest-Token: <uuid>` — parsed by custom middleware

### CustomerUser Model Fields

```
CustomerUser
├── user (OneToOneField → Django User) — email, password, is_active
├── display_name (CharField, max 50, optional)
├── avatar_url (URLField, optional)
├── phone_number (EncryptedCharField, optional — AES-256-GCM, same as vendor)
├── guest_token (UUIDField, nullable — tracks pre-login session)
├── preferred_radius_m (IntegerField, default=500)
├── preferred_categories (JSONField, default=[])
├── last_known_lat (DecimalField, nullable)
├── last_known_lng (DecimalField, nullable)
├── behavioral_data (JSONField, default={}) — local implicit learning
├── notification_enabled (BooleanField, default=True)
├── data_export_requested_at (DateTimeField, nullable)
├── created_at, updated_at, is_deleted (soft delete)
```

---

## 4. DATABASE DESIGN — ALL NEW MODELS

### 4.1 UserPreference Model

```
UserPreference
├── user (ForeignKey → CustomerUser, nullable — for guest preferences)
├── guest_token (UUIDField, nullable — for guest mode)
├── default_view (CharField: 'AR' | 'MAP' | 'LIST', default='AR')
├── search_radius_m (IntegerField, default=500, max=5000)
├── show_open_now_only (BooleanField, default=False)
├── preferred_category_slugs (JSONField, default=[])
├── price_range (CharField: 'BUDGET' | 'MID' | 'PREMIUM', default='MID')
├── theme (CharField: 'DARK' | 'LIGHT' | 'SYSTEM', default='DARK')
├── notifications_nearby_deals (BooleanField, default=True)
├── notifications_flash_deals (BooleanField, default=True)
├── notifications_new_vendors (BooleanField, default=True)
├── notifications_all_off (BooleanField, default=False)
├── updated_at (DateTimeField, auto_now=True)
```

### 4.2 UserSearchHistory Model

```
UserSearchHistory
├── user (ForeignKey → CustomerUser, nullable)
├── guest_token (UUIDField, nullable)
├── query_text (CharField, max=200)
├── query_type (CharField: 'TEXT' | 'VOICE' | 'TAG')
├── extracted_category (CharField, nullable)
├── extracted_intent (CharField, nullable)
├── result_count (IntegerField)
├── navigated_to_vendor_id (UUIDField, nullable — FK to Vendor)
├── searched_at (DateTimeField, auto_now_add=True)
```
Index: `(user, searched_at)` — for history retrieval. Purged after 90 days (Celery task).

### 4.3 UserVendorInteraction Model

```
UserVendorInteraction
├── user (ForeignKey → CustomerUser, nullable)
├── guest_token (UUIDField, nullable)
├── vendor_id (UUIDField — not FK, denormalized for performance)
├── interaction_type (CharField: 'VIEW' | 'TAP' | 'NAVIGATION' | 'CALL' | 'REEL_VIEW' | 'PROMOTION_TAP' | 'ARRIVAL')
├── session_id (UUIDField — groups interactions in one session)
├── lat (DecimalField, nullable — user location at time of interaction)
├── lng (DecimalField, nullable)
├── interacted_at (DateTimeField, auto_now_add=True)
```
Index: `(vendor_id, interaction_type, interacted_at)` — for vendor analytics aggregation.
Partitioned by month (PostgreSQL range partitioning in production).

### 4.4 FlashDealAlert Model

```
FlashDealAlert
├── user (ForeignKey → CustomerUser, nullable)
├── guest_token (UUIDField, nullable)
├── discount_id (UUIDField)
├── alerted_at (DateTimeField, auto_now_add=True)
├── dismissed (BooleanField, default=False)
```
Purpose: Prevent re-alerting same user for same flash deal.

### 4.5 NearbyReelView Model

```
NearbyReelView
├── reel_id (UUIDField)
├── user (ForeignKey → CustomerUser, nullable)
├── guest_token (UUIDField, nullable)
├── watched_seconds (IntegerField)
├── completed (BooleanField)
├── cta_tapped (BooleanField, default=False)
├── viewed_at (DateTimeField, auto_now_add=True)
```

### 4.6 Database Indexes (Critical for Performance)

```sql
-- Discovery query optimization
CREATE INDEX idx_vendor_location ON vendors_vendor USING GIST(location);
CREATE INDEX idx_vendor_active ON vendors_vendor(is_deleted, is_active) WHERE is_deleted=false AND is_active=true;
CREATE INDEX idx_discount_active ON discounts_discount(vendor_id, starts_at, ends_at) WHERE is_deleted=false;
CREATE INDEX idx_interaction_vendor ON user_portal_uservendorinteraction(vendor_id, interacted_at);
CREATE INDEX idx_searchhistory_user ON user_portal_usersearchhistory(user_id, searched_at);
```

---

## 5. DISCOVERY ENGINE — RANKING ALGORITHM

### Architecture
The discovery engine lives in `apps/user_portal/services/discovery_service.py`. It is the most performance-critical piece of the entire User Portal backend.

### Query Pipeline

```
Step 1: Spatial Filter
  → PostGIS ST_DWithin(vendor.location, user_point, radius_meters)
  → Only active, non-deleted vendors
  → Result: candidate set (typically 50-200 vendors)

Step 2: Business Hours Filter (optional, if show_open_now_only=True)
  → Parse vendor.business_hours JSON
  → Check current day + time against hours
  → Filter out closed vendors

Step 3: Tag Filter (if tags provided)
  → vendors.tags__slug IN [requested_tags]
  → AND logic for multi-tag selection

Step 4: Scoring (Python-level, after DB fetch)
  For each candidate vendor:
    distance_score = 1 - (distance_m / max_distance_m)  → 0.0 to 1.0
    relevance_score = tag_overlap_ratio(vendor.tags, query_tags)  → 0.0 to 1.0
    active_offer_score = 1.0 if has_active_promotion() else 0.0
    popularity_score = normalize(navigation_clicks_30d + profile_views_30d)
    # [AUDIT FIX — CRITICAL] Tier contributes exactly 15% as per UP-0 formula.
    # It is NOT a global multiplier. Previous version applied tier twice (once in score,
    # once as multiplier) — that caused Platinum vendors to unfairly dominate discovery.
    tier_score = {SILVER: 0.25, GOLD: 0.50, DIAMOND: 0.75, PLATINUM: 1.00}[subscription_tier]
    # ^ Normalized 0-1: Silver=base, Platinum=full — proportional contribution only

    final_score = (
        relevance_score   * 0.30 +
        distance_score    * 0.25 +
        active_offer_score * 0.15 +
        popularity_score  * 0.15 +
        tier_score        * 0.15   # 15% — spec-exact, no separate multiplier
    )

Step 5: Apply system tag boosts (post-scoring, before sort):
  # System tags are invisible to users — they boost final_score only
  # [AUDIT FIX — MEDIUM 2.5] Document this clearly: system tags must fire AFTER the weighted formula
  if 'new_vendor_boost' in vendor.system_tags:  final_score += 0.10  # first 30 days
  if 'trending'         in vendor.system_tags:  final_score += 0.05
  if 'verified'         in vendor.system_tags:  final_score += 0.03
  # Cap at 1.0 to prevent score overflow
  final_score = min(final_score, 1.0)

Step 6: Sort by final_score DESC, limit to requested page size

Step 7: Serialize + cache result (Redis, TTL 60 seconds per location cell)
```

### Location Cell Caching Strategy
- Divide map into ~500m × 500m grid cells (geohash precision-5)
- Cache discovery results per `(geohash_cell, tag_filter_hash, radius)` key
- TTL: 60 seconds (promotions are time-sensitive)
- Invalidation: When a vendor in that cell updates, or a promotion starts/ends

### Popularity Score Calculation
- Updated every 15 minutes by a Celery task: `update_vendor_popularity_scores`
- Stored on `Vendor.popularity_score` (Float field — add to existing model)
- Formula: `log(1 + navigation_clicks_30d) + log(1 + profile_views_30d)` — log scale prevents viral outliers from dominating

---

## 6. API NAMESPACE STRUCTURE

All User Portal APIs under `/api/v1/user-portal/` in `config/urls.py`.

```
/api/v1/user-portal/
│
├── auth/                          ← customer_auth.urls
│   ├── guest/
│   ├── register/
│   ├── verify-email/
│   ├── login/
│   ├── logout/
│   ├── token/refresh/
│   ├── password-reset/
│   ├── password-reset/confirm/
│   ├── me/
│   └── account/  (GET=export, DELETE=delete)
│
├── discovery/                     ← user_portal.urls
│   ├── nearby/                    ← Main ranked vendor list
│   ├── nearby/ar-markers/         ← Lightweight AR overlay data
│   ├── nearby/map-pins/           ← Map pin data
│   ├── nearby/reels/              ← Reels feed
│   ├── search/                    ← Text search
│   ├── voice-search/              ← Voice query processing
│   ├── tags/                      ← Tag browser + counts
│   ├── flash-alert/               ← Flash deal proximity check (alert for NEW flash deals)
│   ├── promotions-strip/          ← [AUDIT FIX 1.7] All active promotions nearby (strip display)
│   └── cities/                    ← [AUDIT FIX 1.8] City + area list for manual location picker
│
├── vendors/                       ← Vendor detail (read-only)
│   ├── <vendor_id>/               ← Full vendor profile
│   ├── <vendor_id>/reels/         ← Vendor's reels
│   ├── <vendor_id>/voice-bot/     ← Voice bot query
│   └── <vendor_id>/nearby/        ← Similar vendors nearby
│
├── deals/                         ← Active promotions
│   ├── nearby/                    ← All active deals near user
│   └── <discount_id>/             ← Deal detail
│
├── preferences/                   ← user_preferences.urls
│   ├── GET/PUT /                  ← Read + update preferences
│   └── search-history/
│       ├── GET /                  ← User's search history
│       └── DELETE /               ← Clear history
│
├── track/                         ← Analytics tracking (fire-and-forget)
│   ├── interaction/               ← POST vendor interaction event
│   └── reel-view/                 ← POST reel view event
│
└── auth/consent/                  ← [AUDIT FIX 3.10] POST GDPR consent recording
```

---

## 7. CORE API MODULES — DISCOVERY & SEARCH

### 7.1 Nearby Vendors API

**`GET /api/v1/user-portal/discovery/nearby/`**

Query Parameters:
```
lat          float   required  — User latitude
lng          float   required  — User longitude
radius_m     int     optional  — default 500, max 5000
tags         string  optional  — comma-separated tag slugs
open_now     bool    optional  — filter to currently open vendors
sort         string  optional  — 'relevance' (default) | 'distance' | 'deals'
page         int     optional  — default 1
page_size    int     optional  — default 20, max 50
```

Response Shape:
```json
{
  "count": 23,
  "next": "/api/v1/user-portal/discovery/nearby/?page=2",
  "results": [
    {
      "id": "uuid",
      "name": "Raja Burgers",
      "slug": "raja-burgers-lahore",
      "category_tag": {"slug": "food", "label": "Food", "emoji": "🍔"},
      "subscription_tier": "GOLD",
      "distance_m": 120,
      "bearing_deg": 45.2,
      "location": {"lat": 31.5, "lng": 74.3},
      "is_open_now": true,
      "active_promotion": {
        "type": "PERCENTAGE",
        "value": 20,
        "label": "20% OFF",
        "ends_at": "2026-02-27T15:00:00Z",
        "urgent": true
      },
      "voice_bot_available": true,
      "thumbnail_url": "https://...",
      "relevance_score": 0.87,
      "popularity_score": 0.63
    }
  ]
}
```

Performance target: **< 150ms** (with Redis cache hit), **< 400ms** (cache miss, PostGIS query).

### 7.2 AR Markers API

**`GET /api/v1/user-portal/discovery/nearby/ar-markers/`**

Purpose: Lightweight endpoint specifically for AR overlay — minimal payload, maximum speed.

Same query params as nearby endpoint. Returns only fields needed for AR rendering:

```json
{
  "markers": [
    {
      "id": "uuid",
      "name": "Raja Burgers",
      "distance_m": 120,
      "bearing_deg": 45.2,
      "tier": "GOLD",
      "has_promotion": true,
      "promotion_label": "20% OFF",
      "promotion_urgent": true,
      "category_emoji": "🍔",
      "voice_bot": false
    }
  ],
  "user_location": {"lat": 31.5, "lng": 74.3},
  "generated_at": "2026-02-27T10:00:00Z"
}
```

Performance target: **< 80ms** (cached). This endpoint is polled every 3-5 seconds by the AR view.

### 7.3 Map Pins API

**`GET /api/v1/user-portal/discovery/nearby/map-pins/`**

Returns minimal data for rendering map pins — GeoJSON format for Mapbox compatibility:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [74.3, 31.5]},
      "properties": {
        "id": "uuid",
        "name": "Raja Burgers",
        "tier": "GOLD",
        "has_active_promotion": true,
        "category_slug": "food",
        "distance_m": 120,
        "pin_color": "#FFC107"
      }
    }
  ]
}
```

Pin color rules:
- Silver: `#9E9E9E`
- Gold: `#FFC107`
- Diamond: `#00BCD4` (teal)
- Platinum: gradient (client renders this — API provides `"PLATINUM"` tier string)

### 7.4 Text Search API

**`GET /api/v1/user-portal/discovery/search/`**

Query Parameters:
```
q        string  required  — search query (min 2 chars)
lat      float   required
lng      float   required
radius_m int     optional  — default 2000 for text search (wider radius)
```

Backend Implementation:
1. Normalize query (lowercase, strip, transliterate)
2. Django ORM: `Q(name__icontains=q) | Q(tags__name__icontains=q) | Q(description__icontains=q)`
3. PostGIS distance filter applied
4. Same ranking algorithm as nearby endpoint
5. Cache: **no caching** for search (too many unique queries) — query must be fast on its own

Performance target: **< 300ms** (no cache, real DB query with indexes).

### 7.5 Voice Search Processing API

**`POST /api/v1/user-portal/discovery/voice-search/`**

Request Body:
```json
{
  "transcript": "cheap pizza near me",
  "lat": 31.5,
  "lng": 74.3,
  "language": "en"
}
```

Backend NLP Processing (rule-based, no external ML service in Phase-1):

```
Intent Classification (keyword-based rules):
  Category extraction:
    "pizza" → tag_slug: "pizza"
    "burger" → tag_slug: "burgers"
    "coffee" | "cafe" → tag_slug: "cafe"
    "salon" | "haircut" → tag_slug: "salon"
    [... full keyword map for all 50+ category tags ...]

  Price intent extraction:
    "cheap" | "budget" | "affordable" → intent_tag: "budget-friendly"
    "under 300" | "under 500" → price_max: 300/500
    "expensive" | "premium" → intent_tag: "premium"

  Time intent extraction:
    "now" | "open" | "right now" → filter: open_now=True
    "late night" → intent_tag: "late-night"
    "breakfast" → intent_tag: "breakfast"
    "lunch" → intent_tag: "lunch"

  Action intent extraction:
    "take me to" | "directions to" | "navigate to" → action: NAVIGATE
    "show" | "find" | "what's" → action: DISCOVER
```

Response:
```json
{
  "understood_as": "cheap pizza near me",
  "extracted": {
    "category": "pizza",
    "intent_tags": ["budget-friendly"],
    "open_now": false,
    "action": "DISCOVER"
  },
  "voice_response": "I found 3 pizza places near you. Pizza Hub is 120m away with 20% off. Would you like directions?",
  "results": [],
  "suggested_queries": ["cheap biryani near me", "open cafe right now"]
}
```

### 7.6 Tag Browser API

**`GET /api/v1/user-portal/discovery/tags/`**

Query Parameters: `lat`, `lng`, `radius_m`

Response:
```json
{
  "hot_right_now": [
    {"slug": "pizza", "label": "Pizza", "emoji": "🍕", "active_deal_count": 12}
  ],
  "by_intent": [
    {"slug": "quick-bite", "label": "Quick Bite", "emoji": "🍔", "vendor_count": 45},
    {"slug": "open-now", "label": "Open Now", "emoji": "🟢", "vendor_count": 23},
    {"slug": "budget-friendly", "label": "Budget Friendly", "emoji": "💰", "vendor_count": 31}
  ],
  "by_category": [
    {"slug": "food", "label": "Food", "emoji": "🍽️", "vendor_count": 89}
  ],
  "by_distance": [
    {"label": "Walking (under 5 min)", "radius_m": 400, "vendor_count": 12},
    {"label": "Nearby (under 10 min)", "radius_m": 800, "vendor_count": 34},
    {"label": "In my area", "radius_m": 2000, "vendor_count": 89}
  ]
}
```

Caching: Results cached per geohash cell, TTL 120 seconds.

### 7.7 Flash Deal Alert API

**`GET /api/v1/user-portal/discovery/flash-alert/`**

Query Parameters: `lat`, `lng`, `radius_m=200`
Auth: Guest token or JWT

Purpose: Client polls this every 60 seconds to check for new flash deals.

Response:
```json
{
  "flash_deal": {
    "discount_id": "uuid",
    "vendor_name": "Mario's Pizza",
    "distance_m": 150,
    "label": "Flash Deal: 30% OFF",
    "started_at": "2026-02-27T10:00:00Z",
    "ends_at": "2026-02-27T11:00:00Z"
  }
}
```
Returns `{"flash_deal": null}` if no un-alerted flash deal within radius.
After returning, creates `FlashDealAlert` record to prevent re-alerting.

---

*Continues in USER_PORTAL_BACKEND_PLAN_PART2.md*
