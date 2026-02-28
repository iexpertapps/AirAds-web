# AirAd — FLUTTER MOBILE APP MASTER PLAN
## Customer Discovery + Vendor Mobile Management — Flutter 3.x + Dart
### Phase B Only — Built AFTER Backend + Frontend are Stable

**Version:** 2.0 — Full Build Plan  
**Date:** February 2026  
**Status:** AUTHORITATIVE — Supersedes `03_FLUTTER_MOBILE_PLAN.md`  
**Prerequisite:** Backend Phase B APIs stable + tested. Vendor Portal frontend complete.
**Subscription Ref:** `requirements/AirAd Phase-1 – Tiered Vendor Subscription Architecture-2.md`
**Value Ladder:** Visibility (Silver) → Control (Gold) → Automation (Diamond) → Dominance (Platinum)

---

## TABLE OF CONTENTS

1. [Product Vision & User Modes](#1-product-vision--user-modes)
2. [Tech Stack](#2-tech-stack)
3. [Architecture & Project Structure](#3-architecture--project-structure)
4. [Theming & Branding](#4-theming--branding)
5. [Navigation & Route Guards](#5-navigation--route-guards)
6. [Core Infrastructure](#6-core-infrastructure)
7. [Feature: Onboarding & Auth](#7-onboarding--auth)
8. [Feature: Customer Discovery (AR + Map + Voice + Tags)](#8-customer-discovery)
9. [Feature: Vendor Profile & Reels](#9-vendor-profile--reels)
10. [Feature: Navigation & Directions](#10-navigation--directions)
11. [Feature: Vendor App (Claim + Manage)](#11-vendor-app)
12. [Offline Strategy](#12-offline-strategy)
13. [Push Notifications](#13-push-notifications)
14. [State Management Patterns](#14-state-management-patterns)
15. [Testing Strategy](#15-testing-strategy)
16. [Build Sequence & Sessions](#16-build-sequence--sessions)
17. [Quality Gate Checklist](#17-quality-gate-checklist)
18. [Non-Negotiable Rules](#18-non-negotiable-rules)

---

## 1. PRODUCT VISION & USER MODES

### The Core Question AirAd Answers

**"What can I get right now, near me, with value?"**

### Single App, Two Modes

The Flutter app serves **both customers and vendors** from a single codebase. The user selects their mode during onboarding, and the app adapts its entire UI accordingly.

**Customer Mode — Discovery-First:**
- AR camera view with floating vendor bubbles (signature feature)
- Voice-driven search ("cheap pizza nearby")
- Tag-based browsing (categories, intents, time, deals)
- Vendor profiles with reels, discounts, navigation
- Minimal friction: no mandatory signup, GPS + camera as primary inputs

**Vendor Mode — Management-Lite:**
- Claim business flow (search → verify → setup)
- Quick discount creation (optimized for speed, not detail)
- Reel upload with trim editor
- Performance overview (simplified analytics)
- Complex management → "Open web portal" link

### User Personas Served

| Persona | Mode | Primary Interaction | Key Feature |
|---|---|---|---|
| Hungry Professional | Customer | Voice search | "Cheap lunch near me under 300" |
| Weekend Explorer | Customer | AR camera | Discover spots while walking |
| Bargain Hunter | Customer | Tag browsing | Filter by "Discounts Live" |
| Late-Night Snacker | Customer | Tags + voice | "What's open now for food?" |
| Micro-Vendor Owner | Vendor | Quick discount | "20% off next 2 hours" |
| Restaurant Manager | Vendor | Reel upload | Showcase daily specials |

---

## 2. TECH STACK

| Package | Purpose | Why |
|---|---|---|
| **Flutter 3.x + Dart (null-safety)** | Framework | Cross-platform, single codebase iOS + Android |
| **flutter_riverpod** | State management | Type-safe, testable, granular rebuilds |
| **go_router** | Navigation | Deep link support, declarative guards |
| **dio** | HTTP client | Interceptors for JWT + caching |
| **flutter_secure_storage** | Token storage | Keychain (iOS) / Keystore (Android) |
| **google_maps_flutter** | Map view | Standard map rendering + custom markers |
| **ar_flutter_plugin** | AR camera | AR marker rendering on camera feed |
| **speech_to_text** | Voice recognition | On-device speech → text |
| **flutter_tts** | Text to speech | Voice bot response playback |
| **camera** | Camera access | AR view + video recording |
| **image_picker** | Gallery access | Video selection for reels |
| **video_player** | Reel playback | Vendor profile reel viewing |
| **connectivity_plus** | Network state | Offline detection + banner |
| **geolocator** | GPS location | Real-time position tracking |
| **flutter_compass** | Compass heading | AR bubble positioning |
| **url_launcher** | External links | Google Maps / Apple Maps navigation |
| **google_fonts** | Typography | DM Sans consistency |
| **cached_network_image** | Image caching | S3 presigned URL images |
| **dio_cache_interceptor** | API caching | Offline response fallback |
| **flutter_local_notifications** | Local notifications | Foreground push display |
| **firebase_messaging** | FCM push | Remote push notifications |
| **permission_handler** | Permissions | Unified permission management |
| **shimmer** | Loading states | Skeleton loading animations |
| **lottie** | Micro-animations | Onboarding, success states |
| **share_plus** | Sharing | Share vendor profiles |
| **path_provider** | File paths | Video temp storage |
| **video_compress** | Video processing | Trim + compress before upload |

---

## 3. ARCHITECTURE & PROJECT STRUCTURE

### Feature-Based Architecture

Every feature is self-contained with its own models, providers, screens, and widgets. Cross-feature communication happens only through `core/` providers.

```
mobile/
├── lib/
│   ├── main.dart                          # Entry: ProviderScope, GoRouter, ThemeData
│   │
│   ├── core/
│   │   ├── api/
│   │   │   ├── api_client.dart            # Dio + JWT interceptor + refresh + cache
│   │   │   └── api_endpoints.dart         # All endpoint URL constants
│   │   ├── auth/
│   │   │   ├── auth_provider.dart         # Riverpod: AuthState (user, token, type)
│   │   │   ├── auth_service.dart          # Login, verify OTP, refresh, logout
│   │   │   └── token_storage.dart         # flutter_secure_storage wrapper
│   │   ├── theme/
│   │   │   ├── app_theme.dart             # ThemeData light + dark
│   │   │   ├── app_colors.dart            # Brand colors (matches DLS exactly)
│   │   │   └── app_typography.dart        # DM Sans text styles
│   │   ├── router/
│   │   │   └── app_router.dart            # GoRouter config + auth guards
│   │   ├── permissions/
│   │   │   └── permissions_service.dart   # Location, Mic, Camera with rationale
│   │   ├── connectivity/
│   │   │   └── connectivity_provider.dart # Network state Riverpod provider
│   │   ├── location/
│   │   │   └── location_provider.dart     # GPS StreamProvider
│   │   └── utils/
│   │       ├── distance_formatter.dart    # "80m", "1.2km"
│   │       ├── time_formatter.dart        # "2 min ago", "Open until 10 PM"
│   │       ├── currency_formatter.dart    # "PKR 3,000", "₨3,000"
│   │       └── phone_formatter.dart       # "*********4567"
│   │
│   ├── features/
│   │   ├── onboarding/
│   │   │   ├── models/
│   │   │   ├── providers/
│   │   │   └── screens/
│   │   │       ├── splash_screen.dart
│   │   │       ├── onboarding_screen.dart       # 3 swipeable intro screens
│   │   │       └── role_selection_screen.dart    # Customer or Vendor
│   │   │
│   │   ├── auth/
│   │   │   ├── models/
│   │   │   │   └── otp_state.dart
│   │   │   ├── providers/
│   │   │   │   └── otp_provider.dart
│   │   │   └── screens/
│   │   │       ├── phone_entry_screen.dart
│   │   │       └── otp_screen.dart
│   │   │
│   │   ├── discovery/
│   │   │   ├── models/
│   │   │   │   ├── vendor_summary.dart
│   │   │   │   └── search_filters.dart
│   │   │   ├── providers/
│   │   │   │   ├── discovery_provider.dart       # Vendors list + pagination
│   │   │   │   └── search_provider.dart          # Active filters + query
│   │   │   └── screens/
│   │   │       ├── discover_screen.dart           # Main home tab
│   │   │       └── widgets/
│   │   │           ├── vendor_card.dart
│   │   │           ├── filter_chips_row.dart
│   │   │           └── search_bar.dart
│   │   │
│   │   ├── ar/
│   │   │   ├── models/
│   │   │   │   └── ar_vendor_bubble.dart
│   │   │   ├── providers/
│   │   │   │   └── ar_provider.dart              # Compass + GPS + vendor positions
│   │   │   └── screens/
│   │   │       ├── ar_camera_screen.dart
│   │   │       └── widgets/
│   │   │           ├── vendor_bubble.dart         # Floating AR bubble widget
│   │   │           └── ar_bottom_sheet.dart       # Expandable vendor list
│   │   │
│   │   ├── map/
│   │   │   ├── providers/
│   │   │   │   └── map_provider.dart
│   │   │   └── screens/
│   │   │       ├── map_screen.dart
│   │   │       └── widgets/
│   │   │           ├── vendor_pin.dart
│   │   │           ├── cluster_pin.dart
│   │   │           └── vendor_summary_sheet.dart
│   │   │
│   │   ├── tags/
│   │   │   ├── models/
│   │   │   │   └── tag_group.dart
│   │   │   ├── providers/
│   │   │   │   └── tags_provider.dart
│   │   │   └── screens/
│   │   │       └── tags_browser_screen.dart
│   │   │
│   │   ├── voice/
│   │   │   ├── models/
│   │   │   │   └── voice_query_result.dart
│   │   │   ├── providers/
│   │   │   │   └── voice_provider.dart
│   │   │   └── screens/
│   │   │       ├── voice_search_overlay.dart      # Full-screen search UI
│   │   │       └── voice_bot_overlay.dart          # Vendor-specific Q&A
│   │   │
│   │   ├── vendor_profile/
│   │   │   ├── models/
│   │   │   │   └── vendor_detail.dart
│   │   │   ├── providers/
│   │   │   │   └── vendor_detail_provider.dart
│   │   │   └── screens/
│   │   │       ├── vendor_profile_screen.dart
│   │   │       └── widgets/
│   │   │           ├── reel_strip.dart
│   │   │           ├── discount_card.dart
│   │   │           ├── hours_section.dart
│   │   │           ├── action_row.dart
│   │   │           └── voice_bot_button.dart
│   │   │
│   │   ├── reels/
│   │   │   ├── providers/
│   │   │   │   ├── reel_player_provider.dart
│   │   │   │   └── reels_feed_provider.dart      # Nearby reels feed (End User §6.1)
│   │   │   └── screens/
│   │   │       ├── reel_fullscreen_player.dart
│   │   │       └── reels_feed_screen.dart        # Customer reels feed tab
│   │   │
│   │   ├── navigation/
│   │   │   ├── providers/
│   │   │   │   └── navigation_provider.dart
│   │   │   └── screens/
│   │   │       └── navigation_screen.dart
│   │   │
│   │   ├── saved/
│   │   │   ├── providers/
│   │   │   │   └── saved_vendors_provider.dart
│   │   │   └── screens/
│   │   │       └── saved_vendors_screen.dart
│   │   │
│   │   ├── profile/
│   │   │   └── screens/
│   │   │       ├── customer_profile_screen.dart
│   │   │       └── settings_screen.dart
│   │   │
│   │   └── vendor_app/                            # VENDOR MODE
│   │       ├── claim/
│   │       │   ├── models/
│   │       │   │   └── claim_state.dart
│   │       │   ├── providers/
│   │       │   │   └── claim_provider.dart
│   │       │   └── screens/
│   │       │       ├── find_business_screen.dart
│   │       │       ├── claim_confirm_screen.dart
│   │       │       └── pending_claim_screen.dart
│   │       ├── business/
│   │       │   ├── providers/
│   │       │   │   └── vendor_profile_provider.dart
│   │       │   └── screens/
│   │       │       └── vendor_profile_edit_screen.dart
│   │       ├── discounts/
│   │       │   ├── providers/
│   │       │   │   └── vendor_discounts_provider.dart
│   │       │   └── screens/
│   │       │       ├── discount_manager_screen.dart
│   │       │       └── widgets/
│   │       │           ├── active_discount_card.dart
│   │       │           └── quick_create_sheet.dart
│   │       ├── media/
│   │       │   ├── providers/
│   │       │   │   └── reel_upload_provider.dart
│   │       │   └── screens/
│   │       │       ├── reel_management_screen.dart
│   │       │       ├── video_upload_screen.dart
│   │       │       └── video_trim_screen.dart
│   │       └── performance/
│   │           ├── providers/
│   │           │   └── performance_provider.dart
│   │           └── screens/
│   │               └── performance_screen.dart
│   │
│   └── widgets/                                   # Shared widgets
│       ├── offline_banner.dart
│       ├── shimmer_loading.dart
│       ├── error_state.dart
│       ├── empty_state.dart
│       └── tier_badge.dart
│
├── test/
│   ├── unit/
│   │   ├── ranking_service_test.dart
│   │   ├── voice_parser_test.dart
│   │   ├── distance_formatter_test.dart
│   │   ├── feature_gate_test.dart
│   │   └── currency_formatter_test.dart
│   ├── widget/
│   │   ├── vendor_card_test.dart
│   │   ├── otp_screen_test.dart
│   │   ├── discount_card_test.dart
│   │   └── voice_search_overlay_test.dart
│   └── integration/
│       ├── auth_flow_test.dart
│       ├── discovery_flow_test.dart
│       └── claim_flow_test.dart
│
├── pubspec.yaml
├── analysis_options.yaml
└── README.md
```

---

## 4. THEMING & BRANDING

### Brand Colors (Exact Match to Web DLS)

```dart
class AppColors {
  // Brand — matches DLS tokens exactly
  static const rausch    = Color(0xFFFF5A5F);  // Primary CTA
  static const babu      = Color(0xFF00A699);  // Success / approved
  static const arches    = Color(0xFFFC642D);  // Warning / pending
  static const hof       = Color(0xFF484848);  // Primary text
  static const foggy     = Color(0xFF767676);  // Secondary text

  // Light mode
  static const background = Color(0xFFF7F7F7);
  static const surface    = Color(0xFFFFFFFF);
  static const border     = Color(0xFFDDDDDD);

  // Dark mode (higher saturation for outdoor readability)
  static const darkBackground = Color(0xFF121212);
  static const darkSurface    = Color(0xFF1E1E1E);
  static const darkRausch     = Color(0xFFFF6B6F);
  static const darkBabu       = Color(0xFF00B8AA);
  static const darkBorder     = Color(0xFF333333);

  // Semantic
  static const success     = Color(0xFF008A05);
  static const successBg   = Color(0xFFE8F5E9);
  static const warning     = Color(0xFFC45300);
  static const warningBg   = Color(0xFFFFF3E0);
  static const error       = Color(0xFFC13515);
  static const errorBg     = Color(0xFFFFEBEE);

  // Subscription tier colors
  static const silverTier   = Color(0xFF9E9E9E);
  static const goldTier     = Color(0xFFFFD700);
  static const diamondTier  = Color(0xFF4FC3F7);
  static const platinumTier = Color(0xFF7E57C2);
}
```

### Typography

```dart
// DM Sans via google_fonts package
// All text styles use DM Sans exclusively
// Light mode: hof (dark grey) for primary, foggy for secondary
// Dark mode: white for primary, grey-400 for secondary
```

### Theme Mode

- **System default** — respects device light/dark setting
- Dark mode tested on ALL screens (outdoor AR use case)
- High contrast mode option in settings (for sunlight readability)

---

## 5. NAVIGATION & ROUTE GUARDS

### Route Structure

```
/splash                              → SplashScreen
/onboarding                          → OnboardingScreen (3 swipeable pages)
/role-selection                      → RoleSelectionScreen

/auth/phone                          → PhoneEntryScreen
/auth/otp                            → OtpScreen

--- Customer Mode ---
/discover                            → DiscoverScreen (home tab)
/discover/ar                         → ARCameraScreen (full-screen)
/reels                               → ReelsFeedScreen (reels tab — End User §6.1)
/map                                 → MapScreen (map tab)
/tags                                → TagsBrowserScreen (browse tab)
/saved                               → SavedVendorsScreen (saved tab)
/profile                             → CustomerProfileScreen (profile tab)
/vendor/:slug                        → VendorProfileScreen
/vendor/:slug/navigate               → NavigationScreen
/vendor/:slug/reel/:reelId           → ReelFullscreenPlayer

--- Vendor Mode ---
/vendor-app/find                     → FindBusinessScreen
/vendor-app/claim/:id                → ClaimConfirmScreen
/vendor-app/pending                  → PendingClaimScreen
/vendor-app/business                 → VendorProfileEditScreen (home tab)
/vendor-app/discounts                → DiscountManagerScreen (discounts tab)
/vendor-app/media                    → ReelManagementScreen (media tab)
/vendor-app/performance              → PerformanceScreen (performance tab)
/vendor-app/settings                 → VendorSettingsScreen
```

### Route Guard Logic

```dart
// GoRouter redirect:
// 1. No token → /splash → /onboarding OR /auth/phone
// 2. Valid token + CUSTOMER → /discover
// 3. Valid token + VENDOR (no claim) → /vendor-app/find
// 4. Valid token + VENDOR (pending claim) → /vendor-app/pending
// 5. Valid token + VENDOR (approved) → /vendor-app/business
// 6. Expired token → attempt refresh → on fail: /auth/phone
```

### Bottom Navigation Bars

```
Customer: Discover | Reels | Map | Saved | Profile
          (5 tabs, AR button floating above Discover tab)
          Reels = Nearby vendor reels feed (End User §6.1 — vertical TikTok-style)
          Browse/Tags accessible via filter icon on Discover tab

Vendor:   My Business | Discounts | Media | Performance
          (4 tabs, "Create Discount" FAB floating)
```

---

## 6. CORE INFRASTRUCTURE

### API Client (`core/api/api_client.dart`)

```dart
// Dio instance configuration:
// - BaseOptions: baseUrl from env, connectTimeout 10s, receiveTimeout 30s
// - JWT Interceptor:
//     → Attach Authorization: Bearer {token} to all requests
//     → On 401: attempt refresh via /api/v1/auth/{type}/refresh/
//     → On refresh success: retry original request
//     → On refresh failure: clear secure storage → navigate to /auth/phone
// - Cache Interceptor (dio_cache_interceptor):
//     → Cache GET requests for offline fallback
//     → CachePolicy: forceCache when offline, refreshForceCache when online
// - Error Interceptor:
//     → Parse { success, data, message, errors } JSON envelope
//     → Throw typed exceptions: UnauthorizedException, NetworkException, etc.
// - Logging Interceptor (debug only):
//     → Log request/response in debug mode
```

### Permissions Service (`core/permissions/`)

**Critical: Never crash or block app on permission denial.**

```
Permission: Location (required for core)
  → Rationale screen: "AirAd needs your location to show nearby vendors"
  → On deny: city-level manual selection screen (never crash)
  → On permanent deny: show settings link

Permission: Microphone (voice search)
  → Rationale screen: "Enable your mic to search by voice"
  → On deny: hide voice search icon silently (never show error)

Permission: Camera (AR + video upload)
  → Rationale screen: "Enable camera for AR view and video upload"
  → On deny: hide AR button, show map as default view
  → One-time SnackBar: "AR not available. Showing map view."
```

### Location Provider

```dart
// StreamProvider<Position> from geolocator
// - High accuracy mode for AR (1-second intervals)
// - Battery-saving mode for discovery list (30-second intervals)
// - Falls back to last known position if permission denied
// - Location updates pause when app is backgrounded
```

### Connectivity Provider

```dart
// StreamProvider<ConnectivityResult> from connectivity_plus
// - Drives offline banner visibility
// - Controls API cache policy (forceCache when offline)
// - Disables write operations when offline
// - Auto-refreshes stale data when connection restored
```

---

## 7. ONBOARDING & AUTH

### Splash Screen (2 seconds)

- AirAd logo centered, white background (light) / dark background (dark mode)
- Check auth state:
  - Valid JWT → route to correct home based on user_type
  - No JWT → check onboarding_complete flag
  - First launch → /onboarding
  - Returning user → /auth/phone

### Onboarding (First-Time Only — 3 Screens)

```
Screen 1: "Discover what's around you right now"
  → AR concept illustration (Lottie animation of phone scanning street)
  → AirAd rausch gradient background

Screen 2: "Real deals from real nearby shops"
  → Vendor cards with discount badges illustration
  → babu (teal) gradient background

Screen 3: "Talk to find it, walk to get it"
  → Voice search waveform + navigation route illustration
  → arches (orange) gradient background

Controls:
  → "Skip" top-right on all screens
  → Dot indicators at bottom
  → "Get Started" CTA on last screen only
  → Stored: SharedPreferences onboarding_complete = true
```

### Role Selection

```
Two large, visually distinct cards:

┌────────────────────┐  ┌────────────────────┐
│    🔍               │  │    🏪               │
│                     │  │                     │
│  I'm Looking for    │  │  I Have a           │
│  Places Nearby      │  │  Business           │
│                     │  │                     │
│  Discover vendors,  │  │  Claim & manage     │
│  deals, and food    │  │  your listing       │
│  around you         │  │  on AirAd           │
│                     │  │                     │
│  [ Get Started ]    │  │  [ Get Started ]    │
└────────────────────┘  └────────────────────┘

Tapping either → PhoneEntryScreen with role stored in provider
```

### Phone Entry Screen

- Country code selector (pre-selected by device locale, Pakistan default)
- Phone number input with format validation
- "Continue" → `POST /api/v1/auth/{customer|vendor}/send-otp/`
- Loading state on button during API call
- Error: "Phone number invalid" or "Too many attempts, try again in X minutes"

### OTP Screen

```
Enter the 6-digit code sent to
+92 ****4567

┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐
│   │ │   │ │   │ │   │ │   │ │   │
└───┘ └───┘ └───┘ └───┘ └───┘ └───┘

Auto-advance: each box auto-focuses next on digit entry
Auto-submit: when all 6 filled
60-second countdown for resend (Timer widget)
Loading indicator on verify

On success:
  CUSTOMER → /discover
  VENDOR (no claim) → /vendor-app/find
  VENDOR (pending) → /vendor-app/pending
  VENDOR (approved) → /vendor-app/business
```

---

## 8. CUSTOMER DISCOVERY

### 8.1 Discover Screen (Home Tab)

**Layout:**
- Search bar at top (text input + microphone icon)
- Horizontal scrollable quick-filter chips below search
- AR camera FAB button top-right (hidden if camera denied)
- Infinite scroll vendor cards (20 per page)
- Pull-to-refresh with current location

**Quick Filter Chips:**
- "Cheap", "Open Now", "Nearby", "Discounts", "Pizza", "Cafe"
- Multi-select → combinable filters
- Active chips highlighted in rausch

**VendorCard Widget:**
```
┌─────────────────────────────────┐
│ [Cover Photo — 16:9]            │
│     🏷️ 20% OFF  (discount badge)│
│                            ⭐   │ ← Subscription badge
│ ┌──┐                            │
│ │🔵│ Pizza Hub          120m    │ ← Logo + name + distance
│ └──┘ Pizza · Open Now           │ ← Category + status
│                                  │
│ 🎬 🎬 🎬  (reel thumbnails)     │ ← If vendor has reels
│ 🎙️ (voice bot icon on logo)    │ ← If voice bot configured
└─────────────────────────────────┘

Interactions:
  - Tap → VendorProfileScreen
  - Long press → Quick action BottomSheet (Directions, Call, Share)
  - Swipe right → Save to favorites (heart animation)
```

### 8.2 AR Camera Screen

**Entry:** AR FAB button → full-screen immersive experience

**AR View:**
- Camera feed + compass heading + GPS → render floating vendor "bubbles"
- Each bubble: vendor name (bold), distance ("80m"), discount badge if active
- Bubble size varies by distance (closer = slightly larger, max 5-8 visible)
- Bubbles move as user rotates phone (compass heading)
- "X more nearby" indicator at bottom of screen

**Vendor Bubble Widget:**
```
    ┌──────────────────┐
    │  Pizza Hub       │
    │  80m   🏷️20%OFF  │
    │  ⭐ Verified      │
    └──────────────────┘
          │
          ▼ (pointer to real-world direction)
```

**Bubble Interaction:**
- Tap bubble → VendorProfileScreen
- List button at bottom → slides up BottomSheet with full vendor list sorted by distance

**Device Fallback:**
- No compass/heading sensors OR inadequate GPU → automatically switch to map view
- One-time SnackBar: "AR view is not available on this device. Showing map instead."

**Privacy:** Camera feed processed LOCALLY ONLY. No recording, no upload, no storage.

**Close:** X button top-left → back to Discover tab

### 8.3 Map Screen (Tab)

**Full-screen Google Maps:**
- User location: pulsing blue dot
- Vendor pins: custom markers with category icons
- Active discount: larger pin with pulsing animation + discount badge
- Premium vendors: gold-outlined pin

**Map Controls:**
- My Location button (bottom-right)
- Radius selector: 200m / 500m / 1km / 2km (segmented control)
- Filter button (top-right) → same tag filter sheet
- Translucent radius indicator circle

**Cluster Behavior:**
- Dense areas: cluster pins into count circles ("5 vendors")
- Tap cluster → zoom in to reveal individual pins

**Vendor List Toggle:**
- Draggable handle at bottom → slides up half-screen vendor list
- List updates as map is panned/zoomed
- Sorted by distance from map center

**Pin Tap:**
- Tap pin → vendor summary BottomSheet (logo, name, distance, discount, CTA buttons)
- Tap summary card → VendorProfileScreen

### 8.4 Voice Search

**Trigger:** Microphone icon on Discover screen search bar

**Voice Search Overlay (full-screen):**
```
┌─────────────────────────────────┐
│                                  │
│          [X close]               │
│                                  │
│     ╭──────────────╮            │
│     │  🎤           │            │
│     │  (animated    │            │
│     │   waveform)   │            │
│     ╰──────────────╯            │
│                                  │
│  "Say what you're looking for"   │
│  Like "cheap pizza" or           │
│  "open pharmacy nearby"          │
│                                  │
│  Transcription appears here:     │
│  "cheap pizza near me"           │
│                                  │
│  Interpreted as:                 │
│  [Pizza] [Budget: Cheap] [Nearby]│
│                                  │
└─────────────────────────────────┘
```

**Flow:**
1. `speech_to_text` plugin: on-device transcription
2. Show transcription in real-time on screen
3. On speech end: `POST /api/v1/discovery/voice-search/`
4. Animate overlay down → show filtered results on Discover screen
5. Active filter chips show interpreted tags (category, intent)

**Error handling:**
- Speech unclear: "I didn't catch that. Try saying 'cheap food' or 'open cafe'"
- No results: "I couldn't find that nearby. Try a different search."
- Mic denied: icon hidden (never show error)

### 8.5 Tag-Based Browsing (Tab)

**Tags Screen — Sectioned BottomSheet:**

```
Section 1: "What's happening now?" (PROMOTION + TIME tags)
  → [Discounts Live] [Happy Hour] [Open Now] [Late Night]
  → Orange background on active deal tags

Section 2: "What do you want?" (INTENT tags)
  → [Cheap 💰] [Premium ✨] [Family 👨‍👩‍👧] [Healthy 🥗]
  → Chips with emoji icons

Section 3: "What are you looking for?" (CATEGORY tags)
  → Grid of category cards: [🍕 Pizza] [☕ Cafe] [🍔 Burgers] [💇 Salon]
  → 3-column grid with icon + name

Section 4: "Near a specific place?" (LOCATION tags)
  → Area + landmark names as flat searchable list
```

**Multi-Tag Selection:**
- Multiple tags combinable (AND logic)
- Selected tags: persistent filter bar at top with X chips + "Clear All"
- Live results update as tags selected
- Floating bubble: "14 vendors match your filters"
- Close sheet → see filtered results immediately on Discover screen

### 8.6 Reels Feed Screen (Tab — End User §6.1)

**Entry:** "Reels" tab in bottom navigation bar

**Full-screen vertical TikTok-style reel feed:**
```
┌─────────────────────────────────┐
│                                  │
│     [Full-screen 9:16 video]     │
│                                  │
│                                  │
│     Auto-playing vendor reel     │
│     (muted by default)           │
│                                  │
│                                  │
│  ┌──┐ Pizza Hub         120m    │ ← Overlay: vendor info
│  │🔵│ 🏷️ 20% OFF Happy Hour    │ ← Active discount badge
│  └──┘                            │
│  [Visit Profile] [Navigate]      │ ← CTA buttons
│                                  │
│  🔊 (tap to unmute)              │
│                                  │
└─────────────────────────────────┘

Swipe up → next reel
Swipe down → previous reel
Tap → pause/resume
```

**Data Source:** `GET /api/v1/discovery/nearby/reels/?lat&lng&radius`

**Ranking:** Reels ranked by:
1. Distance (closest vendors first)
2. Recency (newer reels prioritized)
3. Engagement (higher completion rate boosted)
4. Active promotion (vendors with live deals surface higher)

**Behavior:**
- Auto-play (muted) when reel is in focus
- Pause when swiped away or app backgrounded
- Pre-load next 2 reels for smooth scrolling
- Each reel shows vendor name, distance, active discount (if any)
- Tap vendor overlay → VendorProfileScreen
- "Navigate" button → NavigationScreen
- Infinite scroll with shimmer loader between batches
- Pull-to-refresh from top

**Offline:** Disable with "Connect to internet to see nearby reels" message

---

## 9. VENDOR PROFILE & REELS

### Vendor Profile Screen

**Sticky Header (scrollable):**
```
┌─────────────────────────────────┐
│ [Cover Photo — full-width 220px]│
│  ←  (back)              🔗(share)│
│                                  │
│ ┌──┐ Pizza Hub          120m    │
│ │🔵│ Pizza · Open · ⭐ Verified  │
│ └──┘                            │
│                                  │
│ [Navigate] [Call] [Ask Bot 🎙️]  │ ← Action row
└─────────────────────────────────┘
```

**Video Reel Section:**
- Horizontal scroll row of 9:16 reel cards
- Tap → full-screen VideoPlayer
- Reels auto-play (muted) when scrolled into view, pause when out

**About Section:** description, address, website (url_launcher)

**Hours Section:** Compact weekly view, today highlighted, open/closed badge

**Active Discounts Section:**
- Active: prominent cards with countdown timer ("Ends in 1h 23m")
- Scheduled: lighter upcoming cards

**Location Map:** Small non-interactive map + "Get Directions" button

**Service Options:** "Delivery Available" + "Pickup Available" chips

### Reel Fullscreen Player

- Vertical swipe: next/previous reel
- Tap to pause/resume
- Muted by default, tap to unmute
- Vendor name + CTA overlay at bottom
- Duration: 9 or 11 seconds (fixed)
- Auto-advance to next reel on completion

---

## 10. NAVIGATION & DIRECTIONS

**Trigger:** "Navigate" button on VendorProfileScreen

**Decision Logic:**
- Distance ≤ 2km → show in-app walking navigation
- Distance > 2km → "Open in Google Maps" / "Open in Apple Maps" via url_launcher

**In-App Navigation Screen:**
- Map with route drawn in rausch red (user → vendor)
- Walking directions only (simplest, most useful for AirAd use case)
- Step-by-step panel (BottomSheet): current step in large text, distance to next turn
- Arrow indicator using compass heading
- Continuous GPS updates every 2 seconds
- Recalculate if user deviates >50m

**Arrival Detection:**
- Within 30m → "You've arrived!" screen with Lottie celebration
- Optional "I'm Here" button → analytics event
- Show vendor profile CTA

---

## 11. VENDOR APP

### 11.0 Progressive Activation (§3.2 — Mobile)

The vendor app adapts based on `activation_stage` from the dashboard API (same as web portal):

```
Stage: CLAIM (Day 0-3)
  → Show only: Profile edit, business hours, upload 1 reel
  → Bottom nav: My Business tab only (other tabs greyed with lock icon)
  → Banner: "Complete your profile to unlock more tools!"
  → Guided checklist: "Upload logo" → "Set hours" → "Upload first reel"

Stage: ENGAGEMENT (Day 3+)
  → Unlock: Discounts tab, basic performance numbers
  → Banner: "Create your first discount to attract nearby customers!"
  → Guided tooltip on Discounts tab (first open)

Stage: MONETIZATION (Day 7+)
  → Unlock: Performance tab fully, upgrade prompts
  → ROI card on My Business tab: "X views this week — upgrade to get 3x more"
  → "Upgrade" button in settings

Stage: GROWTH / RETENTION (Day 14+)
  → All tabs fully unlocked per subscription tier
  → No activation restrictions
```

**Implementation:**
- `activation_stage` read from vendor dashboard API response
- `ActivationGateWidget` wraps locked tabs — shows lock icon + "Unlock in X days" or "Upload a reel to unlock"
- Stage transitions trigger Lottie celebration animation

### 11.1 Find Business Screen

- Search bar: match unclaimed listings in real-time
- Results list: name, address, "Unclaimed" badge
- GPS-based: show nearest unclaimed first
- "Register New Business" button at bottom (for businesses not in system)

### 11.2 Claim Flow

**ClaimConfirmScreen:**
- "Is this your business?" with listing details (name, address, photo if available)
- "Yes, This Is My Business" CTA + "Not My Business" link
- On confirm → POST claim request

**Verification Path:**
- Auto (OTP available): 6-digit OTP sent to business phone on file
- Manual (no OTP): upload storefront photo + optional business license
- GPS proximity check: must be within 100m (background, transparent to user)

**PendingClaimScreen:**
- "Claim Submitted" with estimated review time
- Status bar: Submitted → Under Review → Approved/Rejected
- Push notification on status change (FCM)
- Pull-to-refresh to check status

### 11.3 Vendor Profile Edit (Post-Claim)

- Focus on mobile-optimized actions: photos, hours, delivery/pickup toggles
- Logo + cover photo upload (camera or gallery)
- Business hours: mobile picker (tap day → set open/close times)
- Profile completeness progress bar
- Complex operations → "Manage on web portal" link (url_launcher)

### 11.4 Discount Manager

**Discounts Tab Sections:**
1. **Active Right Now:** Large live card with green pulsing indicator, countdown, "Stop Early" button
2. **Upcoming:** Scheduled discounts with start time countdown
3. **Past:** Recent history with views received during window

**Quick Create (FAB → BottomSheet):**
```
Type: [Flat 💵] [% Off 📊] [BOGO 🎁] [Happy Hour ⏰]

Duration: [30 min] [1 hour] [2 hours] [Custom]

Value: [_____] (large number input)

Start: [Now ✅] [Schedule 📅]

[ Create Discount ]
```

**Tier Enforcement:**
- "Happy Hours used today: 1/3" progress bar
- Silver trying Happy Hour: upgrade prompt with "Available from Gold"

### 11.5 Reel Management

- Vertical list: thumbnail, title, view count, upload date, drag-to-reorder
- Upload limit: "1 of 1 used" (Silver), "3 of 6 uploaded" (Diamond)
- Silver at limit: disabled upload button + "Upgrade to Gold for 3 videos"

**Upload Flow:**
1. "Add Video" → BottomSheet: "Record Now" or "Choose from Gallery"
2. Trim Editor: horizontal scrubber, start/end handles, live preview (9-15 seconds)
3. Upload: title input → chunked upload with progress bar
4. Processing badge until backend confirms
5. Local notification on completion

### 11.6 Performance Screen

- Simplified analytics (compared to web portal):
  - Total views this week (large hero number)
  - Bar chart: daily views (7 days)
  - Top 3 performing reels
  - Active discount performance
- "See detailed analytics on web" link for advanced features

---

## 12. OFFLINE STRATEGY

| Scenario | Behavior |
|---|---|
| Discovery results | Cache last successful response per location |
| Vendor profile | Cache individual vendor details |
| Tags list | Cache for 24 hours |
| Write operations | Disabled with "Connect to internet" message |
| Network restored | Auto-refresh all stale providers |
| Persistent UI | Amber banner: "You're offline — showing cached results" |
| AR mode | Disable (requires real-time GPS + data) |
| Map mode | Show cached pins, disable search |
| Voice search | Disable (requires API call) |

**Rules:**
- NEVER crash or show error screen when offline
- ALWAYS show cached content with clear offline indicator
- NEVER allow write operations (discount create, reel upload, profile edit) offline
- Auto-dismiss offline banner when connection restored

---

## 13. PUSH NOTIFICATIONS

### Notification Types

| Type | Recipient | Trigger | Frequency Limit |
|---|---|---|---|
| Claim Status | Vendor | Claim approved/rejected | Once per claim |
| Subscription Expiry | Vendor | 7 days + 1 day before expiry | 2 per cycle |
| Nearby Discount | Customer | GPS enters area with active deal | Max 2/day |
| Flash Deal | Customer | Vendor launches flash deal nearby | Max 3/day |
| New Vendor | Customer | New vendor in frequent area | Max 1/week |
| Re-engagement | Customer | 7 days inactive | Once per period |

### Implementation

- `firebase_messaging` for FCM token registration
- Token sent to backend on login: `PATCH /api/v1/auth/{type}/profile/` with `device_token`
- `flutter_local_notifications` for foreground display
- Deep link routing via GoRouter on notification tap
- Notification preferences in settings screen (toggle by type)

---

## 14. STATE MANAGEMENT PATTERNS

### Auth Provider (StateNotifier)

```dart
// StateNotifier<AuthState>
// AuthState: { user, accessToken, refreshToken, userType, vendorId }
// Methods: login(phone, otp), logout(), refreshToken()
// Persisted via flutter_secure_storage
// On logout: clear storage, navigate to /auth/phone
```

### Discovery Provider (StateNotifier)

```dart
// StateNotifier<DiscoveryState>
// DiscoveryState: { vendors, isLoading, hasMore, activeFilters, currentLocation }
// Methods: loadMore(), refresh(), applyFilters(tags), applyVoiceSearch(query)
// Caches last successful results for offline use
// Pagination: 20 vendors per page, infinite scroll trigger
```

### Location Provider (StreamProvider)

```dart
// StreamProvider<Position> from geolocator
// Permission check before streaming
// Falls back to last known position if denied
// AR mode: high accuracy, 1-second intervals
// Discovery mode: battery-saving, 30-second intervals
```

### Vendor Detail Provider (FutureProvider.family)

```dart
// FutureProvider.family<VendorDetail, String>(slug)
// Cached via dio_cache_interceptor
// Offline: serve from cache with stale indicator
```

---

## 15. TESTING STRATEGY

### Unit Tests

| Test | What it Verifies |
|---|---|
| `ranking_service_test.dart` | Scoring formula with known inputs → expected outputs |
| `voice_parser_test.dart` | Rule-based NLP: "cheap pizza" → {category: pizza, intent: cheap} |
| `distance_formatter_test.dart` | "80m", "1.2km", "3.5km" formatting |
| `feature_gate_test.dart` | Every tier × every feature → correct bool |
| `currency_formatter_test.dart` | "PKR 3,000", "Free" formatting |

### Widget Tests

| Test | What it Verifies |
|---|---|
| `vendor_card_test.dart` | All states: with/without discount, reels, voice bot |
| `otp_screen_test.dart` | Auto-advance, auto-submit, countdown timer |
| `discount_card_test.dart` | Active/scheduled/expired states, countdown |
| `voice_search_overlay_test.dart` | Transcription display, interpreted tags |

### Integration Tests

| Test | What it Verifies |
|---|---|
| `auth_flow_test.dart` | Phone entry → OTP → home screen routing |
| `discovery_flow_test.dart` | Search → filter → vendor card → profile |
| `claim_flow_test.dart` | Find business → claim → pending → approved |

### Manual Testing Checklist (Physical Device Required)

- [ ] AR view on physical device (compass + GPS accuracy)
- [ ] Voice search on physical device (speech_to_text quality)
- [ ] Video upload with trim editor (camera + gallery paths)
- [ ] Offline mode: kill network → cached results + banner
- [ ] Permission denial: location, mic, camera (graceful fallback)
- [ ] Dark mode: all screens visually correct
- [ ] Navigation: walking route + arrival detection
- [ ] Push notifications: claim approval, nearby discount
- [ ] Performance: smooth scrolling, no jank on vendor list
- [ ] Battery: 10 min AR session < 5% drain

---

## 16. BUILD SEQUENCE & SESSIONS

### Prerequisites

Before starting Flutter development:
- [ ] Backend Phase B APIs stable and tested
- [ ] Vendor Portal (web) complete and tested
- [ ] API documentation (OpenAPI) up to date
- [ ] Test environment deployed with seed data

### Build Sessions (6 Sessions)

| Session | Features | Goal |
|---|---|---|
| **FL-S1** | Core + Auth | Project setup, theming, API client, auth flow (splash → onboard → OTP → home) |
| **FL-S2** | Discovery + Map | Discover screen with vendor cards, map screen with pins, infinite scroll, search |
| **FL-S3** | AR + Voice | AR camera with vendor bubbles, voice search overlay, tag browsing |
| **FL-S4** | Vendor Profile | Profile screen with reels, discounts, hours, navigation, voice bot Q&A |
| **FL-S5** | Vendor App | Claim flow, profile edit, discount manager, reel upload with trim |
| **FL-S6** | Polish + Test | Offline mode, push notifications, dark mode polish, performance optimization |

### Session Dependencies

```
FL-S1 → FL-S2 → FL-S3 (sequential — each builds on previous)
                   ↓
                 FL-S4 (vendor profile — needs discovery working)
                   ↓
                 FL-S5 (vendor app — needs profile + auth working)
                   ↓
                 FL-S6 (polish — needs all features in place)
```

### Gate: Flutter App Complete

- [ ] Both user modes working end-to-end (Customer + Vendor)
- [ ] AR view functional on physical iOS + Android devices
- [ ] Voice search parses queries and returns results
- [ ] Claim flow: search → claim → verify → approved → dashboard
- [ ] Offline mode: cached results shown, write ops disabled, banner displayed
- [ ] All permissions: graceful fallback on denial (never crash)
- [ ] Dark mode: all screens tested and visually correct
- [ ] Push notifications: received and deep-link correctly
- [ ] Performance: 60fps scrolling, <2s screen transitions
- [ ] All unit + widget + integration tests passing
- [ ] Manual device testing checklist 100% complete

---

## 17. QUALITY GATE CHECKLIST

### Architecture

- [ ] Feature-based folder structure — no cross-feature imports except through `core/`
- [ ] All state in Riverpod providers — no setState for business logic
- [ ] All API calls through `api_client.dart` — no raw Dio usage in features
- [ ] JWT interceptor: 401 → refresh → retry → on failure clear storage + redirect

### UX & Accessibility

- [ ] Dark mode from day one — all screens tested
- [ ] DM Sans typography everywhere (google_fonts)
- [ ] Brand colors match DLS exactly (AppColors constants)
- [ ] Semantic labels on all interactive elements
- [ ] Respect system accessibility settings (text scale, reduced motion)
- [ ] Minimum touch target: 44×44 pixels

### Permissions

- [ ] Rationale screen BEFORE system permission dialog
- [ ] Location denied → city-level manual selection (never crash)
- [ ] Mic denied → voice search icon hidden (never error)
- [ ] Camera denied → AR hidden, map shown as default

### Offline

- [ ] Never crash or show error screen when offline
- [ ] Cached results served with amber banner
- [ ] Write operations disabled with clear message
- [ ] Auto-refresh when connection restored

### AR & Privacy

- [ ] Camera feed NEVER uploaded to server
- [ ] No recording or storage of AR sessions
- [ ] Device fallback: no compass/GPU → map view with one-time message
- [ ] Max 5-8 bubbles at once (performance)

### Voice

- [ ] On-device transcription only (speech_to_text)
- [ ] Rule-based NLP — no ML calls
- [ ] Graceful failure: "I couldn't find that nearby"

### Vendor Feature Gates

- [ ] `vendor_has_feature()` checked before showing premium UI
- [ ] Silver at reel limit: upload disabled + upgrade message
- [ ] Silver voice bot: locked icon + upgrade prompt
- [ ] Happy hour limits displayed accurately per tier

### Performance

- [ ] Reel auto-play only when scrolled into view
- [ ] CachedNetworkImage for all remote images
- [ ] Infinite scroll: 20 vendors per page, shimmer loaders
- [ ] AR: max 5-8 bubbles (GPU optimization)
- [ ] Video upload: chunked, background, progress bar

---

## 18. NON-NEGOTIABLE RULES

1. **Camera feed LOCAL ONLY** — never upload AR camera data to any server
2. **Rule-based NLP only** — no ML models in Phase 1
3. **Never crash on permission denial** — always graceful fallback
4. **Never crash offline** — always show cached content with banner
5. **`vendor_has_feature()` is the ONLY feature gate** — backend enforced, UI reflects
6. **DM Sans typography only** — no system fonts except in fallback chain
7. **Brand colors from AppColors only** — never hardcode hex in widgets
8. **Dark mode tested on every screen** — not optional
9. **Minimum 44×44px touch targets** — accessibility non-negotiable
10. **Phone numbers always masked** — `*********4567` in all UI
11. **OTP boxes: no autocomplete** — security requirement
12. **FCM tokens sent to backend on every login** — push notification registration
13. **Reels: auto-mute by default** — user taps to unmute
14. **AR bubbles: max 8 visible** — performance + visual clarity
15. **Navigation: walking only** — driving directions via external maps app

---

**— End of Flutter Mobile App Master Plan —**
