# USER PORTAL FLUTTER PLAN — PART 1
## AirAds Customer App — Flutter Architecture, Design System, App Shell, AR Experience, Voice Search

This plan defines the complete Flutter mobile application for AirAds end customers. Customer-only scope — no vendor management features. Mirrors the User Portal web app in UX goals but delivers native mobile capabilities (AR, voice, location, push notifications).

---

## TABLE OF CONTENTS (Part 1)

1. [App Identity & Platform Strategy](#1-app-identity)
2. [Overall Architecture — Clean Architecture Feature-First](#2-overall-architecture)
3. [Tech Stack & Dependencies](#3-tech-stack)
4. [Project Structure](#4-project-structure)
5. [Design System — AirAds DLS in Flutter](#5-design-system)
6. [App Shell — Navigation & Layout](#6-app-shell)
7. [State Management Strategy](#7-state-management)
8. [API Layer](#8-api-layer)
9. [Native AR Experience](#9-native-ar-experience)
10. [Voice Search — Native Mic Integration](#10-voice-search)

> **Part 2 covers:** Location Services, Map Integration, All Screens (Landing/Auth/Discovery/Profile/Deals/Reels/Navigation/Preferences), Push Notifications, Offline Mode, Performance, iOS vs Android Differences, App Store Requirements, Build Sequence, QA Checklist.

---

## 1. APP IDENTITY & PLATFORM STRATEGY

### App Name & Bundle IDs
- **App Name:** AirAds
- **Bundle ID (iOS):** `pk.airad.customerapp`
- **App ID (Android):** `pk.airad.customerapp`
- **Stores:** Apple App Store + Google Play Store (both Phase-1)
- **Versioning:** Semantic (`1.0.0+1`)
- **Target:**
  - Android: `minSdk 21` (Android 5.0+), `targetSdk 34`
  - iOS: minimum iOS 14.0 (AR requires iOS 14+, covers 95%+ active devices)

### Relationship to Web User Portal
- Calls **same backend APIs** (`/api/v1/user-portal/`)
- Same brand identity: orange/crimson/teal/black, DM Sans font
- Better AR, voice, navigation than web (native hardware APIs)
- Additional native: push notifications, offline mode, platform deep links

### Customer-Only Scope
Zero vendor management features. If a vendor opens this app, they see only the customer discovery experience — Vendor Portal management stays on the web app.

---

## 2. OVERALL ARCHITECTURE — CLEAN ARCHITECTURE FEATURE-FIRST

### Pattern: Clean Architecture, Vertical Slices

```
lib/
├── core/               ← App-wide: theme, network, error handling, storage
├── features/           ← One folder per feature (vertical slices)
│   ├── auth/
│   ├── discovery/
│   ├── ar/
│   ├── voice/
│   ├── map/
│   ├── vendor_profile/
│   ├── deals/
│   ├── reels/
│   ├── navigation/
│   ├── preferences/
│   └── notifications/
└── shared/             ← Shared widgets, models, utilities
```

Each feature folder:
```
feature_name/
├── data/
│   ├── datasources/    ← Remote (API) + Local (Hive cache)
│   ├── models/         ← JSON serialization (Freezed)
│   └── repositories/   ← Implements domain interface
├── domain/
│   ├── entities/       ← Pure Dart objects
│   ├── repositories/   ← Abstract interfaces
│   └── usecases/       ← Single-responsibility business logic
└── presentation/
    ├── bloc/           ← Events, States, Bloc class
    ├── pages/          ← Full-screen pages
    └── widgets/        ← Feature-specific widgets
```

### Key Architecture Decisions

1. **BLoC for all business logic** — no logic in widgets
2. **Repository pattern** — data source swappable (remote ↔ cache)
3. **get_it + injectable** — dependency injection, testable
4. **`Either<Failure, T>`** throughout — typed error handling (dartz)
5. **Feature-first, not layer-first** — each feature independently workable

---

## 3. TECH STACK & DEPENDENCIES

### Core Flutter
- **Flutter SDK:** 3.19+ (stable)
- **Dart SDK:** 3.3+
- **State Management:** `flutter_bloc` + `bloc`
- **DI:** `get_it` + `injectable`
- **Functional:** `dartz` (Either for error handling)
- **Navigation:** `go_router` 13+ (declarative, deep links, guards)

### UI & Animation
- **Animations:** `flutter_animate` (declarative chaining)
- **Glassmorphism:** Custom `BackdropFilter` + `ClipRRect`
- **Lottie:** `lottie` (arrival checkmark, voice wave)
- **Icons:** `lucide_icons` (matches web) + Material fallback
- **Video:** `video_player` + `chewie`
- **Image:** `cached_network_image`

### Location & Maps
- **Location:** `geolocator` (GPS, permissions, position stream)
- **Geocoding:** `geocoding` (lat/lng → area name)
- **Maps:** `mapbox_maps_flutter` (Mapbox GL)

### AR & Sensors
- **AR:** `ar_flutter_plugin` (ARCore Android + ARKit iOS)
- **Camera:** `camera` (fallback Simulated AR mode)
- **Compass:** `flutter_compass`
- **Sensors:** `sensors_plus` (accelerometer for walking safety)

### Voice
- **STT:** `speech_to_text` (native mic, both platforms)
- **TTS:** `flutter_tts` (voice bot response audio)

### Networking & Storage
- **HTTP:** `dio` + interceptors
- **Cache:** `hive` (fast key-value, offline mode)
- **Secure storage:** `flutter_secure_storage` (JWT, guest token — encrypted)
- **Connectivity:** `connectivity_plus`

### Notifications
- **Push:** `firebase_messaging` (FCM)
- **Local:** `flutter_local_notifications`
- **Firebase:** `firebase_core`

### Native & Platform
- **Share:** `share_plus`
- **Deep links:** `app_links` (Universal Links + App Links)
- **Permissions:** `permission_handler`
- **Device info:** `device_info_plus` (AR capability check)

### Dev & Code Quality
- **Models:** `freezed` + `freezed_annotation` + `json_serializable`
- **Testing:** `bloc_test`, `mocktail`, `flutter_test`
- **Linting:** `very_good_analysis`
- **Code gen:** `build_runner`

---

## 4. PROJECT STRUCTURE

```
airad_customer_app/
├── android/app/src/main/
│   ├── AndroidManifest.xml       ← Permissions, deep links, FCM
│   └── build.gradle              ← minSdk 21, targetSdk 34
├── ios/Runner/
│   ├── Info.plist                ← NSCamera, NSLocation*, NSMicrophone usage strings
│   └── AppDelegate.swift         ← Firebase init, deep link handling
├── assets/
│   ├── images/airad_logo.png
│   ├── animations/
│   │   ├── arrival_checkmark.json    ← Lottie
│   │   └── voice_wave.json           ← Lottie
│   └── fonts/DMSans/                 ← Regular, Medium, SemiBold, Bold
├── lib/
│   ├── main.dart                 ← App entry, DI setup, Firebase init, Hive init
│   ├── app.dart                  ← MaterialApp + GoRouter + theme
│   │
│   ├── core/
│   │   ├── theme/
│   │   │   ├── app_theme.dart        ← Dark + light ThemeData
│   │   │   ├── app_colors.dart       ← All brand color constants
│   │   │   ├── app_text_styles.dart  ← DM Sans text styles
│   │   │   └── app_spacing.dart      ← 8px base spacing constants
│   │   ├── network/
│   │   │   ├── dio_client.dart       ← Dio instance + interceptors
│   │   │   ├── api_endpoints.dart    ← All URL string constants
│   │   │   └── network_info.dart     ← Connectivity check
│   │   ├── error/
│   │   │   ├── failures.dart         ← Freezed failure hierarchy
│   │   │   └── exceptions.dart       ← Typed exceptions
│   │   ├── storage/
│   │   │   ├── secure_storage.dart   ← Token storage
│   │   │   └── hive_service.dart     ← Box init + access
│   │   ├── permissions/
│   │   │   └── permission_service.dart
│   │   └── constants/
│   │       ├── app_constants.dart    ← Timeouts, limits
│   │       └── route_names.dart      ← GoRouter route constants
│   │
│   ├── features/                 ← (see architecture above)
│   └── shared/
│       ├── widgets/
│       │   ├── ar_marker_widget.dart
│       │   ├── vendor_card_widget.dart
│       │   ├── promotion_badge_widget.dart
│       │   ├── countdown_timer_widget.dart
│       │   ├── tier_badge_widget.dart
│       │   ├── distance_badge_widget.dart
│       │   ├── skeleton_loader_widget.dart
│       │   ├── voice_wave_widget.dart
│       │   └── offline_banner_widget.dart
│       ├── models/
│       │   ├── vendor_model.dart
│       │   ├── promotion_model.dart
│       │   ├── reel_model.dart
│       │   └── tag_model.dart
│       └── utils/
│           ├── geo_utils.dart        ← Bearing, Haversine, geohash
│           ├── formatters.dart       ← Distance, countdown, date
│           └── nlp_utils.dart        ← Keyword extraction
├── test/
│   ├── unit/
│   ├── widget/
│   └── integration/
├── pubspec.yaml
├── analysis_options.yaml             ← very_good_analysis
└── .env                              ← via --dart-define (MAPBOX_TOKEN, API_BASE_URL)
```

---

## 5. DESIGN SYSTEM — AIROADS DLS IN FLUTTER

### 5.1 Brand Colors (`app_colors.dart`)

```dart
class AppColors {
  // Brand Primitives
  static const brandOrange       = Color(0xFFFF8C00);
  static const brandOrangeLight  = Color(0xFFFFB347);
  static const brandOrangeGlow   = Color(0x40FF8C00); // 25% opacity
  static const brandCrimson      = Color(0xFFC41E3A);
  static const brandCrimsonLight = Color(0xFFE8425A);
  static const brandCrimsonGlow  = Color(0x40C41E3A);
  static const brandTeal         = Color(0xFF00BCD4);
  static const brandTealLight    = Color(0xFF4DD0E1);
  static const brandTealGlow     = Color(0x4000BCD4);
  static const brandBlack        = Color(0xFF000000);

  // Dark Theme Surfaces
  static const darkBgPage     = Color(0xFF0A0A0A);
  static const darkBgSurface  = Color(0xFF141414);
  static const darkBgElevated = Color(0xFF1E1E1E);
  static const darkBgNav      = Color(0xFF000000);
  static const darkBorder     = Color(0x1AFFFFFF); // 10% white

  // Dark Theme Text
  static const darkTextPrimary   = Color(0xFFFFFFFF);
  static const darkTextSecondary = Color(0xA6FFFFFF); // 65% white
  static const darkTextTertiary  = Color(0x66FFFFFF); // 40% white
  static const darkTextDisabled  = Color(0x40FFFFFF); // 25% white

  // Light Theme Surfaces
  static const lightBgPage     = Color(0xFFF5F5F5);
  static const lightBgSurface  = Color(0xFFFFFFFF);
  static const lightBgElevated = Color(0xFFFAFAFA);
  static const lightTextPrimary = Color(0xFF0A0A0A);
  static const lightTextSecondary = Color(0xA60A0A0A);

  // Semantic
  static const success = brandTeal;
  static const warning = Color(0xFFFFC107);
  static const error   = brandCrimson;

  // Tier Colors
  static const tierSilver  = Color(0xFF9E9E9E);
  static const tierGold    = Color(0xFFFFC107);
  static const tierDiamond = brandTeal;
  // Tier Platinum: LinearGradient([brandOrange, brandCrimson])
}
```

### 5.2 Text Styles (`app_text_styles.dart`)

All styles use `'DMSans'` font family.

| Name | Size | Weight | Line Height |
|---|---|---|---|
| `display` | 40px | Bold (700) | 1.2 |
| `heading1` | 32px | Bold | 1.2 |
| `heading2` | 24px | Bold | 1.3 |
| `heading3` | 20px | SemiBold (600) | 1.3 |
| `bodyLarge` | 17px | Regular (400) | 1.5 |
| `bodyMedium` | 15px | Regular | 1.5 |
| `bodySmall` | 13px | Regular | 1.5 |
| `caption` | 11px | Regular | 1.4 |
| `labelLarge` | 15px | SemiBold | — |
| `labelMedium` | 13px | Medium (500) | — |
| `labelSmall` | 11px | Medium | — |

### 5.3 Spacing (`app_spacing.dart`)

```dart
class AppSpacing {
  static const xs = 4.0;   static const sm = 8.0;
  static const md = 12.0;  static const base = 16.0;
  static const lg = 20.0;  static const xl = 24.0;
  static const xxl = 32.0; static const xxxl = 40.0;
  static const huge = 48.0; static const massive = 64.0;
}
```

### 5.4 ThemeData

Two `ThemeData` instances in `app_theme.dart`: `AppTheme.dark` (default) and `AppTheme.light`.

```dart
// Dark theme applied as default:
MaterialApp(
  themeMode: preferencesBloc.theme, // ThemeMode.dark by default (first launch)
  theme: AppTheme.light,
  darkTheme: AppTheme.dark,
)
```

Theme preference stored in Hive `'settings'` box key `'theme'`. Default: `ThemeMode.dark`.

### 5.5 Animation Constants

```dart
class AppDurations {
  static const fast   = Duration(milliseconds: 150);
  static const base   = Duration(milliseconds: 200);
  static const smooth = Duration(milliseconds: 300);
  static const spring = Duration(milliseconds: 400);
}

class AppCurves {
  static const fast   = Curves.easeOut;
  static const base   = Curves.easeInOut;
  static const spring = Curves.elasticOut;
  static const smooth = Curves.easeInOutCubic;
}
```

---

## 6. APP SHELL — NAVIGATION & LAYOUT

### 6.1 GoRouter Configuration

```dart
// All routes in go_router config (router.dart)
final router = GoRouter(
  initialLocation: '/',
  redirect: (context, state) { /* guest token init, auth checks */ },
  routes: [
    GoRoute(path: '/', builder: (_) => LandingPage()),
    GoRoute(path: '/login', builder: (_) => LoginPage()),
    GoRoute(path: '/register', builder: (_) => RegisterPage()),
    ShellRoute(
      builder: (_, __, child) => AppShell(child: child),
      routes: [
        GoRoute(path: '/discover', builder: (_) => DiscoveryPage()),
        GoRoute(path: '/deals',    builder: (_) => DealsPage()),
        GoRoute(path: '/reels',    builder: (_) => ReelsPage()),
        GoRoute(path: '/browse',   builder: (_) => TagBrowserPage()),
        GoRoute(path: '/me',       builder: (_) => MePage()),
      ],
    ),
    GoRoute(path: '/vendor/:id', builder: (_, s) => VendorProfilePage(id: s.pathParameters['id']!)),
    GoRoute(path: '/navigate/:id', builder: (_, s) => NavigationPage(id: s.pathParameters['id']!)),
    GoRoute(path: '/preferences', builder: (_) => PreferencesPage()),
  ],
);
```

### 6.2 Bottom Navigation Bar (AppShell)

```
5 Tabs:
  Discover 🏠  →  /discover
  Deals 🔥     →  /deals
  Reels 🎬     →  /reels
  Browse 🏷️   →  /browse
  Me 👤        →  /me

Design:
  Background: AppColors.darkBgNav (pure black)
  Selected: AppColors.brandOrange (icon + label)
  Unselected: AppColors.darkTextTertiary
  Top border: 1px AppColors.darkBorder
  Height: 60px + MediaQuery.padding.bottom (safe area)

Active indicator: small orange pill above active icon
  AnimatedContainer width: 24px (active) → 4px (inactive), duration: AppDurations.smooth

All tabs: minimum 44×44px touch target
Reels tab: bottom nav stays VISIBLE but uses transparent/overlay styling
  [AUDIT FIX — MEDIUM 2.3] Never fully hide bottom nav — users must switch tabs without back-swipe
  On Reels tab: BottomNavigationBar bg = Colors.transparent (overlays black video)
  Active tab label: hidden (icons only, full-screen context)
  Opacity: 0.7 when on Reels tab, 1.0 on all other tabs
```

### 6.3 Discovery Sub-View Switcher (Inside DiscoveryPage)

```
Segmented pill control inside DiscoveryPage header (not system AppBar)
  "📷 AR" | "🗺️ Map" | "📋 List"

Styling:
  Container: rounded pill, AppColors.darkBgElevated bg
  Active segment: white bg, brandOrange text
  Inactive: transparent, secondary text

Animation: AnimatedContainer for active segment position shift (AppDurations.smooth)
State: stored in DiscoveryBloc — switching uses IndexedStack (preserves AR session)
```

### 6.4 Discovery Page Custom AppBar

```
Not a system AppBar — custom Column at top of DiscoveryPage body.
Background: AppColors.darkBgNav, height: ~100px

Row 1 (44px):
  Left: "📍 Gulberg III" — tappable area name (LocationBloc)
  Right: AR | Map | List segment control

Row 2 (44px):
  Full-width pill search bar (AppColors.darkBgElevated bg, border-radius: 22)
  Left: search text input (bodyMedium)
  Right: mic button — 36×36px circle, brandGradient bg, white mic icon
```

---

## 7. STATE MANAGEMENT STRATEGY

### Key BLoCs

**`AuthBloc`:**
- Events: InitializeAuth, LoginWithEmail, Register, Logout, InitializeGuestToken
- States: AuthInitial, AuthLoading, AuthAuthenticated(user), AuthGuest(guestToken), AuthError

**`LocationBloc`:**
- Events: RequestPermission, StartUpdates, StopUpdates
- States: LocationInitial, PermissionDenied, LocationLoading, LocationUpdated(lat, lng, areaName)
- Runs continuously during discovery; `distanceFilter: 30m` for battery efficiency

**`DiscoveryBloc`:**
- Events: SetView, LoadNearbyVendors, SetFilters, SetRadius, TextSearch, VoiceSearchQuery, RefreshVendors
- States: DiscoveryInitial, DiscoveryLoading, DiscoveryLoaded(vendors, activeView, filters), DiscoveryEmpty, DiscoveryError

**`ARBloc`:**
- Events: InitializeAR, UpdateHeading, UpdateMarkers, TapMarker, CollapseMarker
- States: ARInitializing, ARRealMode, ARSimulatedMode, ARLoaded(markers, heading)

**`VoiceBloc`:**
- Events: StartListening, StopListening, ProcessTranscript, VendorBotQuery, Reset
- States: VoiceIdle, VoiceListening, VoiceProcessing(transcript), VoiceResults, VoiceError

**`NavigationBloc`:**
- Events: StartNavigation(vendor), UpdatePosition, CancelNavigation
- States: NavigationIdle, NavigationActive(eta, instruction), NavigationArrived

**`PreferencesBloc`:**
- Events: Load, UpdatePreference, ClearHistory, DeleteAccount, ExportData
- States: PreferencesLoading, PreferencesLoaded, PreferencesUpdating, PreferencesError

### BLoC Registration (get_it + injectable)

- BLoCs: factory (new instance per page)
- Repositories: singleton
- Dio client: singleton

### State Persistence

| State | Storage | Notes |
|---|---|---|
| Auth tokens | `flutter_secure_storage` | Encrypted, survives restart |
| Guest token | `flutter_secure_storage` | Encrypted |
| Theme preference | `hive` box `'settings'` | Fast read on startup |
| Default view (AR/Map/List) | `hive` box `'settings'` | Remembered |
| Search radius | `hive` box `'settings'` | Remembered |
| Cached vendor list | `hive` box `'discovery_cache'` | Offline mode |
| Active filters | DiscoveryBloc in-memory | Not persisted |

---

## 8. API LAYER

### Dio Configuration (`dio_client.dart`)

```dart
Dio(BaseOptions(
  baseUrl: const String.fromEnvironment('API_BASE_URL'),
  connectTimeout: Duration(seconds: 10),
  receiveTimeout: Duration(seconds: 10),
))
// Interceptors: AuthInterceptor, RetryInterceptor (3 retries), LoggingInterceptor (debug only)
```

**AuthInterceptor:** Attaches JWT (`Authorization: Bearer`) OR guest token (`X-Guest-Token`).

> **[AUDIT FIX — HIGH 1.21]** Token refresh race condition must be handled with deduplication. If multiple concurrent requests all get 401 simultaneously, only ONE refresh call should be made — all others queue and retry with the new token.

```dart
// In dio_client.dart — AuthInterceptor:
Future<Response?>? _refreshFuture; // singleton refresh promise

@override
void onError(DioException err, ErrorInterceptorHandler handler) async {
  if (err.response?.statusCode == 401) {
    if (_refreshFuture == null) {
      // First 401 — start refresh, store promise
      _refreshFuture = _doRefresh().whenComplete(() => _refreshFuture = null);
    }
    try {
      await _refreshFuture; // all concurrent 401s wait on same future
      // Retry original request with new token
      final opts = err.requestOptions;
      opts.headers['Authorization'] = 'Bearer ${await secureStorage.getAccessToken()}';
      final retried = await dio.fetch(opts);
      handler.resolve(retried);
    } catch (_) {
      // Refresh failed — logout
      authBloc.add(LogoutEvent());
      handler.reject(err);
    }
  } else {
    handler.next(err);
  }
}

Future<void> _doRefresh() async {
  final refreshToken = await secureStorage.getRefreshToken();
  if (refreshToken == null) throw Exception('No refresh token');
  final resp = await dio.post(ApiEndpoints.tokenRefresh, data: {'refresh': refreshToken});
  await secureStorage.saveTokens(
    access: resp.data['access'],
    refresh: resp.data['refresh'], // rotation — new refresh token on each use
  );
}
```

On refresh failure → `AuthBloc.add(LogoutEvent())` → GoRouter redirects to `/login` with `?returnTo=<currentPath>`.

### API Endpoints (`api_endpoints.dart`)

```dart
class ApiEndpoints {
  static const guestToken   = '/auth/guest/';
  static const login        = '/auth/login/';
  static const register     = '/auth/register/';
  static const tokenRefresh = '/auth/token/refresh/';
  static const me           = '/auth/me/';
  static const deleteAccount = '/auth/account/';
  static const exportData   = '/auth/account/export/';

  static const nearby       = '/discovery/nearby/';
  static const arMarkers    = '/discovery/nearby/ar-markers/';
  static const mapPins      = '/discovery/nearby/map-pins/';
  static const reelsFeed    = '/discovery/nearby/reels/';
  static const search       = '/discovery/search/';
  static const voiceSearch  = '/discovery/voice-search/';
  static const tags         = '/discovery/tags/';
  static const flashAlert       = '/discovery/flash-alert/';
  static const promotionsStrip  = '/discovery/promotions-strip/'; // [AUDIT FIX 1.7] all active promos
  static const citiesSelector   = '/discovery/cities/';           // [AUDIT FIX 1.8] city picker
  static const consentRecord    = '/auth/consent/';               // [AUDIT FIX 3.10] GDPR consent
  static const dealsNearby      = '/deals/nearby/';
  static const preferences      = '/preferences/';
  static const searchHistory    = '/preferences/search-history/';
  static const trackInteraction = '/track/interaction/';
  static const trackReelView    = '/track/reel-view/';

  static String vendorDetail(String id) => '/vendors/$id/';
  static String vendorReels(String id)  => '/vendors/$id/reels/';
  static String vendorVoiceBot(String id) => '/vendors/$id/voice-bot/';
  static String vendorNearby(String id) => '/vendors/$id/nearby/';
}
```

### Error Handling

All repository methods return `Either<Failure, T>`:
```dart
abstract class Failure extends Equatable {}
class NetworkFailure extends Failure {}
class ServerFailure extends Failure { final String message; final int statusCode; }
class AuthFailure extends Failure {}
class NotFoundFailure extends Failure {}
class ValidationFailure extends Failure { final Map<String, List<String>> errors; }
class CacheFailure extends Failure {}
class RateLimitFailure extends Failure { final int retryAfterSeconds; } // [AUDIT FIX 3.5] 429 handling

// HTTP 429 handling in AuthInterceptor:
// if (err.response?.statusCode == 429) {
//   final retryAfter = int.tryParse(err.response?.headers.value('retry-after') ?? '10') ?? 10;
//   handler.reject(DioException(..., error: RateLimitFailure(retryAfterSeconds: retryAfter)));
//   // Show SnackBar: "Searching too fast — try again in Xs"
// }
```

---

## 9. NATIVE AR EXPERIENCE

### 9.1 Three AR Modes (Mobile + Desktop Support)

> **[AUDIT FIX]** Flutter is mobile-only, but requirements specify desktop AR fallback. Since Flutter doesn't support desktop AR, we must define the desktop strategy in coordination with the web frontend.

**Mode A — Real AR (ARCore/ARKit - Mobile Only):**
- Camera permission granted + `ar_flutter_plugin` initializes successfully
- AR overlay on live camera feed
- Target: 30 FPS minimum, 60 FPS target
- Available on: iOS 14+, Android with ARCore support

**Mode B — Simulated AR (Mobile Fallback):**
- Camera denied, ARCore/ARKit unavailable, older device
- Custom gradient background + floating markers (no camera)
- Markers positioned using compass bearing (compass hardware still works)
- Premium look — not a degraded experience
- Available on: All mobile devices as fallback

**Mode C — Desktop/Web AR Coordination:**
- Flutter app is mobile-only **by design**
- Desktop users access AR via web User Portal (React frontend)
- Flutter includes deep links to web AR experience:
  ```dart
  // When desktop AR requested from Flutter
  if (Platform.isMac || Platform.isWindows || Platform.isLinux) {
    final webARUrl = 'https://airads.com/discover?view=ar&lat=$lat&lng=$lng';
    await launchUrl(Uri.parse(webARUrl));
    return; // Exit AR flow
  }
  ```
- Web AR provides same simulated AR experience as Flutter Mode B
- Cross-platform consistency: same ranking algorithm, same marker behavior

**Platform Detection Strategy:**

```dart
enum ARPlatform {
  mobileReal,    // ARCore/ARKit available
  mobileSimulated, // Mobile fallback
  desktopWeb,    // Redirect to web
}

Future<ARPlatform> detectARPlatform() async {
  // Desktop platforms - redirect to web
  if (Platform.isMac || Platform.isWindows || Platform.isLinux) {
    return ARPlatform.desktopWeb;
  }
  
  // Mobile AR capability check
  final cameraPermission = await Permission.camera.status;
  if (cameraPermission.isDenied) return ARPlatform.mobileSimulated;
  
  final arSupported = await _checkARSupport();
  return arSupported ? ARPlatform.mobileReal : ARPlatform.mobileSimulated;
}
```

**Cross-Platform AR Consistency:**

```dart
// Shared AR data model for web-mobile coordination
class ARMarkerData {
  final String vendorId;
  final String vendorName;
  final double lat, lng;
  final double distanceM;
  final String categorySlug;
  final String categoryEmoji;
  final double rankingScore;
  final bool hasActivePromotion;
  final String? promotionLabel;
  
  // Same format used by Flutter and React
  Map<String, dynamic> toJson() => {
    'vendorId': vendorId,
    'vendorName': vendorName,
    'lat': lat,
    'lng': lng,
    'distanceM': distanceM,
    'categorySlug': categorySlug,
    'categoryEmoji': categoryEmoji,
    'rankingScore': rankingScore,
    'hasActivePromotion': hasActivePromotion,
    'promotionLabel': promotionLabel,
  };
  
  factory ARMarkerData.fromJson(Map<String, dynamic> json) => ARMarkerData(/* ... */);
}

// Web AR deep link generation
String generateWebARLink(double lat, double lng, List<ARMarkerData> markers) {
  final params = {
    'view': 'ar',
    'lat': lat.toString(),
    'lng': lng.toString(),
    'markers': markers.map((m) => m.toJson()).toList(),
  };
  
  return 'https://airads.com/discover?' + Uri(queryParameters: params).query;
}
```

**Detection logic in ARBloc:**
1. Check platform type (desktop vs mobile)
2. If desktop → redirect to web AR via deep link
3. If mobile → check camera permission via `permission_handler`
4. Check AR support: `arFlutterPlugin.checkAndroidArCoreAvailability()` / iOS ARKit check
5. Both OK → Mode A; any fail → Mode B
6. No compass → Mode B with fixed marker positions

### 9.2 AR View Layout

```
Mode A: Stack
  [0] ARKitSceneView / ARCoreView (full-screen)
  [1] CompassWidget (top-right, 64×64px)
  [2] AR markers Stack (absolutely positioned)
  [3] DiscoverySearchBar (top overlay)
  [4] RadiusSliderWidget (bottom overlay)
  [5] WalkingSafetyBanner (conditional, top)
  [6] ExpandedMarkerSheet (conditional, bottom)

Mode B: Same overlay stack, GradientBackground Widget at [0]
  Custom animated gradient — dark blues/greens — premium simulated feel
```

### 9.3 AR Marker Positioning Algorithm with Ranking Integration

```dart
// For each vendor:
double bearing   = GeoUtils.calculateBearing(userLat, userLng, vendorLat, vendorLng);
double relative  = (bearing - deviceHeading + 360) % 360;
bool   isVisible = relative <= 60 || relative >= 300;

double normalized = relative <= 180
    ? relative / 180.0       // 0 to 1 (right of center)
    : (relative - 360) / 180.0; // -1 to 0 (left of center)

double screenX = screenWidth * 0.5 + (normalized * screenWidth * 0.6);

// **[AUDIT FIX]** Apply ranking algorithm to AR marker positioning
// Higher-ranked vendors get better positioning and visibility
double rankingScore = vendor.baseRankingScore + vendor.behavioralBoost;

// Scale markers based on ranking (ranked vendors appear larger)
double scale   = (1.0 - (distanceM / maxRadiusM) * 0.5).clamp(0.5, 1.0);
double rankingScale = 1.0 + (rankingScore * 0.3); // Up to 30% larger for top-ranked
scale = scale * rankingScale.clamp(0.8, 1.3);

// Z-index ordering based on ranking (higher-ranked vendors render on top)
int zIndex = (rankingScore * 100).round();

// Visibility priority for high-ranking vendors
// If more than 15 vendors, prioritize top-ranked ones for display
bool shouldRender = isVisible && 
    (_visibleVendors.length < 15 || 
     rankingScore > _rankingThreshold);

// Position adjustment for top 3 ranked vendors (slightly elevated)
double yOffset = 0;
if (rankingScore > 0.8) { // Top 20%
  yOffset = -20.0; // Elevate high-ranking markers
} else if (rankingScore > 0.6) { // Top 40%
  yOffset = -10.0;
}

// Final position with ranking-based adjustments
double screenY = screenHeight * 0.5 + yOffset;

// Store for rendering
if (shouldRender) {
  _visibleVendors.add(ARMarker(
    vendor: vendor,
    x: screenX,
    y: screenY,
    scale: scale,
    zIndex: zIndex,
    rankingScore: rankingScore,
  ));
}
```

**Ranking-Based AR Marker Behavior:**

```dart
class ARMarker {
  final Vendor vendor;
  final double x, y;
  final double scale;
  final int zIndex;
  final double rankingScore;

  // Ranking-based visual enhancements
  Color get markerColor {
    if (rankingScore > 0.8) return AppColors.brandOrange;      // Top 20% - orange
    if (rankingScore > 0.6) return AppColors.brandTeal;        // Top 40% - teal  
    if (rankingScore > 0.4) return AppColors.brandCrimson;     // Mid range - crimson
    return AppColors.tierSilver;                               // Low ranking - grey
  }

  double get opacity {
    return (0.6 + (rankingScore * 0.4)).clamp(0.6, 1.0);
  }

  Duration get animationDuration {
    // Higher-ranked vendors get smoother animations
    return Duration(milliseconds: (800 - (rankingScore * 400)).round());
  }

  bool get hasPulseEffect {
    return rankingScore > 0.7; // Top 30% get pulsing effect
  }
}
```

**Behavioral Learning Integration in AR:**

```dart
// In ARBloc - track AR interactions for behavioral learning
void onMarkerTapped(String vendorId) {
  final vendor = _visibleVendors.firstWhere((m) => m.vendor.id == vendorId);
  
  // Record interaction for behavioral ranking
  _behavioralService.recordInteraction(
    vendorId, 
    'AR_TAP', 
    vendor.rankingScore > 0.7 ? 'positive' : null
  );
  
  // Update AR marker state
  emit(ARMarkerSelected(vendorId));
}

void onMarkerExpanded(String vendorId) {
  _behavioralService.recordInteraction(vendorId, 'AR_EXPAND', 'positive');
}

// Apply behavioral learning to AR marker sorting
List<ARMarker> _sortMarkersByRanking(List<ARMarker> markers) {
  final userProfile = _behavioralService.getUserProfile();
  
  return markers
      .map((marker) => marker.copyWith(
            behavioralBoost: _behavioralService
                .calculatePersonalizationBoost(marker.vendor, userProfile)
          ))
      .sort((a, b) => (b.rankingScore + b.behavioralBoost)
          .compareTo(a.rankingScore + a.behavioralBoost));
}
```

Maximum 15 markers rendered simultaneously (enforced client-side after backend limit), **with ranking-based prioritization**.

### 9.4 ARMarkerWidget Design

```
Collapsed (pill):
  Width: 160-240px (scale-proportional), Height: 56px
  Background: Color(0xCC141414) — semi-transparent dark
  BackdropFilter: ImageFilter.blur(sigmaX:12, sigmaY:12)
  Border: 1px Color(0x1AFFFFFF)
  Border-radius: 28 (full pill)

  Row content:
    [emoji 20px] [vendor_name bold 14px] [distance secondary 12px] [promotion badge]

  Promotion badge (if active):
    AppColors.brandOrange bg, "20% OFF" white 10px bold
    AnimationController: pulsing box-shadow glow (2s loop)

On tap → AnimatedContainer: height 56 → 140, width auto (spring AppDurations.spring)
  Added rows: category chip, hours text, active promotion detail
  3 action buttons (Row):
    TextButton "🧭 Directions" → GoRouter.push('/navigate/:id')
    TextButton "📞 Call" → url_launcher tel:
    TextButton "View →" → GoRouter.push('/vendor/:id')

Tap background → collapseAll (GestureDetector on Stack parent)
```

### 9.5 AR Clustering

```
Client-side: group vendors with angular separation < 8° bearing
If group.length >= 3 → ARClusterWidget

ARClusterWidget:
  Same pill style + orange border (2px)
  Count badge: "5 vendors" + 2 top category emojis

On tap → DraggableScrollableSheet: individual vendor cards (scrollable list)
  Each card tap → GoRouter.push('/vendor/:id')
```

### 9.6 Walking Safety Overlay

```
Trigger: sensors_plus accelerometer magnitude > 1.5 m/s² sustained 2 seconds

WalkingSafetyBanner:
  SlideTransition from top
  AppColors.brandCrimson (85% opacity) background
  "👀 Watch where you're walking!" — 14px white bold
  Height: 44px (non-blocking)
  Auto-dismiss: 3 seconds
  Minimum re-trigger interval: 30 seconds
  Reduced-motion: static banner (no animation)
```

### 9.7 CompassWidget

```
Size: 64×64px
CustomPainter: compass rose with N/S/E/W labels + tick marks
Rotation: RotationTransition driven by AnimationController
  Target: deviceHeading from FlutterCompass.events stream
  Animation: Tween<double>, 150ms, AppCurves.fast (smooth, no jitter)
  Fallback (no compass): static compass
```

---

## 10. VOICE SEARCH — NATIVE MIC INTEGRATION

### 10.1 Permission Flow

```
First voice tap → PermissionService.requestMicrophone()

If granted: proceed directly

If denied: bottom sheet:
  Icon: mic-off (Lucide)
  Title: "Microphone Access Needed"
  Body: "Enable in Settings to use voice search."
  CTA: "Open Settings" → openAppSettings()
  Secondary: "Type Instead" → keyboard focus on search field
```

### 10.2 VoiceBloc States

```
VoiceIdle:       Static mic button (gradient circle)
VoiceListening:  Mic button pulsing (AnimationController scale 1.0↔1.15, 800ms loop)
                 Lottie voice_wave.json playing
                 Real-time transcript displayed
VoiceProcessing: CircularProgressIndicator replaces mic, "Searching..." text
VoiceResults:    Results in active discovery view, overlay dismissed
VoiceError:      Error message + retry button + type-instead option
```

### 10.3 Multi-Language SpeechToText Usage Pattern

> **[AUDIT FIX]** Requirements specify support for Urdu, English, and Roman Urdu. Current implementation only supports English. Must add multi-language detection and processing.

```dart
final speech = SpeechToText();

// Language detection and initialization
Future<bool> initializeVoiceSearch() async {
  // Detect device preferred language
  final locale = Platform.localeName; // e.g., 'en_US', 'ur_PK', 'en_PK'
  final languageCode = locale.split('_')[0]; // 'en', 'ur'
  
  // Map to supported voice search languages
  final voiceLocale = _mapToVoiceLocale(languageCode);
  
  return await speech.initialize(
    onStatus: (s) => add(VoiceStatusChanged(s)),
    onError:  (e) => add(VoiceError(e.errorMsg)),
    finalTimeout: Duration(seconds: 10),
  );
}

String _mapToVoiceLocale(String languageCode) {
  switch (languageCode) {
    case 'ur':
      return 'ur_PK'; // Urdu (Pakistan)
    case 'en':
      return 'en_US'; // English (US) - default
    default:
      return 'en_US'; // Fallback to English
  }
}

// Dynamic locale selection based on user preference
Future<void> startListening() async {
  final userPreferredLanguage = getUserLanguagePreference(); // From preferences
  
  final voiceLocale = userPreferredLanguage == 'ur' ? 'ur_PK' : 'en_US';
  
  await speech.listen(
    onResult: (result) => add(VoiceTranscriptUpdated(
      result.recognizedWords,
      result.finalResult,
    )),
    listenMode:    ListenMode.dictation,
    partialResults: true,   // word-by-word display
    cancelOnError:  true,
    pauseFor:       Duration(seconds: 2),  // auto-stop on silence
    localeId:       voiceLocale, // Dynamic locale
  );
}
```

### 10.4 Multi-Language NLP Keyword Extraction (`nlp_utils.dart`)

> **[AUDIT FIX]** Must support Urdu, English, and Roman Urdu keyword extraction. Rule-based approach with language-specific keyword maps.

```dart
class NlpUtils {
  static Map<String, dynamic> extractIntent(String transcript) {
    // Detect language first
    final detectedLanguage = _detectLanguage(transcript);
    
    switch (detectedLanguage) {
      case 'urdu':
        return _extractUrduIntent(transcript);
      case 'roman_urdu':
        return _extractRomanUrduIntent(transcript);
      case 'english':
      default:
        return _extractEnglishIntent(transcript);
    }
  }
  
  static String _detectLanguage(String transcript) {
    // Simple language detection based on script
    final hasUrduChars = transcript.contains(RegExp(r'[\u0600-\u06FF]'));
    final hasRomanChars = transcript.contains(RegExp(r'[a-zA-Z]'));
    
    if (hasUrduChars && !hasRomanChars) return 'urdu';
    if (hasRomanChars && _containsUrduWords(transcript)) return 'roman_urdu';
    return 'english';
  }
  
  static bool _containsUrduWords(String transcript) {
    final romanUrduWords = [
      'biryani', 'kabab', 'chai', 'nashta', 'dinner', 'lunch',
      'sasta', 'mahenga', 'kareeb', 'door', 'abhi', 'kal',
      'acha', 'bura', 'teek', 'theek', 'hai', 'hain'
    ];
    final lower = transcript.toLowerCase();
    return romanUrduWords.any((word) => lower.contains(word));
  }

  // English keyword extraction
  static Map<String, dynamic> _extractEnglishIntent(String transcript) {
    final lower = transcript.toLowerCase();
    String? category;
    for (final e in _englishCategoryKeywords.entries) {
      if (e.value.any(lower.contains)) { category = e.key; break; }
    }
    final priceIntent = ['cheap','budget','affordable','expensive']
        .any(lower.contains) ? 'budget-friendly' : null;
    final openNow = ['open','right now','currently'].any(lower.contains);
    final action = ['take me to','directions','navigate'].any(lower.contains)
        ? 'NAVIGATE' : 'DISCOVER';
    return {'category': category, 'priceIntent': priceIntent, 'openNow': openNow, 'action': action};
  }

  // Urdu keyword extraction (Urdu script)
  static Map<String, dynamic> _extractUrduIntent(String transcript) {
    String? category;
    for (final e in _urduCategoryKeywords.entries) {
      if (transcript.contains(e.key)) { category = e.value; break; }
    }
    final priceIntent = transcript.contains('سستا') || transcript.contains('سستی')
        ? 'budget-friendly' : null;
    final openNow = transcript.contains('ابھی') || transcript.contains('فی الحال');
    final action = transcript.contains('لے چلو') || transcript.contains('راستہ')
        ? 'NAVIGATE' : 'DISCOVER';
    return {'category': category, 'priceIntent': priceIntent, 'openNow': openNow, 'action': action};
  }

  // Roman Urdu keyword extraction
  static Map<String, dynamic> _extractRomanUrduIntent(String transcript) {
    final lower = transcript.toLowerCase();
    String? category;
    for (final e in _romanUrduCategoryKeywords.entries) {
      if (e.value.any(lower.contains)) { category = e.key; break; }
    }
    final priceIntent = ['sasta','sasti','mahenga','cheap','budget']
        .any(lower.contains) ? 'budget-friendly' : null;
    final openNow = ['abhi','filhaal','open','right now'].any(lower.contains);
    final action = ['le chalo','rasta','directions','navigate'].any(lower.contains)
        ? 'NAVIGATE' : 'DISCOVER';
    return {'category': category, 'priceIntent': priceIntent, 'openNow': openNow, 'action': action};
  }

  // Multi-language keyword maps
  static const Map<String, List<String>> _englishCategoryKeywords = {
    'pizza': ['pizza'],
    'burger': ['burger', 'burgers'],
    'biryani': ['biryani', 'rice'],
    'cafe': ['cafe', 'coffee', 'tea'],
    'salon': ['salon', 'haircut', 'barber'],
    // ... all English categories
  };

  static const Map<String, String> _urduCategoryKeywords = {
    'بیرونی': 'biryani',
    'کباب': 'kabab',
    'چائے': 'cafe',
    'بیوٹی پارلر': 'salon',
    // ... all Urdu categories
  };

  static const Map<String, List<String>> _romanUrduCategoryKeywords = {
    'biryani': ['biryani', 'biryan'],
    'kabab': ['kabab', 'kebab'],
    'chai': ['chai', 'tea', 'chaye'],
    'salon': ['salon', 'beauty parlor', 'haircut'],
    // ... all Roman Urdu categories
  };
}
```

### 10.5 Language Preference Management

```dart
// In preferences bloc
class VoiceLanguagePreference {
  static const String english = 'english';
  static const String urdu = 'urdu';
  static const String romanUrdu = 'roman_urdu';
  
  static String getDisplayName(String languageCode) {
    switch (languageCode) {
      case english: return 'English';
      case urdu: return 'اردو (Urdu)';
      case romanUrdu: return 'Roman Urdu';
      default: return 'English';
    }
  }
  
  static String getVoiceLocale(String languageCode) {
    switch (languageCode) {
      case urdu: return 'ur_PK';
      case english:
      case romanUrdu:
      default: return 'en_US';
    }
  }
}

// UI for language selection
Widget buildVoiceLanguageSelector() {
  return DropdownButton<String>(
    value: voiceLanguagePreference,
    items: [
      DropdownMenuItem(value: VoiceLanguagePreference.english, child: Text('English')),
      DropdownMenuItem(value: VoiceLanguagePreference.urdu, child: Text('اردو')),
      DropdownMenuItem(value: VoiceLanguagePreference.romanUrdu, child: Text('Roman Urdu')),
    ],
    onChanged: (language) {
      // Save preference
      preferencesBloc.add(UpdateVoiceLanguage(language!));
    },
  );
}
```

  // Full keyword map: 50+ categories
  static const _categoryKeywords = {
    'pizza':   ['pizza'],
    'burger':  ['burger', 'burgers'],
    'biryani': ['biryani', 'rice'],
    'cafe':    ['cafe', 'coffee', 'chai', 'tea'],
    'salon':   ['salon', 'haircut', 'barber', 'hair'],
    // ... all 50+ entries matching backend keyword_map.py
  };
}
```

### 10.5 Voice Overlay Layout

```
Modal barrier (dark, 85% opacity)
Center card:
  AppColors.darkBgSurface bg, border-radius: 24, padding: 32
  Width: min(360, screenWidth - 40)

  Content (Column):
    Lottie(voice_wave.json, 120px height) — while listening
    OR static mic icon (idle state)
    
    Transcript text:
      "cheap pizza near me"
      Italic while listening, fontStyle normal after final
      Color: darkTextPrimary
      Animated character reveal (flutter_animate .fadeIn .slideX stagger)
    
    Status text: "Listening..." / "Searching..." / error message
    
    4 suggestion chips (Wrap, before listening starts, vanish when speech begins):
      TagChip-equivalent, tappable → auto-send that query
    
    TextButton "Cancel" (brandCrimson)
```

### 10.6 Vendor Voice Bot TTS

```dart
// flutter_tts (voice bot response playback)
final tts = FlutterTts();
await tts.setLanguage("en-US");
await tts.setSpeechRate(0.9);  // slightly slower
await tts.setVolume(1.0);

await tts.speak(responseText);
```

Mute state: `VoiceBloc.isTTSEnabled` — persisted in Hive.
TTS stops automatically when app backgrounded.
iOS TTS restriction: only fires after user taps mic (counts as user interaction).

---

*Continues in USER_PORTAL_FLUTTER_PLAN_PART2.md*
