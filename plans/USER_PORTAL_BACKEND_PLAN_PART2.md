# USER PORTAL BACKEND PLAN — PART 2
## AirAds User Portal — Vendor Profile, Promotions, Voice Bot, Preferences, Analytics, Performance, Security, Build Sequence

This is Part 2 of the User Portal Backend Plan. Part 1 covered: Strategic Context, New Apps, Auth System, Database Design, Discovery Engine, API Namespace, Core Discovery APIs.

---

## TABLE OF CONTENTS (Part 2)

8. [Vendor Profile APIs](#8-vendor-profile-apis)
9. [Promotions & Deals Engine](#9-promotions--deals-engine)
10. [Voice Bot Integration — Customer Side](#10-voice-bot-integration)
11. [Reels Feed API](#11-reels-feed-api)
12. [Navigation Integration](#12-navigation-integration)
13. [User Preferences APIs](#13-user-preferences-apis)
14. [Analytics & Behavioral Tracking](#14-analytics--behavioral-tracking)
15. [Performance & Caching Architecture](#15-performance--caching-architecture)
16. [Security Architecture](#16-security-architecture)
17. [Celery Tasks — User Portal](#17-celery-tasks)
18. [Scaling Plan](#18-scaling-plan)
19. [Build Sequence & Sessions](#19-build-sequence--sessions)
20. [Quality Gate Checklist](#20-quality-gate-checklist)

---

## 8. VENDOR PROFILE APIs

### 8.1 Vendor Detail — Full Profile

**`GET /api/v1/user-portal/vendors/<vendor_id>/`**

This endpoint returns everything needed to render the full vendor profile screen. It is read-only — no modification allowed from the User Portal.

Response Shape:
```json
{
  "id": "uuid",
  "name": "Raja Burgers",
  "slug": "raja-burgers-lahore",
  "description": "Best burgers in Gulberg since 2010.",
  "subscription_tier": "GOLD",
  "tier_badge": {
    "label": "Verified",
    "icon": "verified",
    "color": "#00BCD4"
  },
  "category_tags": [
    {"slug": "food", "label": "Food", "emoji": "🍔"}
  ],
  "intent_tags": ["budget-friendly", "quick-bite"],
  "location": {
    "lat": 31.5204,
    "lng": 74.3587,
    "area_name": "Gulberg III",
    "city_name": "Lahore",
    "address_line": "23 MM Alam Road, Gulberg"
  },
  "distance_m": 120,
  "bearing_deg": 45.2,
  "is_open_now": true,
  "business_hours": {
    "monday": {"open": "09:00", "close": "23:00"},
    "tuesday": {"open": "09:00", "close": "23:00"},
    "wednesday": null,
    "thursday": {"open": "09:00", "close": "23:00"},
    "friday": {"open": "09:00", "close": "00:00"},
    "saturday": {"open": "10:00", "close": "00:00"},
    "sunday": {"open": "10:00", "close": "22:00"}
  },
  "today_hours": "09:00 – 23:00",
  "phone_number": "+92-XXX-XXXXXXX",
  "website_url": null,
  "cover_media_url": "https://...",
  "logo_url": "https://...",
  "active_promotion": {
    "id": "uuid",
    "type": "PERCENTAGE",
    "value": 20,
    "label": "20% OFF",
    "description": "On all burgers",
    "starts_at": "2026-02-27T12:00:00Z",
    "ends_at": "2026-02-27T15:00:00Z",
    "countdown_seconds": 3600,
    "urgent": false
  },
  "voice_bot": {
    "available": true,
    "tier": "BASIC",
    "intro_message": "Welcome to Raja Burgers! How can I help you?"
  },
  "stats": {
    "navigation_clicks": 1240,
    "profile_views_30d": 3400
  },
  "delivery_available": false,
  "pickup_available": true,
  "reels_count": 3,
  "navigation": {
    "google_maps_app": "comgooglemaps://?daddr=31.5204,74.3587&directionsmode=walking",
    "google_maps_web": "https://www.google.com/maps/dir/?api=1&destination=31.5204,74.3587",
    "apple_maps": "maps://?daddr=31.5204,74.3587&dirflg=w"
  }
}
```

**Performance target:** < 200ms (vendor detail cached per vendor_id, TTL 5 minutes — invalidated on vendor update).

### 8.2 Vendor Reels

**`GET /api/v1/user-portal/vendors/<vendor_id>/reels/`**

Returns active reels for the vendor (ordered by recency, limited to tier max):
- Silver: up to 1 reel
- Gold: up to 3 reels
- Diamond: up to 6 reels
- Platinum: unlimited

```json
{
  "reels": [
    {
      "id": "uuid",
      "video_url": "https://...",
      "thumbnail_url": "https://...",
      "duration_seconds": 9,
      "cta_label": "Get Directions",
      "cta_action": "NAVIGATE",
      "has_promotion": true,
      "promotion_label": "20% OFF",
      "view_count": 450,
      "created_at": "2026-02-20T10:00:00Z"
    }
  ]
}
```

### 8.3 Vendor Voice Bot Query

**`POST /api/v1/user-portal/vendors/<vendor_id>/voice-bot/`**

Available only if vendor has Gold/Diamond/Platinum subscription.

Request:
```json
{
  "query": "Are you open on Sunday?",
  "session_id": "uuid"
}
```

Backend Logic:
1. Check vendor has voice bot configured and active
2. Load VoiceBotConfig for vendor
3. Rule-based response matching (NLP keyword system):
   - Hours queries → return business_hours data
   - Menu queries → return menu_items from VoiceBotConfig
   - Delivery queries → return delivery/pickup config
   - Price queries → return price range tags
   - Promotion queries → return active_promotion data
4. Diamond/Platinum: dynamic responses using live data
5. Gold: static pre-recorded responses only
6. Log query in AnalyticsEvent for vendor dashboard

Response:
```json
{
  "response_text": "Yes, we're open on Sundays from 10:00 AM to 10:00 PM!",
  "response_audio_available": false,
  "source": "hours",
  "vendor_name": "Raja Burgers",
  "follow_up_suggestions": [
    "What's the lunch special?",
    "Do you offer delivery?"
  ]
}
```

**Tier gating:**
- Silver: returns `{"available": false}` with 403 status
- Gold: static responses only
- Diamond/Platinum: dynamic, live-data responses

### 8.4 Similar Vendors Nearby

**`GET /api/v1/user-portal/vendors/<vendor_id>/nearby/`**

Returns vendors in same category, within 1km, excluding the current vendor:
```
Query params: lat, lng (required)
Limit: 6 vendors max (for "More Nearby" horizontal scroll)
Same serializer shape as nearby endpoint (compact version)
```

---

## 9. PROMOTIONS & DEALS ENGINE

### 9.1 Active Deals Nearby

**`GET /api/v1/user-portal/deals/nearby/`**

Query Parameters:
```
lat, lng          required
radius_m          optional, default 2000 (deals view uses wider radius than discovery)
category          optional — filter by category slug
sort              optional — 'ending_soon' (default) | 'closest' | 'best_value'
page, page_size   optional
```

Backend Logic:
1. PostGIS query: vendors within radius
2. Join with Discount table: `now() BETWEEN starts_at AND ends_at`
3. Filter: `discount.is_deleted = false AND discount.is_active = true`
4. For each active discount, compute:
   - `remaining_seconds` = ends_at − now()
   - `urgency_level` = 'HIGH' if < 3600s, 'MEDIUM' if < 7200s, 'NORMAL' otherwise
5. Sort by chosen option
6. Return deal cards

Response Shape (per deal card):
```json
{
  "discount_id": "uuid",
  "vendor": {
    "id": "uuid",
    "name": "Mario's Pizza",
    "category_emoji": "🍕",
    "distance_m": 300,
    "is_open_now": true,
    "tier": "DIAMOND",
    "location": {"lat": 31.52, "lng": 74.36}
  },
  "promotion": {
    "type": "PERCENTAGE",
    "value": 30,
    "label": "30% OFF",
    "description": "All pizzas, dine-in only",
    "ends_at": "2026-02-27T15:00:00Z",
    "remaining_seconds": 5400,
    "urgency_level": "MEDIUM",
    "is_flash_deal": false,
    "is_happy_hour": true
  }
}
```

### 9.2 Deal Detail

**`GET /api/v1/user-portal/deals/<discount_id>/`**

Full deal information including vendor profile summary. Used when user taps a deal card to see full detail.

### 9.3 Real-Time Promotion Status

Promotions are time-sensitive. Backend does NOT serve stale data:
- `starts_at` and `ends_at` stored in UTC (Django timezone-aware datetimes)
- `active_promotion` field on vendor serializer computed dynamically at query time — never cached beyond 60 seconds
- Celery beat task `expire_promotions` runs every 5 minutes — marks ended discounts as `is_active=False` (belt-and-suspenders; primary source of truth is always `now() BETWEEN starts_at AND ends_at`)

### 9.4 Flash Deal Logic

Flash deals are a subset of discounts with `is_flash_deal=True`. They have special handling:
- Shorter duration (typically 1-2 hours)
- Platinum vendors only (Smart Automation tier)
- Trigger push notification via `apps/notifications/` — Firebase FCM
- `FlashDealAlert` table prevents duplicate alerts to same user
- Flash deal alert check endpoint (`/discovery/flash-alert/`) polled by client every 60s

> **[AUDIT FIX — HIGH 1.18]** Flash alert endpoint must filter to flash deals that started within the last 90 minutes only (`started_at >= now() - interval '90 minutes'`). Without this filter, a user walking past a vendor gets alerted about a 6-hour-old flash deal, degrading trust. Add `started_within_minutes=90` filter to the query in `FlashDealAlertView`.

### 9.5 Active Promotions Strip API (Distinct from Flash Alert)

> **[AUDIT FIX — HIGH 1.7]** The Promotions Strip in Discovery Home (UP-4) shows ALL active promotions nearby — not just new flash deals. The existing `/discovery/flash-alert/` endpoint only returns newly-started flash deals. A dedicated endpoint is required for the promotions strip.

**`GET /api/v1/user-portal/discovery/promotions-strip/`**

Query Parameters: `lat`, `lng`, `radius_m=500`

Backend Logic:
1. PostGIS: vendors within radius with `has_active_promotion=True`
2. Filter: `now() BETWEEN discount.starts_at AND discount.ends_at`
3. Order by: `ends_at ASC` (ending soonest first — creates urgency)
4. Limit: max 10 results
5. Cache: TTL 30 seconds (promotions-strip-specific key `up:promo_strip:{geohash}`)

Response:
```json
{
  "promotions": [
    {
      "vendor_id": "uuid",
      "vendor_name": "Raja Burgers",
      "distance_m": 120,
      "label": "20% OFF",
      "emoji": "🔥",
      "ends_at": "2026-02-27T15:00:00Z",
      "walk_minutes": 2
    }
  ]
}
```
Returns `{"promotions": []}` when no active promotions nearby (client auto-hides the strip).
Add URL: `/api/v1/user-portal/discovery/promotions-strip/` to `user_portal/urls.py`.

---

## 10. VOICE BOT INTEGRATION — CUSTOMER SIDE

### 10.1 Global Voice Search (Discovery-Level)

Already covered in Section 7.5 of Part 1 (`/api/v1/user-portal/discovery/voice-search/`).

Backend NLP is **rule-based keyword matching** — no external ML API dependency in Phase-1. This keeps the system:
- Fast (< 50ms processing time)
- Cost-free (no per-query charges)
- Resilient (no external API failure risk)

### 10.2 Keyword Map — Complete Coverage

The keyword-to-intent mapping is stored in `apps/user_portal/nlp/keyword_map.py`.

Categories covered (50+ entries): pizza, burger, biryani, cafe/coffee, salon/barber, grocery/kiryana, pharmacy, electronics, clothing, restaurant, bakery, sweets, juice, fast-food, Chinese, desi, BBQ, shawarma, gym, laundry, repair, auto, school, hospital, hotel, and all other common local business types.

Price intents: budget-friendly, mid-range, premium.
Time intents: open-now, late-night, breakfast, lunch, dinner.
Action intents: NAVIGATE, CALL, DISCOVER.

### 10.3 Vendor Voice Bot — Tier-Based Behavior

| Feature | Silver | Gold | Diamond | Platinum |
|---|---|---|---|---|
| Voice bot available | ❌ | ✅ Basic | ✅ Dynamic | ✅ Advanced |
| Response type | — | Static pre-configured | Live data-driven | Live + predictive |
| Query types supported | — | Hours, Basic FAQ | All query types | All + context-aware |
| Response audio (TTS) | — | No | Via client SpeechSynthesis | Via client SpeechSynthesis |
| Query logging | — | Aggregate only | Full logging | Full + analytics |

---

## 11. REELS FEED API

### 11.1 Nearby Reels Feed

**`GET /api/v1/user-portal/discovery/nearby/reels/`**

TikTok-style vertical feed of reels from nearby vendors.

Query Parameters:
```
lat, lng          required
radius_m          optional, default 1000
page, page_size   optional (default page_size=10)
```

Ranking Logic for Reels Feed:
```
reel_score = (
    distance_factor * 0.30 +      # closer vendor = higher score
    recency_factor * 0.25 +        # newer reel = higher score
    engagement_rate * 0.25 +       # completions / views
    has_active_promotion * 0.20    # promo reels boosted
) * tier_multiplier
```

Response:
```json
{
  "reels": [
    {
      "id": "uuid",
      "video_url": "https://...",
      "thumbnail_url": "https://...",
      "duration_seconds": 11,
      "vendor": {
        "id": "uuid",
        "name": "Pizza Hub",
        "category_emoji": "🍕",
        "distance_m": 200,
        "tier": "DIAMOND"
      },
      "has_promotion": true,
      "promotion": {
        "label": "20% OFF",
        "ends_at": "2026-02-27T15:00:00Z"
      },
      "cta_label": "Get Directions",
      "view_count": 1240
    }
  ],
  "next_page": 2
}
```

### 11.2 Reel View Tracking

**`POST /api/v1/user-portal/track/reel-view/`**

Fire-and-forget analytics. Async processing via Celery.

Request:
```json
{
  "reel_id": "uuid",
  "watched_seconds": 9,
  "completed": true,
  "cta_tapped": false
}
```

Response: `202 Accepted` immediately. Actual DB write happens in background Celery task.

---

## 12. NAVIGATION INTEGRATION

### 12.1 Navigation Architecture

AirAds does not build a custom routing engine. Navigation is handled via:

**Tier 1 (Primary):** Deep link to Google Maps / Apple Maps native app
**Tier 2 (Fallback):** Web Google Maps directions URL (`target="_blank"`)
**Tier 3 (In-app preview):** Mapbox GL JS / Flutter Mapbox with route drawn

Backend role for navigation:
1. **Track navigation click:** Log `UserVendorInteraction(type='NAVIGATION')` — feeds ranking algorithm
2. **Return deep link URLs:** Navigation URLs generated server-side in vendor detail response (see Section 8.1)

### 12.2 Navigation URL Generation

Utility function in `apps/user_portal/services/navigation_service.py`:

```
get_navigation_urls(vendor, user_lat, user_lng) → dict:
  google_maps_app:  comgooglemaps://?daddr={lat},{lng}&directionsmode=walking
  google_maps_web:  https://www.google.com/maps/dir/{user_lat},{user_lng}/{lat},{lng}
  apple_maps:       maps://?daddr={lat},{lng}&dirflg=w
  mapbox_coords:    {"from": [user_lng, user_lat], "to": [dest_lng, dest_lat]}
```

These URLs are embedded in the vendor detail API response under `navigation` key.

### 12.3 Arrival Detection

Arrival detection is **client-side only** — no backend involvement. Client uses `navigator.geolocation.watchPosition()` (web) or `geolocator.getPositionStream()` (Flutter) and checks if distance to vendor < 30m. When arrived, client fires an optional interaction event `type='ARRIVAL'` for analytics.

### 12.4 Interaction Tracking

**`POST /api/v1/user-portal/track/interaction/`**

```json
{
  "vendor_id": "uuid",
  "interaction_type": "NAVIGATION",
  "session_id": "uuid",
  "lat": 31.52,
  "lng": 74.36
}
```

Response: `202 Accepted` — async write. Accepted types: `VIEW | TAP | NAVIGATION | CALL | REEL_VIEW | PROMOTION_TAP | ARRIVAL`.

---

## 13. USER PREFERENCES APIs

### 13.1 Get / Update Preferences

**`GET /api/v1/user-portal/preferences/`**
**`PUT /api/v1/user-portal/preferences/`**

Auth: JWT (logged-in) or `X-Guest-Token` header (guest mode).

Guest preferences: stored in `UserPreference(user=null, guest_token=<uuid>)` — expire in 30 days.
Logged-in preferences: stored in `UserPreference(user=<CustomerUser>)`.

On login/register, if `guest_token` preferences exist → **migrated** to the user account via `migrate_guest_preferences(guest_token, user)` service call. This happens transparently on every successful login.

> **[AUDIT FIX — MEDIUM 2.8]** Guest preference migration edge cases:
> - Login request body accepts optional `guest_token` field
> - If guest prefs exist AND user has no prior prefs → full copy
> - If user already has prefs → merge (only override defaults, not explicit user choices)
> - After merge: `UserPreference.guest_token = null` (disassociate from guest)
> - `FlashDealAlert` rows with that `guest_token` → reassigned to `user`
> - `UserSearchHistory` rows → reassigned to `user`
> - Old `GuestPreference` row → soft-deleted (not hard-deleted for 30-day audit trail)

GET Response:
```json
{
  "default_view": "AR",
  "search_radius_m": 500,
  "show_open_now_only": false,
  "preferred_category_slugs": ["food", "cafe"],
  "price_range": "BUDGET",
  "theme": "DARK",
  "notifications": {
    "nearby_deals": true,
    "flash_deals": true,
    "new_vendors": true,
    "all_off": false
  }
}
```

### 13.2 Search History

**`GET /api/v1/user-portal/preferences/search-history/`**

Returns last 20 search queries (text + voice + tag) for the user. Ordered by `searched_at DESC`.

**`DELETE /api/v1/user-portal/preferences/search-history/`**

Clears all search history for user/guest. Returns `204 No Content`.

### 13.3 Data Export (GDPR Article 20)

**`GET /api/v1/user-portal/auth/account/export/`**

Collects and returns all user data as JSON download:
- Account profile
- Preferences
- Search history
- Interaction events (last 90 days)
- Reel view history

Content-Disposition: `attachment; filename="airad-data-export-{date}.json"`

### 13.4 Account Deletion (GDPR Right to Erasure)

**`DELETE /api/v1/user-portal/auth/account/`**

Request body:
```json
{"confirmation_code": "abc123"}
```

Flow:
1. Sends confirmation code to registered email first (separate endpoint: `POST /auth/account/deletion-code/`)
2. On DELETE with valid code:
   - `CustomerUser.is_deleted = True` (soft delete)
   - Clears PII: nullifies name, email, phone, behavioral_data
   - Purges search history, interaction events, preferences
   - Django User: `is_active = False`
   - Celery task queued: `purge_deleted_customer_data` (runs in 30 days — GDPR grace period)
   - AuditLog entry created (immutable record of deletion request)
3. Returns `204 No Content`
4. Client should logout and redirect to landing page

---

## 14. ANALYTICS & BEHAVIORAL TRACKING

### 14.1 Tracking Architecture

**Philosophy:** Fire-and-forget. Tracking must NEVER slow down the user-facing experience.

All tracking endpoints respond with `202 Accepted` immediately. Actual writes happen via Celery tasks (queued to Redis, processed by Celery workers).

### 14.2 Session Management

Sessions are created client-side (UUID v4, stored in `sessionStorage` / Flutter memory). The backend receives `session_id` in tracking requests and groups interactions per session for funnel analysis.

### 14.3 Analytics Events → Vendor Dashboards

The following user portal events flow into vendor analytics (visible in Vendor Portal dashboard):

| User Action | Vendor Metric Updated |
|---|---|
| `TAP` on AR marker / map pin | `vendor.ar_tap_count` |
| `VIEW` vendor profile | `vendor.profile_view_count` |
| `NAVIGATION` click | `vendor.navigation_click_count` (Gold+ can see breakdown) |
| `PROMOTION_TAP` | `discount.taps_during_campaign` |
| `REEL_VIEW` completed | `reel.view_count`, `reel.completion_rate` |

Updates are **not real-time** — Celery task `aggregate_vendor_analytics` runs every 15 minutes, aggregating `UserVendorInteraction` rows into vendor-level counters.

### 14.4 Behavioral Personalization Strategy

**Client-side behavioral learning (primary):**
- Stored in `localStorage` (web) / `hive` (Flutter) — on device only
- Categories browsed, price ranges interacted with, time-of-day patterns
- Used to reorder discovery results client-side (no API involvement)
- Privacy-first: never sent to server in Phase-1

**Server-side behavioral signals (secondary):**
- `UserSearchHistory` → used to generate personalized voice search suggestions
- `UserVendorInteraction` → used to exclude recently-viewed vendors from "New to you" highlights
- **Never** used for individual user profiling or ad targeting
- Aggregated only for vendor analytics dashboards

---

## 15. PERFORMANCE & CACHING ARCHITECTURE

### 15.1 Redis Cache Layer

Same Redis instance as existing backend. Separate key namespace: `up:` (user portal prefix).

| Cache Key Pattern | TTL | Content |
|---|---|---|
| `up:nearby:{geohash}:{tag_hash}:{radius}` | 60s | Discovery results JSON |
| `up:ar:{geohash}:{radius}` | 30s | AR markers (shorter TTL — AR is real-time) |
| `up:vendor:{vendor_id}` | 300s | Full vendor profile |
| `up:tags:{geohash}` | 120s | Tag browser counts |
| `up:deals:{geohash}:{radius}` | 60s | Active deals nearby |
| `up:reels:{geohash}:{radius}:{page}` | 90s | Reels feed |
| `up:popularity:{vendor_id}` | 900s | Popularity score |

Cache invalidation strategy:
- On `Vendor` update → delete `up:vendor:{id}`, `up:nearby:*` in that geohash cell
- On `Discount` create/expire → delete `up:deals:*` in vendor's geohash, `up:nearby:*`
- On `Reel` upload/delete → delete `up:reels:*` in vendor's geohash
- All invalidations: Django signal receivers → Redis delete (synchronous — small operation)

### 15.2 Database Query Optimization

**Critical queries optimized with:**
- PostGIS `ST_DWithin` spatial index (GiST) — never degree-based distance
- Compound index: `(is_deleted, is_active, subscription_tier)` on Vendor
- Partial index: active promotions only `WHERE is_deleted=false AND ends_at > NOW()`
- `select_related('subscription', 'area')` on all vendor queries
- `prefetch_related('tags')` when tag data needed
- Use `.values()` / `.only()` to fetch only required fields in list endpoints
- Deferred loading: `cover_media_url`, `description` only fetched in detail endpoints

### 15.3 Response Time Targets

| Endpoint | Target (cache hit) | Target (cache miss) |
|---|---|---|
| `/discovery/nearby/` | < 80ms | < 350ms |
| `/discovery/nearby/ar-markers/` | < 40ms | < 150ms |
| `/discovery/nearby/map-pins/` | < 60ms | < 200ms |
| `/vendors/<id>/` | < 60ms | < 200ms |
| `/deals/nearby/` | < 80ms | < 300ms |
| `/discovery/search/` | N/A (no cache) | < 300ms |
| `/discovery/voice-search/` | N/A (no cache) | < 200ms |
| `/track/interaction/` | < 20ms (async 202) | — |

### 15.4 Pagination Strategy

- All list endpoints: cursor-based pagination (keyset pagination) for real-time data
- Default page_size: 20 for vendor lists, 10 for reels
- Max page_size: 50 for vendor lists, 20 for reels
- AR markers: no pagination — all markers within radius returned (max 15 enforced server-side)

### 15.5 Rate Limiting

Using DRF throttle classes:

| Endpoint Group | Anonymous Rate | Authenticated Rate |
|---|---|---|
| Discovery APIs | 60/minute | 120/minute |
| Voice Search | 10/minute | 30/minute |
| Tracking APIs | 100/minute | 200/minute |
| Auth APIs | 5/minute | 10/minute |

Rate limit keys: by IP for anonymous, by user_id for authenticated.

> **[AUDIT FIX — HIGH 3.5 / MEDIUM 3.15]** DRF throttle responses must include `Retry-After` header so clients can display a countdown. Implement a custom throttle class:

```python
# apps/user_portal/throttling.py
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

class DiscoveryAnonThrottle(AnonRateThrottle):
    rate = '60/min'
    scope = 'discovery_anon'

    def throttle_failure(self):
        # DRF already sets Retry-After in the 429 response header via
        # throttle.wait() — ensure DEFAULT_THROTTLE_CLASSES uses these
        return super().throttle_failure()

# In settings: add 'Retry-After' to CORS_ALLOW_HEADERS so Flutter/browser can read it
CORS_ALLOW_HEADERS = [...default headers..., 'retry-after']
```

DRF natively sets `Retry-After` on 429 responses. Ensure it is not stripped by Nginx or CORS config.

---

## 15A. CITY / AREA SELECTOR API

> **[AUDIT FIX — HIGH 1.8]** When user denies location permission, the LocationContext in the Discovery shell shows a city picker. This requires a backend API.

**`GET /api/v1/user-portal/discovery/cities/`**

No query parameters required. Returns all cities and areas where AirAds has active vendors.

Response:
```json
{
  "cities": [
    {
      "id": "uuid",
      "name": "Lahore",
      "lat": 31.5204,
      "lng": 74.3587,
      "active_vendor_count": 340,
      "areas": [
        {"name": "Gulberg III", "lat": 31.5121, "lng": 74.3466},
        {"name": "DHA Phase 5", "lat": 31.4697, "lng": 74.3849}
      ]
    }
  ]
}
```

Backend: Read from existing `geo` app `Area` model with aggregated `active_vendor_count`. Cache: TTL 10 minutes (`up:cities`).

Add URL: `/api/v1/user-portal/discovery/cities/` to `user_portal/urls.py`.

---

## 15B. MEDIA STORAGE & CDN STRATEGY

> **[AUDIT FIX — HIGH 3.13]** All `cover_media_url`, `logo_url`, `thumbnail_url`, and `video_url` fields in API responses must point to stable CDN URLs — not local Railway ephemeral storage.

### Storage Architecture

- **Provider:** AWS S3 (or compatible — Cloudflare R2 preferred for cost)
- **Django Integration:** `django-storages` + `boto3`
- **Media bucket structure:**
  ```
  airad-media/
  ├── vendors/{vendor_id}/logo.{ext}
  ├── vendors/{vendor_id}/cover.{ext}
  ├── reels/{reel_id}/video.mp4
  ├── reels/{reel_id}/thumbnail.jpg
  ```
- **CDN:** CloudFront (or Cloudflare) in front of S3 — all media URLs use CDN domain (`media.airad.pk`)
- **Uploads:** Vendor Portal backend handles all uploads (existing Vendor Portal scope) — User Portal only consumes URLs
- **Image optimization pipeline:** WebP conversion on upload (Pillow + django-imagekit), responsive sizes: `_sm` (200px), `_md` (400px), `_lg` (800px) suffixes
- **Required env vars:**
  ```
  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME,
  AWS_S3_REGION_NAME, AWS_S3_CUSTOM_DOMAIN (CDN URL)
  ```
- **Fallback:** If `cover_media_url` is null → API returns null; client renders CSS gradient fallback (never broken image)

---

## 15C. HEALTH CHECK ENDPOINT

> **[AUDIT FIX — MEDIUM 3.11]** Railway deployment, CI/CD, and load balancers require a health check endpoint.

**`GET /api/v1/health/`** (no auth required — allow any)

Response (200 OK when healthy):
```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok",
  "version": "1.0.0"
}
```

Logic: Executes `SELECT 1` against DB and `redis.ping()`. Returns 503 if either fails.
Add to `config/urls.py` at root level (not under `/api/v1/user-portal/`).

---

## 15D. DEEP LINK WELL-KNOWN FILES

> **[AUDIT FIX — HIGH 3.16]** Flutter Universal Links (iOS) and App Links (Android) require backend-served verification files.

**Files required:**

1. **iOS — `GET /.well-known/apple-app-site-association`**
   ```json
   {
     "applinks": {
       "apps": [],
       "details": [{
         "appID": "TEAMID.pk.airad.customerapp",
         "paths": ["/vendor/*", "/deals", "/reels", "/discover"]
       }]
     }
   }
   ```

2. **Android — `GET /.well-known/assetlinks.json`**
   ```json
   [{
     "relation": ["delegate_permission/common.handle_all_urls"],
     "target": {
       "namespace": "android_app",
       "package_name": "pk.airad.customerapp",
       "sha256_cert_fingerprints": ["<RELEASE_KEYSTORE_SHA256>"]
     }
   }]
   ```

Implementation: Add a `well_known` Django app or simple `TemplateView` at `/.well-known/` in `config/urls.py`. Serve as static JSON. **Must be served over HTTPS with correct `Content-Type: application/json` header**.

Required env var: `APP_TEAM_ID` (iOS), `APP_CERT_FINGERPRINT` (Android) — set in Railway environment.

---

## 15E. GDPR CONSENT RECORDING

> **[AUDIT FIX — HIGH 3.10]** GDPR + Pakistani PDPA require storing proof of user consent for data collection. Deletion/export alone is insufficient — you need consent records.

### ConsentRecord Model

```
ConsentRecord
├── user (ForeignKey → CustomerUser, nullable)
├── guest_token (UUIDField, nullable)
├── consent_type (CharField: 'LOCATION' | 'ANALYTICS' | 'MARKETING' | 'TERMS')
├── consented (BooleanField)
├── consent_version (CharField, e.g. '1.0') — bump when policy changes
├── ip_address (GenericIPAddressField — hashed for privacy)
├── user_agent (CharField, max=200)
├── consented_at (DateTimeField, auto_now_add=True)
```

Add to `apps/customer_auth/models.py`.

**API endpoint for recording consent:**
`POST /api/v1/user-portal/auth/consent/`
```json
{"consent_type": "LOCATION", "consented": true, "consent_version": "1.0"}
```

**When to fire:**
- On first GPS permission grant → record `LOCATION` consent
- On account registration → record `TERMS` + `ANALYTICS` consent
- On first mic use → record `ANALYTICS` consent update (voice transcripts)

**Data export includes all ConsentRecord rows for this user (GDPR Article 20).**

---

## 16. SECURITY ARCHITECTURE

### 16.1 API Versioning Strategy

> **[AUDIT FIX — CRITICAL]** Production APIs must evolve without breaking existing clients. A comprehensive versioning strategy ensures backward compatibility and smooth upgrades.

### Versioning Policy

**URL Structure:**
```
/api/v1/user-portal/  ← Current version (supported)
/api/v2/user-portal/  ← Future version (when breaking changes needed)
/api/legacy/user-portal/  ← Deprecated versions (6-month sunset)
```

**Version Support Matrix:**
- **v1:** Current production version - Full support
- **v2:** Next version - Developed alongside v1, no breaking changes to v1
- **legacy:** Deprecated versions - Security fixes only, 6-month sunset policy

**Backward Compatibility Rules:**
1. **Never remove fields** from response objects - only add new optional fields
2. **Never change field types** - use new field names for type changes
3. **Never change HTTP methods** for existing endpoints
4. **Never change error response format** - extend with new error codes only
5. **Enum values can be added** but never removed or renamed

**Version Migration Process:**
```python
# In config/urls.py - version routing
urlpatterns = [
    # Current version
    path('api/v1/user-portal/', include('user_portal.urls.v1')),
    
    # Future version (parallel development)
    path('api/v2/user-portal/', include('user_portal.urls.v2')),
    
    # Legacy redirect (graceful migration)
    path('api/legacy/user-portal/', include('user_portal.urls.legacy')),
]

# Version negotiation via header (preferred)
# Accept: application/vnd.airad.user-portal+json;version=1
# Fallback to URL version if no header
```

**Deprecation Strategy:**
```python
# In user_portal/views/base.py
class VersionedAPIView(APIView):
    """Base class for versioned API views"""
    
    def get_serializer_class(self):
        # Route to version-specific serializer
        version = self.request.version or 'v1'
        return getattr(self, f'{version}_serializer_class')
    
    def finalize_response(self, request, response, *args, **kwargs):
        # Add version headers
        response['API-Version'] = request.version or 'v1'
        response['Supported-Versions'] = 'v1,v2'
        
        # Add deprecation warning for legacy versions
        if request.version == 'legacy':
            response['Deprecation-Warning'] = 'This API version will be sunset on 2026-08-27. Please migrate to v1.'
            response['Sunset-Date'] = '2026-08-27T00:00:00Z'
        
        return super().finalize_response(request, response, *args, **kwargs)
```

**Database Migration Compatibility:**
```python
# In user_portal/migrations/ - version-specific migrations
# v1 migrations: 0001_initial.py through 0099_v1_final.py
# v2 migrations: 0100_v2_start.py through 0199_v2_final.py

# Migration compatibility layer in models
class Vendor(models.Model):
    # v1 field - never removed
    name = models.CharField(max_length=200)
    
    # v2 field - added with default
    display_name = models.CharField(max_length=200, blank=True, null=True)
    
    @property
    def effective_name(self):
        """Compatibility property for v1 clients"""
        return self.display_name or self.name
```

### 16.2 Authentication Security

- JWT tokens: audience claim `"aud": "user-portal"` — NOT valid for Admin or Vendor Portal APIs
- Custom `CustomerUserAuthentication` class validates audience on every request
- Token blacklisting on logout (SimpleJWT blacklist app)
- Guest tokens: UUID v4, stored in DB, expire after 30 days
- Brute-force protection on login: 5 failed attempts → 15-minute lockout (same pattern as Admin Portal)

### 16.2 Location Data Privacy

- User GPS coordinates stored in `UserVendorInteraction` for analytics — never for individual real-time tracking
- Location data purged after 90 days (Celery task)
- Camera feed: NEVER touches backend — AR processing is 100% client-side
- Voice transcripts: stored in `UserSearchHistory` for 90 days, auto-purged

### 16.3 Data Classification (per security-architect policy)

| Data | Classification | Controls |
|---|---|---|
| Email address | CONFIDENTIAL | Encrypted at rest, never logged |
| Phone number | RESTRICTED | AES-256-GCM, masked in logs |
| GPS coordinates | CONFIDENTIAL | Stored with user_id only, purged 90 days |
| Voice transcripts | CONFIDENTIAL | Stored as text, purged 90 days |
| Behavioral events | INTERNAL | Aggregated, no PII attached |
| Guest token | INTERNAL | UUID only, no PII linkage |

### 16.4 Input Validation

- All discovery query params: range-validated (radius: 100-5000, lat: -90 to 90, lng: -180 to 180)
- Voice search transcript: max 500 chars, sanitized before NLP processing
- Search query: min 2 chars, max 200 chars, SQL injection impossible (ORM only)
- No file uploads: User Portal is read-only from the user perspective

### 16.5 API Security Headers

Applied to all User Portal endpoints via middleware:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- CORS: restricted to User Portal frontend origin (`app.airad.pk`) AND Flutter app requests

> **[AUDIT FIX — MEDIUM 3.15]** Flutter native HTTP requests do not send `Origin` headers, so standard CORS blocking does not apply. However, to support hybrid/WebView scenarios and future web-to-app transitions, add the Flutter app's origin if applicable. Primary fix: ensure `CORS_ALLOW_ALL_ORIGINS = False` with explicit `CORS_ALLOWED_ORIGINS = ['https://app.airad.pk']` in settings. Flutter native Dio requests bypass CORS entirely — no change needed for native Flutter.

---

## 17. COMPREHENSIVE ERROR HANDLING STRATEGY

> **[AUDIT FIX — CRITICAL]** Production applications without comprehensive error handling crash constantly, provide poor UX, and make debugging impossible. This section defines a complete error handling strategy for the User Portal backend.

### 17.1 Error Classification System

```python
# In user_portal/exceptions.py
from enum import Enum
from typing import Optional, Dict, Any
import traceback
import uuid

class ErrorSeverity(Enum):
    LOW = "low"        # Non-critical, user can continue
    MEDIUM = "medium"  # Affects functionality but app works
    HIGH = "high"      # Major feature broken
    CRITICAL = "critical"  # App unusable, requires immediate attention

class ErrorCategory(Enum):
    VALIDATION = "validation"           # Input validation errors
    AUTHENTICATION = "authentication"   # Auth/authorization failures
    BUSINESS_LOGIC = "business_logic"  # Expected business rule violations
    EXTERNAL_API = "external_api"       # Third-party service failures
    DATABASE = "database"               # Database connectivity/issues
    SYSTEM = "system"                   # Infrastructure failures
    UNKNOWN = "unknown"                 # Unclassified errors

class UserPortalException(Exception):
    """Base exception for all User Portal errors"""
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        error_code: Optional[str] = None,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.error_code = error_code or f"UP_{uuid.uuid4().hex[:8].upper()}"
        self.user_message = user_message or self._get_default_user_message()
        self.context = context or {}
        self.original_exception = original_exception
        self.traceback_str = traceback.format_exc()
    
    def _get_default_user_message(self) -> str:
        """Provide user-friendly default messages"""
        messages = {
            ErrorCategory.VALIDATION: "Please check your input and try again.",
            ErrorCategory.AUTHENTICATION: "Please sign in to continue.",
            ErrorCategory.BUSINESS_LOGIC: "This action is not available right now.",
            ErrorCategory.EXTERNAL_API: "Service temporarily unavailable. Please try again.",
            ErrorCategory.DATABASE: "System busy. Please try again in a moment.",
            ErrorCategory.SYSTEM: "System temporarily unavailable. Please try again later.",
        }
        return messages.get(self.category, "Something went wrong. Please try again.")
```

### 17.2 Global Exception Handler Middleware

```python
# In user_portal/middleware/error_handling.py
import logging
import json
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from .exceptions import UserPortalException, ErrorSeverity
from .utils.error_logger import ErrorLogger

class UserPortalErrorHandler:
    """Centralized error handling for User Portal APIs"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.error_logger = ErrorLogger()
    
    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except UserPortalException as e:
            return self._handle_user_portal_exception(e, request)
        except Exception as e:
            return self._handle_unexpected_exception(e, request)
    
    def _handle_user_portal_exception(self, exc: UserPortalException, request) -> JsonResponse:
        """Handle known User Portal exceptions"""
        # Log the error
        self.error_logger.log_error(
            error_code=exc.error_code,
            message=exc.message,
            category=exc.category.value,
            severity=exc.severity.value,
            request_data=self._extract_request_data(request),
            context=exc.context,
            traceback=exc.traceback_str
        )
        
        # Return appropriate response
        status_code = self._get_status_code(exc.category, exc.severity)
        
        response_data = {
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.user_message,
                "category": exc.category.value,
                "severity": exc.severity.value,
                "retry_after": getattr(exc, 'retry_after', None),
            }
        }
        
        # Include debug info in development
        if settings.DEBUG:
            response_data["debug"] = {
                "technical_message": exc.message,
                "context": exc.context,
                "traceback": exc.traceback_str
            }
        
        return JsonResponse(response_data, status=status_code)
    
    def _handle_unexpected_exception(self, exc: Exception, request) -> JsonResponse:
        """Handle unexpected exceptions"""
        error_id = f"UP_UNEXPECTED_{uuid.uuid4().hex[:8].upper()}"
        
        # Log the unexpected error
        self.error_logger.log_error(
            error_code=error_id,
            message=str(exc),
            category="unexpected",
            severity="critical",
            request_data=self._extract_request_data(request),
            context={},
            traceback=traceback.format_exc()
        )
        
        # Return generic error response
        response_data = {
            "success": False,
            "error": {
                "code": error_id,
                "message": "An unexpected error occurred. Please try again.",
                "category": "system",
                "severity": "high"
            }
        }
        
        if settings.DEBUG:
            response_data["debug"] = {
                "technical_message": str(exc),
                "traceback": traceback.format_exc()
            }
        
        return JsonResponse(response_data, status=500)
    
    def _extract_request_data(self, request) -> Dict[str, Any]:
        """Extract relevant request data for logging"""
        return {
            "method": request.method,
            "path": request.path,
            "user_id": getattr(request.user, 'id', None),
            "is_guest": hasattr(request, 'guest_token'),
            "ip_address": self._get_client_ip(request),
            "user_agent": request.META.get('HTTP_USER_AGENT', ''),
            "query_params": dict(request.GET),
            "body_size": len(request.body) if hasattr(request, 'body') else 0,
        }
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
    
    def _get_status_code(self, category: ErrorCategory, severity: ErrorSeverity) -> int:
        """Map error category and severity to HTTP status codes"""
        mapping = {
            (ErrorCategory.VALIDATION, ErrorSeverity.LOW): 400,
            (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM): 400,
            (ErrorCategory.AUTHENTICATION, ErrorSeverity.LOW): 401,
            (ErrorCategory.AUTHENTICATION, ErrorSeverity.MEDIUM): 401,
            (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH): 403,
            (ErrorCategory.BUSINESS_LOGIC, ErrorSeverity.LOW): 400,
            (ErrorCategory.BUSINESS_LOGIC, ErrorSeverity.MEDIUM): 422,
            (ErrorCategory.BUSINESS_LOGIC, ErrorSeverity.HIGH): 422,
            (ErrorCategory.EXTERNAL_API, ErrorSeverity.LOW): 502,
            (ErrorCategory.EXTERNAL_API, ErrorSeverity.MEDIUM): 502,
            (ErrorCategory.EXTERNAL_API, ErrorSeverity.HIGH): 503,
            (ErrorCategory.DATABASE, ErrorSeverity.MEDIUM): 503,
            (ErrorCategory.DATABASE, ErrorSeverity.HIGH): 503,
            (ErrorCategory.DATABASE, ErrorSeverity.CRITICAL): 503,
            (ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM): 503,
            (ErrorCategory.SYSTEM, ErrorSeverity.HIGH): 503,
            (ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL): 503,
        }
        return mapping.get((category, severity), 500)
```

### 17.3 Structured Error Logging

```python
# In user_portal/utils/error_logger.py
import logging
import json
from datetime import datetime
from django.conf import settings
from ..models import ErrorLog

class ErrorLogger:
    """Structured error logging for monitoring and alerting"""
    
    def __init__(self):
        self.logger = logging.getLogger('user_portal_errors')
        self.setup_logger()
    
    def setup_logger(self):
        """Configure structured logger"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.ERROR)
    
    def log_error(self, error_code: str, message: str, category: str, 
                  severity: str, request_data: Dict[str, Any], 
                  context: Dict[str, Any], traceback: str):
        """Log error with structured data"""
        
        # Log to Python logger
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_code": error_code,
            "message": message,
            "category": category,
            "severity": severity,
            "request": request_data,
            "context": context,
            "traceback": traceback,
        }
        
        self.logger.error(json.dumps(log_data, default=str))
        
        # Store in database for analysis (only in production)
        if not settings.DEBUG:
            try:
                ErrorLog.objects.create(
                    error_code=error_code,
                    message=message,
                    category=category,
                    severity=severity,
                    request_data=request_data,
                    context=context,
                    traceback=traceback,
                    user_id=request_data.get('user_id'),
                    is_guest=request_data.get('is_guest', False),
                    ip_address=request_data.get('ip_address'),
                    user_agent=request_data.get('user_agent'),
                    path=request_data.get('path'),
                    method=request_data.get('method'),
                )
            except Exception:
                # Don't let logging errors crash the app
                self.logger.error("Failed to store error in database")
        
        # Trigger alerts for critical errors
        if severity in ['high', 'critical']:
            self._trigger_alert(error_code, message, severity, request_data)
    
    def _trigger_alert(self, error_code: str, message: str, severity: str, 
                      request_data: Dict[str, Any]):
        """Trigger alerts for critical errors"""
        # Integration with monitoring system (Sentry, PagerDuty, etc.)
        alert_data = {
            "error_code": error_code,
            "message": message,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
            "user_impacted": request_data.get('user_id') is not None,
            "path": request_data.get('path'),
            "ip_address": request_data.get('ip_address'),
        }
        
        # Send to monitoring service
        if hasattr(settings, 'SENTRY_DSN') and settings.SENTRY_DSN:
            try:
                import sentry_sdk
                sentry_sdk.capture_message(
                    f"User Portal Error: {error_code}",
                    level="error" if severity == "high" else "fatal",
                    extra=alert_data
                )
            except Exception:
                pass  # Don't let alerting fail
```

### 17.4 Error Recovery Strategies

```python
# In user_portal/utils/recovery.py
from typing import Optional, Callable, Any
import time
from functools import wraps
from django.core.cache import cache
from ..exceptions import UserPortalException, ErrorCategory, ErrorSeverity

class RetryHandler:
    """Handle retry logic for recoverable errors"""
    
    @staticmethod
    def retry_with_backoff(
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        exceptions: tuple = (Exception,)
    ):
        """Decorator for retry with exponential backoff"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        
                        if attempt == max_attempts - 1:
                            break
                        
                        # Calculate delay
                        delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                        
                        # Log retry attempt
                        logging.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {delay:.2f} seconds..."
                        )
                        
                        time.sleep(delay)
                
                # All attempts failed
                raise last_exception
            
            return wrapper
        return decorator

class CircuitBreaker:
    """Circuit breaker pattern for external services"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise UserPortalException(
                    "Service temporarily unavailable",
                    category=ErrorCategory.EXTERNAL_API,
                    severity=ErrorSeverity.MEDIUM,
                    user_message="Service temporarily unavailable. Please try again later."
                )
        
        try:
            result = func(*args, **kwargs)
            
            # Success: reset failure count and close circuit
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
            self.failure_count = 0
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
            
            raise e

class GracefulDegradation:
    """Handle service degradation when components fail"""
    
    @staticmethod
    def with_fallback(primary_func: Callable, fallback_func: Callable, 
                     fallback_message: Optional[str] = None):
        """Execute primary function with fallback on failure"""
        try:
            return primary_func()
        except Exception as e:
            logging.warning(f"Primary function failed: {str(e)}. Using fallback.")
            
            try:
                result = fallback_func()
                if fallback_message:
                    # Add fallback indicator to result
                    if isinstance(result, dict):
                        result['_fallback_used'] = True
                        result['_fallback_message'] = fallback_message
                return result
            except Exception as fallback_error:
                raise UserPortalException(
                    "Both primary and fallback services failed",
                    category=ErrorCategory.EXTERNAL_API,
                    severity=ErrorSeverity.HIGH,
                    context={
                        "primary_error": str(e),
                        "fallback_error": str(fallback_error)
                    }
                )
```

### 17.5 Error Model for Database Storage

```python
# In user_portal/models.py (add to existing models)
class ErrorLog(models.Model):
    """Store structured error logs for analysis"""
    
    error_code = models.CharField(max_length=32, unique=True, db_index=True)
    message = models.TextField()
    category = models.CharField(max_length=20, choices=[
        ('validation', 'Validation'),
        ('authentication', 'Authentication'),
        ('business_logic', 'Business Logic'),
        ('external_api', 'External API'),
        ('database', 'Database'),
        ('system', 'System'),
        ('unexpected', 'Unexpected'),
    ], db_index=True)
    severity = models.CharField(max_length=10, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], db_index=True)
    
    # Request context
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    is_guest = models.BooleanField(default=False, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    path = models.CharField(max_length=255, db_index=True)
    method = models.CharField(max_length=10, db_index=True)
    
    # Error details
    request_data = models.JSONField(default=dict)
    context = models.JSONField(default=dict)
    traceback = models.TextField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'user_portal_error_logs'
        indexes = [
            models.Index(fields=['created_at', 'severity']),
            models.Index(fields=['category', 'severity']),
            models.Index(fields=['error_code']),
        ]
    
    def __str__(self):
        return f"{self.error_code}: {self.category}/{self.severity}"

# Add to user_portal/admin.py
@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display = ['error_code', 'category', 'severity', 'user_id', 'is_guest', 'path', 'created_at']
    list_filter = ['category', 'severity', 'is_guest', 'created_at']
    search_fields = ['error_code', 'message', 'path']
    readonly_fields = ['error_code', 'created_at', 'traceback']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False  # Errors are created automatically
```

### 17.6 Integration with Django Settings

```python
# In settings/base.py
MIDDLEWARE = [
    # ... existing middleware
    'user_portal.middleware.error_handling.UserPortalErrorHandler',
]

# Error handling settings
USER_PORTAL_ERROR_SETTINGS = {
    'ENABLE_DATABASE_LOGGING': not DEBUG,
    'MAX_RETRY_ATTEMPTS': 3,
    'CIRCUIT_BREAKER_THRESHOLD': 5,
    'CIRCUIT_BREAKER_TIMEOUT': 60,
    'ALERT_SEVERITY_THRESHOLD': 'high',  # Alert for high and critical errors
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structured': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        },
    },
    'handlers': {
        'user_portal_errors': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'structured',
        },
        'user_portal_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'user_portal_errors.log',
            'formatter': 'structured',
        },
    },
    'loggers': {
        'user_portal_errors': {
            'handlers': ['user_portal_errors', 'user_portal_file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
```

---

## 18. CELERY TASKS — USER PORTAL

New tasks added to existing Celery worker (`config/celery_app.py`):

| Task | Schedule | Purpose |
|---|---|---|
| `update_vendor_popularity_scores` | Every 15 minutes | Recalculate popularity score for all active vendors |
| `expire_promotions` | Every 5 minutes | Mark ended discounts as `is_active=False` |
| `aggregate_vendor_analytics` | Every 15 minutes | Aggregate interaction events → vendor counters |
| `purge_guest_tokens` | Daily, 3:00 AM | Delete expired guest tokens (> 30 days old) |
| `purge_search_history` | Daily, 4:00 AM | Delete search history older than 90 days |
| `purge_interaction_events` | Daily, 5:00 AM | Delete interaction events older than 90 days |
| `purge_deleted_customer_data` | Daily, 6:00 AM | Hard delete soft-deleted customer accounts older than 30 days |
| `invalidate_discovery_cache` | On-demand (Django signal receiver — NOT a beat task) | Clear Redis cache on vendor/discount updates |
| `send_flash_deal_push_notification` | On-demand (Celery task triggered by Platinum flash deal creation) | FCM push to eligible users when flash deal starts |

> **[AUDIT FIX — MEDIUM 2.2]** `invalidate_discovery_cache` is a Django signal receiver (synchronous, triggered by model `post_save`/`post_delete` signals), NOT a Celery beat periodic task. It should be in `apps/user_portal/signals.py`, not scheduled in beat config. All other 8 tasks are correctly registered as Celery beat tasks.

All tasks: idempotent (safe to re-run if interrupted). Beat tasks: registered in `config/celery_app.py` beat schedule.

---

## 18. DATA BACKUP & RECOVERY PLAN

> **[AUDIT FIX — CRITICAL]** Production applications without backup strategy risk catastrophic data loss. This section defines comprehensive backup, recovery, and disaster recovery procedures.

### 18.1 Backup Strategy Overview

**Backup Tiers:**
- **Tier 1:** Real-time replication (Primary → Standby)
- **Tier 2:** Hourly snapshots (Point-in-time recovery)
- **Tier 3:** Daily full backups (Long-term retention)
- **Tier 4:** Weekly offsite backups (Disaster recovery)

**Data Classification:**
```python
# In user_portal/backup/models.py
class BackupClassification(models.TextChoices):
    CRITICAL = 'CRITICAL', 'Critical - Real-time backup required'
    IMPORTANT = 'IMPORTANT', 'Important - Hourly backup required'
    STANDARD = 'STANDARD', 'Standard - Daily backup sufficient'
    ARCHIVAL = 'ARCHIVAL', 'Archival - Weekly backup only'

# Data classification mapping
BACKUP_CLASSIFICATION_MAP = {
    # Customer data (Critical - GDPR compliance)
    'customer_user': BackupClassification.CRITICAL,
    'user_preference': BackupClassification.CRITICAL,
    'user_search_history': BackupClassification.IMPORTANT,
    'user_vendor_interaction': BackupClassification.IMPORTANT,
    
    # Vendor data (Important)
    'vendor': BackupClassification.IMPORTANT,
    'vendor_promotion': BackupClassification.IMPORTANT,
    'vendor_reel': BackupClassification.STANDARD,
    
    # System data (Standard/Archival)
    'flash_deal_alert': BackupClassification.STANDARD,
    'nearby_reel_view': BackupClassification.ARCHIVAL,
    'error_log': BackupClassification.STANDARD,
    
    # Configuration (Critical)
    'user_portal_config': BackupClassification.CRITICAL,
}
```

### 18.2 Real-time Replication Setup

**PostgreSQL Streaming Replication:**

```bash
# Primary server configuration (postgresql.conf)
wal_level = replica
max_wal_senders = 3
wal_keep_segments = 64
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/wal_archive/%f'

# Standby server configuration (recovery.conf)
standby_mode = 'on'
primary_conninfo = 'host=primary-db port=5432 user=replicator'
restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'
```

**Redis Replication:**

```bash
# Master redis.conf
bind 0.0.0.0
port 6379
requirepass your_redis_password
save 900 1  # Save if 1 key changes in 15 minutes
appendonly yes
appendfsync everysec

# Slave redis.conf
slaveof master-db-ip 6379
masterauth your_redis_password
slave-serve-stale-data yes
slave-read-only yes
```

### 18.3 Automated Backup System

```python
# In user_portal/backup/tasks.py
from celery import shared_task
from django.conf import settings
from django.core.management import call_command
import boto3
import gzip
import json
from datetime import datetime, timedelta
from .models import BackupLog, BackupClassification

class BackupService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION
        )
        self.backup_bucket = settings.AWS_BACKUP_BUCKET
    
    @shared_task(bind=True, name='backup.create_hourly_snapshot')
    def create_hourly_snapshot(self):
        """Create hourly database snapshots"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        try:
            # PostgreSQL backup
            pg_backup_file = f'postgresql_hourly_{timestamp}.sql.gz'
            self._create_postgresql_backup(pg_backup_file, 'hourly')
            
            # Redis backup
            redis_backup_file = f'redis_hourly_{timestamp}.rdb.gz'
            self._create_redis_backup(redis_backup_file, 'hourly')
            
            # Media files backup (incremental)
            media_backup_file = f'media_incremental_{timestamp}.tar.gz'
            self._create_media_backup(media_backup_file, 'hourly')
            
            # Log backup
            BackupLog.objects.create(
                backup_type='hourly',
                status='success',
                files_created=[pg_backup_file, redis_backup_file, media_backup_file],
                size_bytes=self._calculate_backup_size([pg_backup_file, redis_backup_file, media_backup_file]),
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            BackupLog.objects.create(
                backup_type='hourly',
                status='failed',
                error_message=str(e),
                timestamp=datetime.utcnow()
            )
            raise
    
    @shared_task(bind=True, name='backup.create_daily_full')
    def create_daily_full_backup(self):
        """Create daily full backups"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        try:
            # Full PostgreSQL backup
            pg_backup_file = f'postgresql_full_{timestamp}.sql.gz'
            self._create_postgresql_backup(pg_backup_file, 'full')
            
            # Full Redis backup
            redis_backup_file = f'redis_full_{timestamp}.rdb.gz'
            self._create_redis_backup(redis_backup_file, 'full')
            
            # Full media backup
            media_backup_file = f'media_full_{timestamp}.tar.gz'
            self._create_media_backup(media_backup_file, 'full')
            
            # Configuration backup
            config_backup_file = f'config_full_{timestamp}.tar.gz'
            self._create_config_backup(config_backup_file)
            
            # Log backup with retention cleanup
            BackupLog.objects.create(
                backup_type='daily_full',
                status='success',
                files_created=[pg_backup_file, redis_backup_file, media_backup_file, config_backup_file],
                size_bytes=self._calculate_backup_size([pg_backup_file, redis_backup_file, media_backup_file, config_backup_file]),
                timestamp=datetime.utcnow()
            )
            
            # Clean up old hourly backups (keep 48 hours)
            self._cleanup_old_backups('hourly', hours_to_keep=48)
            
        except Exception as e:
            BackupLog.objects.create(
                backup_type='daily_full',
                status='failed',
                error_message=str(e),
                timestamp=datetime.utcnow()
            )
            raise
    
    def _create_postgresql_backup(self, filename, backup_type):
        """Create PostgreSQL backup"""
        if backup_type == 'full':
            # Full backup with all data
            cmd = f'pg_dump -h {settings.DB_HOST} -U {settings.DB_USER} -d {settings.DB_NAME} --no-password --clean --if-exists'
        else:
            # Hourly incremental backup (data only, no schema)
            cmd = f'pg_dump -h {settings.DB_HOST} -U {settings.DB_USER} -d {settings.DB_NAME} --no-password --data-only'
        
        # Execute backup and compress
        import subprocess
        with gzip.open(f'/tmp/{filename}', 'wb') as f:
            subprocess.run(cmd, shell=True, stdout=f, check=True)
        
        # Upload to S3
        self._upload_to_s3(f'/tmp/{filename}', f'postgresql/{filename}')
        
        # Clean up local file
        os.remove(f'/tmp/{filename}')
    
    def _create_redis_backup(self, filename, backup_type):
        """Create Redis backup"""
        import redis
        import shutil
        
        # Trigger Redis save
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
        r.save()
        
        # Wait for save to complete
        while r.lastsave() == r.info()['rdb_last_save_time']:
            time.sleep(1)
        
        # Copy and compress RDB file
        rdb_path = '/var/lib/redis/dump.rdb'
        with gzip.open(f'/tmp/{filename}', 'wb') as f:
            with open(rdb_path, 'rb') as rdb_file:
                shutil.copyfileobj(rdb_file, f)
        
        # Upload to S3
        self._upload_to_s3(f'/tmp/{filename}', f'redis/{filename}')
        
        # Clean up local file
        os.remove(f'/tmp/{filename}')
    
    def _create_media_backup(self, filename, backup_type):
        """Create media files backup"""
        import tarfile
        
        media_path = settings.MEDIA_ROOT
        
        with tarfile.open(f'/tmp/{filename}', 'w:gz') as tar:
            if backup_type == 'full':
                tar.add(media_path, arcname='media')
            else:
                # Incremental backup - only files modified in last hour
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                for root, dirs, files in os.walk(media_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if datetime.fromtimestamp(os.path.getmtime(file_path)) > cutoff_time:
                            tar.add(file_path, arcname=os.path.relpath(file_path, media_path))
        
        # Upload to S3
        self._upload_to_s3(f'/tmp/{filename}', f'media/{filename}')
        
        # Clean up local file
        os.remove(f'/tmp/{filename}')
    
    def _upload_to_s3(self, local_file, s3_key):
        """Upload file to S3 with proper metadata"""
        self.s3_client.upload_file(
            local_file,
            self.backup_bucket,
            s3_key,
            ExtraArgs={
                'StorageClass': 'STANDARD_IA',  # Infrequent Access for cost optimization
                'ServerSideEncryption': 'AES256',
                'Metadata': {
                    'backup-timestamp': datetime.utcnow().isoformat(),
                    'backup-source': 'airads-user-portal'
                }
            }
        )
    
    def _cleanup_old_backups(self, backup_type, hours_to_keep=48):
        """Clean up old backups from S3"""
        cutoff_date = datetime.utcnow() - timedelta(hours=hours_to_keep)
        prefix = f'{backup_type}/'
        
        response = self.s3_client.list_objects_v2(
            Bucket=self.backup_bucket,
            Prefix=prefix
        )
        
        for obj in response.get('Contents', []):
            if datetime.fromisoformat(obj['LastModified'].replace('Z', '+00:00')) < cutoff_date:
                self.s3_client.delete_object(Bucket=self.backup_bucket, Key=obj['Key'])
```

### 18.4 Disaster Recovery Procedures

```python
# In user_portal/backup/recovery.py
class DisasterRecoveryService:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.backup_bucket = settings.AWS_BACKUP_BUCKET
    
    def initiate_disaster_recovery(self, recovery_point=None):
        """Initiate disaster recovery from specified recovery point"""
        if recovery_point is None:
            recovery_point = self._find_latest_recovery_point()
        
        recovery_log = RecoveryLog.objects.create(
            recovery_point=recovery_point,
            status='initiated',
            started_at=datetime.utcnow()
        )
        
        try:
            # Step 1: Restore database
            self._restore_database(recovery_point, recovery_log)
            
            # Step 2: Restore Redis cache
            self._restore_redis(recovery_point, recovery_log)
            
            # Step 3: Restore media files
            self._restore_media(recovery_point, recovery_log)
            
            # Step 4: Verify system integrity
            self._verify_system_integrity(recovery_log)
            
            recovery_log.status = 'completed'
            recovery_log.completed_at = datetime.utcnow()
            recovery_log.save()
            
        except Exception as e:
            recovery_log.status = 'failed'
            recovery_log.error_message = str(e)
            recovery_log.save()
            raise
    
    def _restore_database(self, recovery_point, recovery_log):
        """Restore PostgreSQL database from backup"""
        backup_file = f'postgresql/postgresql_full_{recovery_point}.sql.gz'
        
        # Download backup from S3
        local_backup = f'/tmp/recovery_{recovery_point}.sql.gz'
        self.s3_client.download_file(self.backup_bucket, backup_file, local_backup)
        
        # Restore database
        import subprocess
        cmd = f'gunzip -c {local_backup} | psql -h {settings.DB_HOST} -U {settings.DB_USER} -d {settings.DB_NAME}'
        subprocess.run(cmd, shell=True, check=True)
        
        # Clean up
        os.remove(local_backup)
        
        recovery_log.add_step('database_restored', 'PostgreSQL database restored successfully')
    
    def _restore_redis(self, recovery_point, recovery_log):
        """Restore Redis from backup"""
        backup_file = f'redis/redis_full_{recovery_point}.rdb.gz'
        
        # Download backup from S3
        local_backup = f'/tmp/redis_recovery_{recovery_point}.rdb.gz'
        self.s3_client.download_file(self.backup_bucket, backup_file, local_backup)
        
        # Stop Redis, replace RDB file, start Redis
        import subprocess
        subprocess.run('systemctl stop redis', shell=True, check=True)
        
        # Extract and replace RDB file
        with gzip.open(local_backup, 'rb') as f:
            with open('/var/lib/redis/dump.rdb', 'wb') as rdb:
                shutil.copyfileobj(f, rdb)
        
        subprocess.run('systemctl start redis', shell=True, check=True)
        
        # Clean up
        os.remove(local_backup)
        
        recovery_log.add_step('redis_restored', 'Redis cache restored successfully')
    
    def _verify_system_integrity(self, recovery_log):
        """Verify system integrity after recovery"""
        # Check database connectivity
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        
        # Check Redis connectivity
        import redis
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
        r.ping()
        
        # Check critical tables exist and have data
        critical_tables = ['customer_user', 'user_preference', 'vendor', 'vendor_promotion']
        for table in critical_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            if count == 0:
                raise Exception(f"Critical table {table} is empty after recovery")
        
        recovery_log.add_step('integrity_verified', 'System integrity verified successfully')
```

### 18.5 Backup Monitoring & Alerting

```python
# In user_portal/backup/monitoring.py
class BackupMonitoringService:
    
    @shared_task(name='backup.monitor_backup_health')
    def monitor_backup_health(self):
        """Monitor backup health and send alerts"""
        
        # Check recent backup failures
        recent_failures = BackupLog.objects.filter(
            status='failed',
            timestamp__gte=datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        if recent_failures > 0:
            self._send_alert(
                'backup_failure',
                f'{recent_failures} backup failures in last 24 hours',
                severity='high'
            )
        
        # Check backup age
        latest_backup = BackupLog.objects.filter(
            status='success',
            backup_type='daily_full'
        ).order_by('-timestamp').first()
        
        if latest_backup and (datetime.utcnow() - latest_backup.timestamp) > timedelta(hours=30):
            self._send_alert(
                'backup_stale',
                'Latest daily backup is more than 30 hours old',
                severity='critical'
            )
        
        # Check storage costs
        total_size = BackupLog.objects.filter(
            timestamp__gte=datetime.utcnow() - timedelta(days=7)
        ).aggregate(total_size=models.Sum('size_bytes'))['total_size'] or 0
        
        if total_size > 100 * 1024 * 1024 * 1024:  # 100GB
            self._send_alert(
                'backup_storage_high',
                f'Weekly backup storage: {total_size / (1024**3):.1f}GB',
                severity='medium'
            )
    
    def _send_alert(self, alert_type, message, severity):
        """Send backup monitoring alert"""
        # Integration with monitoring system
        if hasattr(settings, 'SENTRY_DSN'):
            import sentry_sdk
            sentry_sdk.capture_message(
                f'Backup Alert: {alert_type}',
                level=severity,
                extra={'message': message}
            )
        
        # Send email alert for critical issues
        if severity == 'critical':
            from django.core.mail import send_mail
            send_mail(
                f'Critical Backup Alert: {alert_type}',
                message,
                settings.DEFAULT_FROM_EMAIL,
                settings.BACKUP_ALERT_EMAILS,
                fail_silently=False
            )
```

### 18.6 Backup Retention Policy

```python
# In user_portal/backup/retention.py
class BackupRetentionPolicy:
    
    @shared_task(name='backup.apply_retention_policy')
    def apply_retention_policy(self):
        """Apply backup retention policy"""
        
        retention_rules = {
            'hourly': timedelta(hours=48),      # Keep 48 hours of hourly backups
            'daily_full': timedelta(days=30),   # Keep 30 days of daily backups
            'weekly_offsite': timedelta(days=90), # Keep 90 days of weekly backups
        }
        
        for backup_type, retention_period in retention_rules.items():
            cutoff_date = datetime.utcnow() - retention_period
            
            # Delete from S3
            self._delete_s3_backups(backup_type, cutoff_date)
            
            # Delete from local logs
            BackupLog.objects.filter(
                backup_type=backup_type,
                timestamp__lt=cutoff_date
            ).delete()
    
    def _delete_s3_backups(self, backup_type, cutoff_date):
        """Delete old backups from S3"""
        prefix = f'{backup_type}/'
        
        response = self.s3_client.list_objects_v2(
            Bucket=self.backup_bucket,
            Prefix=prefix
        )
        
        deleted_count = 0
        for obj in response.get('Contents', []):
            if datetime.fromisoformat(obj['LastModified'].replace('Z', '+00:00')) < cutoff_date:
                self.s3_client.delete_object(Bucket=self.backup_bucket, Key=obj['Key'])
                deleted_count += 1
        
        return deleted_count
```

### 18.7 Backup Models & Admin

```python
# In user_portal/backup/models.py (add to existing)
class BackupLog(models.Model):
    backup_type = models.CharField(max_length=20, choices=[
        ('hourly', 'Hourly'),
        ('daily_full', 'Daily Full'),
        ('weekly_offsite', 'Weekly Offsite'),
    ])
    status = models.CharField(max_length=20, choices=[
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('running', 'Running'),
    ])
    files_created = models.JSONField(default=list)
    size_bytes = models.BigIntegerField(default=0)
    error_message = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'backup_logs'
        indexes = [
            models.Index(fields=['backup_type', 'timestamp']),
            models.Index(fields=['status', 'timestamp']),
        ]

class RecoveryLog(models.Model):
    recovery_point = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=[
        ('initiated', 'Initiated'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ])
    steps_completed = models.JSONField(default=list)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def add_step(self, step_name, description):
        self.steps_completed.append({
            'step': step_name,
            'description': description,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.save()

# In user_portal/backup/admin.py
@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    list_display = ['backup_type', 'status', 'size_bytes_display', 'timestamp', 'error_message']
    list_filter = ['backup_type', 'status', 'timestamp']
    search_fields = ['error_message']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    def size_bytes_display(self, obj):
        return f"{obj.size_bytes / (1024*1024):.1f} MB"
    size_bytes_display.short_description = 'Size'

@admin.register(RecoveryLog)
class RecoveryLogAdmin(admin.ModelAdmin):
    list_display = ['recovery_point', 'status', 'started_at', 'completed_at', 'duration']
    list_filter = ['status', 'started_at']
    readonly_fields = ['recovery_point', 'steps_completed', 'started_at', 'completed_at']
    date_hierarchy = 'started_at'
    
    def duration(self, obj):
        if obj.completed_at:
            return obj.completed_at - obj.started_at
        return "In progress"
```

---

## 19. SCALING PLAN

### Phase-1 Scale Targets
- **Users:** 10,000 DAU (Month 3 target)
- **Peak concurrent:** 500 simultaneous API calls
- **Vendors:** 5,000 active vendors across 3 cities

### Infrastructure at Phase-1 Scale
- **Backend:** 2 Django/Gunicorn workers (existing Railway setup)
- **Redis:** Single Redis instance (existing) — sufficient for Phase-1 cache volume
- **Celery:** 2 workers for task processing (existing)
- **Database:** PostgreSQL + PostGIS (existing) — spatial indexes handle 5,000 vendors easily

### Phase-2 Scale Considerations (planned, not built yet)

| Concern | Solution |
|---|---|
| 50,000+ vendors | PostGIS geohash pre-computation table for faster spatial queries |
| Read-heavy discovery | PostgreSQL read replica — writes to primary, discovery reads from replica |
| Large media files | CDN for vendor images, reel thumbnails (CloudFront or similar) |
| High Celery queue volume | Auto-scaling Celery workers based on queue depth metric |
| Redis memory | Redis Cluster if cache exceeds 2GB |
| Multi-city flash deals | Sharded Redis by city to reduce key namespace collisions |

---

## 18. PRODUCTION INFRASTRUCTURE & OPERATIONS

### 18.1 CI/CD Pipeline Strategy

> **[AUDIT FIX — CRITICAL]** Production systems need automated testing, deployment, and quality gates to ensure reliable releases.

### GitHub Actions Workflow

```yaml
# .github/workflows/user-portal-ci-cd.yml
name: User Portal CI/CD Pipeline

on:
  push:
    branches: [main, develop]
    paths: ['airaad/backend/user_portal/**', 'airaad/backend/customer_auth/**', 'airaad/backend/user_preferences/**']
  pull_request:
    branches: [main]
    paths: ['airaad/backend/user_portal/**', 'airaad/backend/customer_auth/**', 'airaad/backend/user_preferences/**']

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '18'

jobs:
  # Code Quality & Security
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          
      - name: Install dependencies
        run: |
          cd airaad/backend
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
          
      - name: Run Black (code formatting)
        run: black --check user_portal/ customer_auth/ user_preferences/
        
      - name: Run Flake8 (linting)
        run: flake8 user_portal/ customer_auth/ user_preferences/ --max-line-length=88 --extend-ignore=E203,W503
        
      - name: Run isort (import sorting)
        run: isort --check-only user_portal/ customer_auth/ user_preferences/
        
      - name: Run Bandit (security linter)
        run: bandit -r user_portal/ customer_auth/ user_preferences/ -f json -o bandit-report.json || true
        
      - name: Run Semgrep (security scanning)
        uses: semgrep/semgrep-action@v1
        with:
          config: auto
          
      - name: Upload security reports
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: bandit-report.json

  # Testing
  test:
    runs-on: ubuntu-latest
    needs: quality
    
    services:
      postgres:
        image: postgis/postgis:15-3.3
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_airad
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
          
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          
      - name: Install dependencies
        run: |
          cd airaad/backend
          pip install -r requirements.txt
          pip install -r requirements-test.txt
          
      - name: Run unit tests
        run: |
          cd airaad/backend
          coverage run --source=user_portal,customer_auth,user_preferences manage test
          coverage xml
          coverage report
          
      - name: Run integration tests
        run: |
          cd airaad/backend
          python manage.py test user_portal.tests.integration --keepdb
          
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: airaad/backend/coverage.xml
          flags: user-portal
          
      - name: Run API contract tests
        run: |
          cd airaad/backend
          python -m pytest user_portal/tests/api_contract/ -v

  # Performance Tests
  performance:
    runs-on: ubuntu-latest
    needs: test
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          
      - name: Install dependencies
        run: |
          cd airaad/backend
          pip install -r requirements.txt
          pip install locust
          
      - name: Run load tests
        run: |
          cd airaad/backend
          locust --config user_portal/tests/performance/locust.conf --headless --html performance-report.html
          
      - name: Upload performance report
        uses: actions/upload-artifact@v3
        with:
          name: performance-report
          path: airaad/backend/performance-report.html

  # Build & Deploy
  deploy:
    runs-on: ubuntu-latest
    needs: [test, performance]
    if: github.event_name == 'push'
    
    environment:
      name: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
      url: ${{ github.ref == 'refs/heads/main' && 'https://app.airad.pk' || 'https://staging.airad.pk' }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
          
      - name: Build Docker image
        run: |
          cd airaad/backend
          docker build -t airad-user-portal:${{ github.sha }} .
          docker tag airad-user-portal:${{ github.sha }} ${{ github.ref == 'refs/heads/main' && 'airad-user-portal:latest' || 'airad-user-portal:staging' }}
          
      - name: Push to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin ${{ secrets.ECR_REGISTRY }}
          docker push ${{ secrets.ECR_REGISTRY }}/airad-user-portal:${{ github.sha }}
          
      - name: Deploy to ECS
        run: |
          aws ecs update-service --cluster airad-${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }} --service user-portal --force-new-deployment
          
      - name: Run smoke tests
        run: |
          cd airaad/backend
          python -m pytest user_portal/tests/smoke/ --base-url=${{ github.ref == 'refs/heads/main' && 'https://app.airad.pk' || 'https://staging.airad.pk' }}
```

### 18.2 Environment Management

```python
# In settings/environment.py
import os
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

def get_environment() -> Environment:
    env = os.getenv('AIRAD_ENV', 'development').lower()
    return Environment(env)

# Environment-specific settings
ENV_CONFIG = {
    Environment.DEVELOPMENT: {
        'DEBUG': True,
        'DATABASE_URL': 'postgres://postgres:postgres@localhost:5432/airad_dev',
        'REDIS_URL': 'redis://localhost:6379/0',
        'ALLOWED_HOSTS': ['localhost', '127.0.0.1'],
        'CORS_ALLOWED_ORIGINS': ['http://localhost:3000'],
        'LOG_LEVEL': 'DEBUG',
        'SENTRY_DSN': None,
    },
    Environment.STAGING: {
        'DEBUG': False,
        'DATABASE_URL': os.getenv('STAGING_DATABASE_URL'),
        'REDIS_URL': os.getenv('STAGING_REDIS_URL'),
        'ALLOWED_HOSTS': ['staging.airad.pk', '*.staging.airad.pk'],
        'CORS_ALLOWED_ORIGINS': ['https://staging.airad.pk'],
        'LOG_LEVEL': 'INFO',
        'SENTRY_DSN': os.getenv('STAGING_SENTRY_DSN'),
    },
    Environment.PRODUCTION: {
        'DEBUG': False,
        'DATABASE_URL': os.getenv('PRODUCTION_DATABASE_URL'),
        'REDIS_URL': os.getenv('PRODUCTION_REDIS_URL'),
        'ALLOWED_HOSTS': ['app.airad.pk', '*.airad.pk'],
        'CORS_ALLOWED_ORIGINS': ['https://app.airad.pk'],
        'LOG_LEVEL': 'WARNING',
        'SENTRY_DSN': os.getenv('PRODUCTION_SENTRY_DSN'),
    }
}

current_env = get_environment()
config = ENV_CONFIG[current_env]
```

### 18.3 Monitoring & Alerting Strategy

```python
# In user_portal/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from django.http import HttpResponse
import time

# Prometheus metrics
REQUEST_COUNT = Counter(
    'user_portal_requests_total',
    'Total requests to User Portal',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'user_portal_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_USERS = Gauge(
    'user_portal_active_users',
    'Number of active users',
    ['user_type']  # guest, registered
)

API_ERRORS = Counter(
    'user_portal_api_errors_total',
    'Total API errors',
    ['error_type', 'severity']
)

class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.path
        ).observe(time.time() - start_time)
        
        # Track errors
        if response.status_code >= 400:
            API_ERRORS.labels(
                error_type=str(response.status_code),
                severity='high' if response.status_code >= 500 else 'medium'
            ).inc()
        
        return response

def metrics_view(request):
    """Prometheus metrics endpoint"""
    return HttpResponse(generate_latest(), content_type='text/plain')

# Health check endpoints
def health_check(request):
    """Basic health check"""
    return HttpResponse({'status': 'healthy'}, content_type='application/json')

def detailed_health_check(request):
    """Detailed health check with dependencies"""
    checks = {
        'database': check_database_connection(),
        'redis': check_redis_connection(),
        'celery': check_celery_workers(),
        'disk_space': check_disk_space(),
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return HttpResponse(
        {'status': 'healthy' if all_healthy else 'unhealthy', 'checks': checks},
        status=status_code,
        content_type='application/json'
    )
```

### 18.4 Data Backup & Recovery Strategy

```bash
#!/bin/bash
# scripts/backup_user_portal.sh

set -e

# Configuration
BACKUP_DIR="/backups/user_portal"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Database backup
echo "Starting database backup..."
pg_dump $DATABASE_URL | gzip > "$BACKUP_DIR/db_backup_$DATE.sql.gz"

# Redis backup
echo "Starting Redis backup..."
redis-cli --rdb "$BACKUP_DIR/redis_backup_$DATE.rdb"

# Media files backup
echo "Starting media files backup..."
aws s3 sync s3://airad-media/user_portal/ "$BACKUP_DIR/media_$DATE/" --delete

# Upload to S3
echo "Uploading backups to S3..."
aws s3 cp "$BACKUP_DIR/db_backup_$DATE.sql.gz" "s3://airad-backups/user_portal/database/"
aws s3 cp "$BACKUP_DIR/redis_backup_$DATE.rdb" "s3://airad-backups/user_portal/redis/"
aws s3 sync "$BACKUP_DIR/media_$DATE/" "s3://airad-backups/user_portal/media_$DATE/"

# Clean up old backups
echo "Cleaning up old backups..."
find $BACKUP_DIR -name "*.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.rdb" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "media_*" -mtime +$RETENTION_DAYS -exec rm -rf {} +

echo "Backup completed successfully!"
```

### 18.5 Security Hardening

```python
# In user_portal/security/middleware.py
class SecurityHeadersMiddleware:
    """Add security headers to all responses"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.mapbox.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.mapbox.com; "
            "media-src 'self' blob:; "
            "worker-src 'self' blob:;"
        )
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = (
            'camera=(), microphone=(), geolocation=(), '
            'payment=(), usb=(), magnetometer=(), gyroscope=()'
        )
        
        return response
```

---

## 19. BUILD SEQUENCE & QA

### Session UP-BE-S7 — Celery Tasks & Performance (2 hours)
- All 9 new Celery tasks (beat schedule registration)
- Redis cache layer integration
- Database index migrations (GiST, partial, compound)
- Rate limiting setup (DRF throttle classes)
- Performance verification against response time targets

### Session UP-BE-S8 — Testing & QA (3 hours)
- Unit tests: ranking algorithm, NLP keyword extraction, distance scoring
- Integration tests: all 35+ endpoints (status codes, response shapes, auth enforcement)
- Performance tests: response time validation with realistic data volume
- Security tests: JWT audience validation, rate limiting enforcement, GDPR deletion flow
- `manage.py check` → 0 issues
- `makemigrations --check` → no pending changes
- Test coverage maintained ≥ 79%

**Total estimated: 8 sessions, 18-22 hours**

---

## 20. QUALITY GATE CHECKLIST

### Correctness
- [ ] All 35+ endpoints return correct data per specification
- [ ] Ranking algorithm uses exact formula: Relevance×0.30 + Distance×0.25 + Offer×0.15 + Popularity×0.15 + Tier×0.15
- [ ] Tier scores (normalized 0–1): Silver=0.25, Gold=0.50, Diamond=0.75, Platinum=1.00 — NO separate global multiplier
- [ ] System tags applied post-scoring: `new_vendor_boost` +0.10, `trending` +0.05, `verified` +0.03
- [ ] Promotions strip endpoint `/discovery/promotions-strip/` returns all active promotions (not just flash deals)
- [ ] Flash deal alert filters to deals started within last 90 minutes only
- [ ] City selector endpoint `/discovery/cities/` returns cities + areas with vendor counts
- [ ] PostGIS ST_DWithin used — NEVER degree-based distance
- [ ] JWT audience claim `user-portal` — tokens not cross-compatible with other portals
- [ ] Voice bot: Silver vendors get 403 Forbidden, Gold+ get responses
- [ ] Flash deal alert: never re-alerts same user/guest for same discount_id

### Performance
- [ ] AR markers endpoint < 40ms cache hit, < 150ms cache miss
- [ ] Nearby vendors endpoint < 80ms cache hit, < 350ms cache miss
- [ ] All tracking endpoints respond in < 20ms (202 Accepted)
- [ ] Redis cache operational for all discovery endpoints
- [ ] No N+1 queries anywhere (verified with `django-debug-toolbar` in dev)

### Security
- [ ] Phone numbers encrypted with AES-256-GCM
- [ ] GPS data purged after 90 days (Celery task verified)
- [ ] Account deletion removes all PII
- [ ] Rate limiting active on all discovery and auth endpoints
- [ ] CORS restricted to User Portal frontend origin

### Privacy
- [ ] Camera feed never touches backend
- [ ] Voice transcripts purged after 90 days
- [ ] Guest mode works with zero PII collected
- [ ] Data export includes all user data + ConsentRecord rows (GDPR Article 20)
- [ ] Account deletion triggers 30-day grace period then hard delete (GDPR)
- [ ] ConsentRecord created on: first GPS grant, account registration, first mic use
- [ ] HealthCheck endpoint `/api/v1/health/` returns 200 OK (DB + Redis verified)
- [ ] `.well-known/apple-app-site-association` served correctly (iOS deep links)
- [ ] `.well-known/assetlinks.json` served correctly (Android deep links)
- [ ] Media files served via CDN URL (`media.airad.pk`) — no local Railway paths

### Architecture
- [ ] All business logic in `services.py` — never in views or serializers
- [ ] AuditLog entry on every account deletion and data export request
- [ ] Soft deletes only — `is_deleted=True`, never immediate hard delete
- [ ] `manage.py check` returns 0 issues
- [ ] `makemigrations --check` returns no pending changes
- [ ] Test coverage ≥ 79%

### Audit Fixes Verification
- [ ] Rate limit: 429 responses include `Retry-After` header (verify with curl; not stripped by Nginx/CORS)
- [ ] Guest pref migration: guest prefs + search history + flash alerts reassigned to user on login
- [ ] System tags: `new_vendor_boost`, `trending`, `verified` boosts applied AFTER weighted formula (unit test)
- [ ] Score cap: `final_score = min(final_score, 1.0)` — score never exceeds 1.0 (unit test)
- [ ] Promotions-strip: returns all active promotions (not just flash deals) — separate endpoint confirmed
- [ ] Cities endpoint: returns cities + areas with vendor counts per area
- [ ] Consent endpoint: POST `/auth/consent/` creates `ConsentRecord` rows for each consent type
- [ ] Navigation URLs: vendor detail response includes `google_maps_app`, `google_maps_web`, `apple_maps` URLs
- [ ] Guest migration: `login` endpoint accepts optional `guest_token` field, migration fires on match
- [ ] AR endpoint TTL: 30s (not 60s — shorter for AR real-time refresh cycle)

---

## 20. CI/CD PIPELINE INTEGRATION

> **[AUDIT FIX — CRITICAL]** Production applications need automated build, test, and deployment pipelines. Manual deployment doesn't scale and introduces human error risks.

### 20.1 CI/CD Architecture Overview

**Pipeline Stages:**
1. **Code Quality & Security** - Linting, formatting, security scanning
2. **Automated Testing** - Unit tests, integration tests, E2E tests
3. **Build & Package** - Docker image creation, artifact storage
4. **Environment Deployment** - Dev → Staging → Production
5. **Post-Deployment Verification** - Health checks, smoke tests

**Branch Strategy:**
- **`main`** - Production-ready code (auto-deploy to production)
- **`develop`** - Integration branch (auto-deploy to staging)
- **`feature/*`** - Feature branches (PR-based deployment to dev)

### 20.2 GitHub Actions Workflow

```yaml
# .github/workflows/user-portal-ci.yml
name: User Portal CI/CD Pipeline

on:
  push:
    branches: [main, develop, 'feature/*']
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: '3.11'
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  code-quality:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install dependencies
        run: |
          cd airaad/backend
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Code formatting check (Black)
        run: |
          cd airaad/backend
          black --check --diff .
      
      - name: Linting (flake8)
        run: |
          cd airaad/backend
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
      
      - name: Security scanning (bandit)
        run: |
          cd airaad/backend
          bandit -r user_portal/ -f json -o bandit-report.json
      
      - name: Secret scanning (TruffleHog)
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: main
          head: HEAD

  backend-tests:
    runs-on: ubuntu-latest
    needs: code-quality
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: airads_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install dependencies
        run: |
          cd airaad/backend
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run database migrations
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/airads_test
          REDIS_URL: redis://localhost:6379/0
        run: |
          cd airaad/backend
          python manage.py migrate
      
      - name: Run unit tests
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/airads_test
          REDIS_URL: redis://localhost:6379/0
          DJANGO_SETTINGS_MODULE: config.settings.test
        run: |
          cd airaad/backend
          pytest user_portal/tests/unit/ -v --cov=user_portal --cov-report=xml
      
      - name: Run integration tests
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/airads_test
          REDIS_URL: redis://localhost:6379/0
          DJANGO_SETTINGS_MODULE: config.settings.test
        run: |
          cd airaad/backend
          pytest user_portal/tests/integration/ -v --cov-append

  build-and-deploy:
    runs-on: ubuntu-latest
    needs: backend-tests
    if: github.event_name == 'push'
    outputs:
      backend-image: ${{ steps.meta.outputs.tags }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}
      
      - name: Build and push image
        uses: docker/build-push-action@v5
        with:
          context: ./airaad/backend
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy-staging:
    runs-on: ubuntu-latest
    needs: build-and-deploy
    if: github.ref == 'refs/heads/develop'
    environment: staging
    
    steps:
      - name: Deploy to Railway (Staging)
        uses: railway-app/railway-action@v1
        with:
          api-token: ${{ secrets.RAILWAY_TOKEN }}
          project-id: ${{ secrets.RAILWAY_PROJECT_ID }}
          environment-id: ${{ secrets.RAILWAY_STAGING_ENV_ID }}
          service: user-portal-backend
          image: ${{ needs.build-and-deploy.outputs.backend-image }}
      
      - name: Run smoke tests
        run: |
          sleep 60
          curl -f ${{ secrets.STAGING_API_URL }}/api/v1/health/ || exit 1
          curl -f ${{ secrets.STAGING_API_URL }}/api/v1/user-portal/nearby/?lat=24.8607&lng=67.0011&radius=1000 || exit 1

  deploy-production:
    runs-on: ubuntu-latest
    needs: build-and-deploy
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
      - name: Deploy to Railway (Production)
        uses: railway-app/railway-action@v1
        with:
          api-token: ${{ secrets.RAILWAY_TOKEN }}
          project-id: ${{ secrets.RAILWAY_PROJECT_ID }}
          environment-id: ${{ secrets.RAILWAY_PROD_ENV_ID }}
          service: user-portal-backend
          image: ${{ needs.build-and-deploy.outputs.backend-image }}
      
      - name: Run production verification
        run: |
          sleep 120
          curl -f ${{ secrets.PROD_API_URL }}/api/v1/health/ || exit 1
          curl -f ${{ secrets.PROD_API_URL }}/api/v1/user-portal/nearby/?lat=24.8607&lng=67.0011&radius=1000 || exit 1
```

### 20.3 Docker Configuration

```dockerfile
# airaad/backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ || exit 1

# Start command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]
```

### 20.4 Monitoring & Alerting Strategy

> **[AUDIT FIX — CRITICAL]** Production applications need comprehensive monitoring and alerting to detect issues before they impact users.

#### 20.4.1 Monitoring Architecture

**Monitoring Stack:**
- **Metrics Collection:** Prometheus + Django Prometheus Exporter
- **Logging:** ELK Stack (Elasticsearch, Logstash, Kibana)
- **Error Tracking:** Sentry
- **APM:** New Relic (Application Performance Monitoring)
- **Uptime Monitoring:** UptimeRobot + custom health checks

**Alerting Channels:**
- **Critical:** PagerDuty (on-call rotation)
- **High:** Slack (#alerts channel)
- **Medium:** Email (devops team)
- **Low:** Dashboard notifications

#### 20.4.2 Metrics Collection System

```python
# In user_portal/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from django.http import HttpResponse
import time
import psutil

# Business Metrics
api_requests_total = Counter(
    'airads_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status_code', 'user_type']
)

api_request_duration = Histogram(
    'airads_api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint', 'user_type'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

active_users = Gauge(
    'airads_active_users',
    'Number of currently active users',
    ['user_type']
)

vendor_discovery_calls = Counter(
    'airads_vendor_discovery_calls_total',
    'Total vendor discovery API calls',
    ['location', 'radius', 'result_count']
)

# Infrastructure Metrics
database_connections = Gauge(
    'airads_database_connections',
    'Active database connections'
)

redis_memory_usage = Gauge(
    'airads_redis_memory_usage_bytes',
    'Redis memory usage in bytes'
)

class PrometheusMiddleware:
    """Django middleware for Prometheus metrics collection"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        # Record request metrics
        duration = time.time() - start_time
        
        # Extract user type from request
        user_type = 'anonymous'
        if hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'customer_profile'):
                user_type = 'customer'
            elif hasattr(request.user, 'vendor_profile'):
                user_type = 'vendor'
        
        # Record metrics
        api_requests_total.labels(
            method=request.method,
            endpoint=self._get_endpoint_name(request),
            status_code=response.status_code,
            user_type=user_type
        ).inc()
        
        api_request_duration.labels(
            method=request.method,
            endpoint=self._get_endpoint_name(request),
            user_type=user_type
        ).observe(duration)
        
        return response
    
    def _get_endpoint_name(self, request):
        """Extract endpoint name from request path"""
        path = request.path
        if '/api/v1/user-portal/' in path:
            return path.split('/api/v1/user-portal/')[-1].split('/')[0] or 'root'
        return 'unknown'

def metrics_view(request):
    """Prometheus metrics endpoint"""
    return HttpResponse(generate_latest(), content_type='text/plain')
```

#### 20.4.3 Alerting System

```python
# In user_portal/monitoring/alerts.py
from celery import shared_task
from django.conf import settings
from datetime import datetime, timedelta
import requests
import json

class AlertService:
    """Alerting Service for system notifications"""
    
    ALERT_THRESHOLDS = {
        'api_response_time': {'warning': 2.0, 'critical': 5.0},
        'error_rate': {'warning': 0.05, 'critical': 0.10},
        'database_connections': {'warning': 80, 'critical': 95},
        'redis_memory': {'warning': 0.80, 'critical': 0.95},
        'disk_usage': {'warning': 0.80, 'critical': 0.95},
        'cpu_usage': {'warning': 0.80, 'critical': 0.95}
    }
    
    @staticmethod
    def check_system_health():
        """Check overall system health"""
        health_checks = {
            'database': AlertService._check_database_health(),
            'redis': AlertService._check_redis_health(),
            'api': AlertService._check_api_health(),
            'disk': AlertService._check_disk_health(),
            'cpu': AlertService._check_cpu_health(),
        }
        
        overall_status = 'healthy'
        issues = []
        
        for component, health in health_checks.items():
            if health['status'] == 'critical':
                overall_status = 'critical'
                issues.append(f"{component}: {health['message']}")
            elif health['status'] == 'warning' and overall_status != 'critical':
                overall_status = 'warning'
                issues.append(f"{component}: {health['message']}")
        
        # Send alert if there are issues
        if overall_status in ['warning', 'critical']:
            AlertService._send_alert(
                alert_type='system_health',
                severity=overall_status,
                message=f"System health: {overall_status}",
                details={'issues': issues}
            )
        
        return overall_status
    
    @staticmethod
    def _check_database_health():
        """Check database health"""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.execute("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """)
                active_connections = cursor.fetchone()[0]
                
                max_connections = 100
                connection_ratio = active_connections / max_connections
                
                if connection_ratio > AlertService.ALERT_THRESHOLDS['database_connections']['critical']:
                    return {
                        'status': 'critical',
                        'message': f'Too many active connections: {active_connections}/{max_connections}'
                    }
                elif connection_ratio > AlertService.ALERT_THRESHOLDS['database_connections']['warning']:
                    return {
                        'status': 'warning',
                        'message': f'High connection count: {active_connections}/{max_connections}'
                    }
                
                return {'status': 'healthy', 'message': 'Database operating normally'}
        
        except Exception as e:
            return {
                'status': 'critical',
                'message': f'Database connection failed: {str(e)}'
            }
    
    @staticmethod
    def _send_alert(alert_type, severity, message, details=None):
        """Send alert through appropriate channels"""
        
        # Send to Slack
        if hasattr(settings, 'SLACK_WEBHOOK_URL'):
            color = {'warning': 'warning', 'critical': 'danger'}.get(severity, 'good')
            
            slack_payload = {
                'text': f'🚨 {severity.title()} Alert: {alert_type}',
                'attachments': [{
                    'color': color,
                    'title': message,
                    'text': json.dumps(details, indent=2) if details else '',
                    'ts': datetime.utcnow().timestamp()
                }]
            }
            
            try:
                requests.post(settings.SLACK_WEBHOOK_URL, json=slack_payload, timeout=10)
            except Exception as e:
                import logging
                logging.error(f"Failed to send Slack alert: {e}")

# Celery task for monitoring
@shared_task(name='monitoring.check_system_health')
def check_system_health():
    """Periodic system health check"""
    AlertService.check_system_health()
```

---

## 21. API VERSIONING STRATEGY

> **[AUDIT FIX — CRITICAL]** Production APIs need versioning for backward compatibility and smooth evolution.

### 21.1 Versioning Architecture

**Versioning Strategy:**
- **URL Path Versioning:** `/api/v1/`, `/api/v2/`, etc.
- **Semantic Versioning:** Major.Minor.Patch (e.g., v1.2.3)
- **Backward Compatibility:** Support at least 2 previous major versions
- **Deprecation Timeline:** 6 months deprecation notice, 12 months removal

### 21.2 URL Router Configuration

```python
# In config/urls.py
from django.urls import path, include
from django.conf import settings
from django.http import JsonResponse

def api_version_info(request):
    """Return API version information"""
    versions = {
        'v1': {
            'status': 'stable',
            'deprecated': False,
            'sunset_date': None,
            'released': '2026-02-01'
        }
    }
    
    return JsonResponse({
        'current_version': 'v1',
        'supported_versions': versions,
        'default_version': 'v1'
    })

urlpatterns = [
    path('api/', api_version_info, name='api_version_info'),
    path('api/v1/', include('user_portal.urls_v1')),
]

# Version-specific URL modules
# user_portal/urls_v1.py
from django.urls import path, include
from . import views as v1_views

urlpatterns_v1 = [
    path('user-portal/', include([
        path('auth/', include([
            path('login/', v1_views.LoginView.as_view(), name='login'),
            path('logout/', v1_views.LogoutView.as_view(), name='logout'),
            path('register/', v1_views.RegisterView.as_view(), name='register'),
        ])),
        path('discovery/', include([
            path('nearby/', v1_views.NearbyVendorsView.as_view(), name='nearby_vendors'),
            path('ar-markers/', v1_views.ARMarkersView.as_view(), name='ar_markers'),
            path('tags/', v1_views.TagsView.as_view(), name='tags'),
            path('voice-search/', v1_views.VoiceSearchView.as_view(), name='voice_search'),
        ])),
        path('vendors/', include([
            path('<uuid:vendor_id>/', v1_views.VendorDetailView.as_view(), name='vendor_detail'),
        ])),
        path('health/', v1_views.HealthCheckView.as_view(), name='health_check'),
    ])),
]
```

### 21.3 Version-Aware View Mixins

```python
# In user_portal/mixins.py
from django.http import HttpResponse
from rest_framework.response import Response

class APIVersionMixin:
    """Mixin to handle API versioning in views"""
    
    def get_api_version(self):
        """Extract API version from request"""
        path = self.request.path
        if '/api/v1/' in path:
            return 'v1'
        elif '/api/v2/' in path:
            return 'v2'
        else:
            return 'v1'  # Default to v1
    
    def get_serializer_class(self):
        """Return version-specific serializer"""
        version = self.get_api_version()
        serializer_class = getattr(self, f'serializer_class_{version}', None)
        return serializer_class or super().get_serializer_class()
    
    def handle_version_deprecation(self):
        """Handle deprecated API versions"""
        version = self.get_api_version()
        
        # Check if version is deprecated
        deprecated_versions = getattr(settings, 'DEPRECATED_API_VERSIONS', {})
        
        if version in deprecated_versions:
            sunset_date = deprecated_versions[version]['sunset_date']
            warning_message = deprecated_versions[version]['warning_message']
            
            # Add deprecation headers
            self.response['X-API-Deprecated'] = 'true'
            self.response['X-API-Sunset-Date'] = sunset_date
            self.response['X-API-Warning'] = warning_message

class APIVersioningMiddleware:
    """Middleware to handle API versioning"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Add version information to request
        request.api_version = self._extract_version(request)
        
        response = self.get_response(request)
        
        # Add version headers
        response['X-API-Version'] = request.api_version
        response['X-API-Supported-Versions'] = 'v1,v2'
        
        return response
    
    def _extract_version(self, request):
        """Extract API version from request"""
        path = request.path
        
        if '/api/v1/' in path:
            return 'v1'
        elif '/api/v2/' in path:
            return 'v2'
        elif '/api/' in path:
            return 'v1'  # Default to v1 for /api/ without version
        
        return None
```

---

## 22. BACKEND OPTIMIZATION (SPEED vs OVER-ENGINEERING)

> **[AUDIT FIX — CRITICAL]** Balance feature completeness with performance. Remove over-engineering that impacts speed.

### 22.1 Performance Optimization Strategy

**Optimization Principles:**
- **80/20 Rule:** Focus on 20% of code that handles 80% of requests
- **Lazy Loading:** Load data only when needed
- **Caching First:** Cache aggressively, invalidate selectively
- **Database Efficiency:** Optimize queries, use indexes wisely
- **Async Processing:** Move heavy operations to background tasks

**Performance Targets:**
- **API Response Time:** < 200ms (95th percentile)
- **Database Query Time:** < 50ms (average)
- **Cache Hit Rate:** > 90%
- **Memory Usage:** < 512MB per worker
- **CPU Usage:** < 70% average

### 22.2 Database Optimization

```python
# In user_portal/optimization/database.py
from django.db import connection
from django.core.cache import cache
from .models import Vendor, Promotion

class OptimizedQueryManager:
    """Optimized database query manager"""
    
    @staticmethod
    def get_nearby_vendors_optimized(lat, lng, radius, limit=50):
        """Optimized nearby vendors query with caching"""
        
        # Create cache key
        cache_key = f"nearby_vendors_{lat:.4f}_{lng:.4f}_{radius}_{limit}"
        
        # Try cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Optimized query with spatial indexing
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT v.id, v.name, v.description, v.address, 
                       v.category, v.tier, v.is_verified,
                       ST_Distance(v.location::geography, ST_MakePoint(%s, %s)::geography) as distance,
                       p.id as promotion_id, p.title as promotion_title,
                       p.discount_percent, p.is_flash_deal
                FROM user_portal_vendor v
                LEFT JOIN user_portal_promotion p ON v.id = p.vendor_id 
                    AND p.is_active = true 
                    AND p.start_time <= NOW() 
                    AND p.end_time >= NOW()
                WHERE ST_DWithin(v.location::geography, ST_MakePoint(%s, %s)::geography, %s)
                    AND v.is_active = true
                ORDER BY distance, 
                         CASE v.tier 
                             WHEN 'PLATINUM' THEN 1
                             WHEN 'DIAMOND' THEN 2
                             WHEN 'GOLD' THEN 3
                             WHEN 'SILVER' THEN 4
                             ELSE 5
                         END,
                         p.is_flash_deal DESC,
                         v.created_at DESC
                LIMIT %s
            """, [lng, lat, lng, lat, radius, limit])
            
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Cache for 5 minutes
        cache.set(cache_key, results, timeout=300)
        
        return results
    
    @staticmethod
    def get_ar_markers_optimized(lat, lng, radius, user_tier='SILVER'):
        """Optimized AR markers query with tier limits"""
        
        # Tier-based limits
        tier_limits = {
            'SILVER': 10,
            'GOLD': 25,
            'DIAMOND': 50,
            'PLATINUM': 100
        }
        
        limit = tier_limits.get(user_tier, 10)
        cache_key = f"ar_markers_{lat:.4f}_{lng:.4f}_{radius}_{user_tier}"
        
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Optimized spatial query
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT v.id, v.name, v.category, v.tier,
                       ST_X(v.location) as lng, ST_Y(v.location) as lat,
                       ST_Distance(v.location::geography, ST_MakePoint(%s, %s)::geography) as distance,
                       p.id as promotion_id, p.title as promotion_title, p.is_flash_deal
                FROM user_portal_vendor v
                LEFT JOIN user_portal_promotion p ON v.id = p.vendor_id 
                    AND p.is_active = true 
                    AND p.start_time <= NOW() 
                    AND p.end_time >= NOW()
                WHERE ST_DWithin(v.location::geography, ST_MakePoint(%s, %s)::geography, %s)
                    AND v.is_active = true
                ORDER BY distance, v.tier DESC, p.is_flash_deal DESC
                LIMIT %s
            """, [lng, lat, lng, lat, radius, limit])
            
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Cache for 30 seconds (AR needs fresh data)
        cache.set(cache_key, results, timeout=30)
        
        return results
```

### 22.3 Caching Strategy

```python
# In user_portal/optimization/cache.py
from django.core.cache import cache
from django.conf import settings
import hashlib

class CacheManager:
    """Advanced caching manager"""
    
    CACHE_TIMEOUTS = {
        'nearby_vendors': 300,      # 5 minutes
        'ar_markers': 30,           # 30 seconds (real-time)
        'vendor_detail': 600,       # 10 minutes
        'tags': 3600,               # 1 hour
        'promotions': 180,          # 3 minutes
        'user_preferences': 3600,    # 1 hour
        'cities': 86400,            # 24 hours
    }
    
    @staticmethod
    def get_cached_data(key, data_type, callback, *args, **kwargs):
        """Get cached data or execute callback and cache result"""
        
        cache_key = f"{data_type}:{key}"
        
        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Execute callback to get fresh data
        fresh_data = callback(*args, **kwargs)
        
        # Cache the result
        timeout = CacheManager.CACHE_TIMEOUTS.get(data_type, 300)
        cache.set(cache_key, fresh_data, timeout=timeout)
        
        return fresh_data
    
    @staticmethod
    def invalidate_cache_pattern(pattern):
        """Invalidate cache keys matching pattern"""
        # Implementation depends on cache backend
        if hasattr(cache, 'keys'):  # Redis backend
            import redis
            r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=1)
            keys = r.keys(f"*{pattern}*")
            for key in keys:
                cache.delete(key.decode('utf-8'))

class SmartCacheMiddleware:
    """Smart caching middleware"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only cache GET requests
        if request.method != 'GET':
            return self.get_response(request)
        
        # Generate cache key based on URL and user
        cache_key = self._generate_cache_key(request)
        
        # Try to get cached response
        cached_response = cache.get(cache_key)
        if cached_response:
            return cached_response
        
        # Get fresh response
        response = self.get_response(request)
        
        # Cache successful GET responses
        if response.status_code == 200 and self._should_cache_response(request, response):
            timeout = self._get_cache_timeout(request.path)
            cache.set(cache_key, response, timeout=timeout)
        
        return response
    
    def _generate_cache_key(self, request):
        """Generate cache key for request"""
        path = request.path
        query_string = request.META.get('QUERY_STRING', '')
        
        # Add user tier if authenticated
        user_tier = 'anonymous'
        if hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'customer_profile'):
                user_tier = getattr(request.user.customer_profile, 'subscription_tier', 'SILVER')
        
        # Create hash for consistency
        key_string = f"{path}:{query_string}:{user_tier}"
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"response:{key_hash}"
    
    def _get_cache_timeout(self, path):
        """Get cache timeout based on endpoint"""
        if '/ar-markers/' in path:
            return 30  # 30 seconds for AR
        elif '/nearby/' in path:
            return 300  # 5 minutes for nearby vendors
        elif '/tags/' in path:
            return 3600  # 1 hour for tags
        else:
            return 600  # 10 minutes default
```

### 22.4 Performance Monitoring

```python
# In user_portal/optimization/monitoring.py
import time
import psutil
from django.db import connection

class PerformanceMonitor:
    """Monitor and optimize performance"""
    
    @staticmethod
    def monitor_request_performance(view_func):
        """Decorator to monitor view performance"""
        def wrapper(request, *args, **kwargs):
            start_time = time.time()
            
            # Get initial metrics
            initial_queries = len(connection.queries)
            
            # Execute view
            response = view_func(request, *args, **kwargs)
            
            # Calculate metrics
            duration = time.time() - start_time
            query_count = len(connection.queries) - initial_queries
            
            # Record metrics (would integrate with APM service)
            print(f"View {view_func.__name__}: {duration:.3f}s, {query_count} queries")
            
            # Alert on slow performance
            if duration > 2.0:  # 2 seconds threshold
                print(f"WARNING: Slow view {view_func.__name__} took {duration:.2f}s")
            
            return response
        
        return wrapper
    
    @staticmethod
    def get_system_metrics():
        """Get current system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Database connections
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                db_connections = cursor.fetchone()[0]
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': (disk.used / disk.total) * 100,
                'database_connections': db_connections,
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {'error': str(e)}

# Usage example:
# @PerformanceMonitor.monitor_request_performance
# def nearby_vendors_view(request):
#     # View logic here
#     pass
```

---

*USER PORTAL BACKEND PLAN — COMPLETE (Part 1 + Part 2)*
*Version: 1.0 | February 2026 | Source of Truth: AirAds_User_Portal_Super_Master_Prompt.md UP-0 through UP-13*
