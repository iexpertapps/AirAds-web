# USER PORTAL FLUTTER PLAN — PART 2
## Location Services, Maps, All Screens, Push Notifications, Offline Mode, Performance, iOS/Android, App Store, Build Sequence, QA

Part 2 of User Portal Flutter Plan. Part 1 covered: App identity, architecture, tech stack, project structure, design system, app shell, state management, API layer, native AR, voice search.

---

## TABLE OF CONTENTS (Part 2)

11. [Location Services](#11-location-services)
12. [Map Integration](#12-map-integration)
13. [Screen-by-Screen Plan](#13-screen-by-screen-plan)
14. [Push Notifications Strategy](#14-push-notifications)
15. [Offline Mode Plan](#15-offline-mode)
16. [Performance Considerations](#16-performance)
17. [iOS vs Android Differences](#17-ios-vs-android-differences)
18. [App Store Deployment Requirements](#18-app-store-deployment)
19. [Branding Consistency](#19-branding-consistency)
20. [Build Sequence & Sessions](#20-build-sequence)
21. [Quality Gate Checklist](#21-quality-gate-checklist)

---

## 11. LOCATION SERVICES

### 11.1 Permission Flow

```
On first Discovery screen mount:

If status = 'denied' (never asked):
  Show pre-permission dialog (our own dialog BEFORE system dialog):
    Icon: large location pin (brandOrange)
    Title: "Enable Location for Better Results"
    Body: "We'll show vendors right where you are. Your location never leaves your
           device while browsing."
    CTA: "Enable Location" → then trigger system permission dialog
    Secondary: "Maybe Later" → fallback mode (city center or last known)

If 'deniedForever' (Android) / 'restricted' (iOS):
  Info chip in discovery: "Location disabled — showing city-wide results"
  Tappable: "Enable in Settings →" → openAppSettings()
  No crash, no blocking screen

If 'granted': proceed with GPS stream
```

**GPS Grant Rate Target: 90%** — pre-permission dialog is the critical enabler of this target.

### 11.2 Location Tracking Strategy

```dart
// LocationBloc.startUpdates():
Geolocator.getPositionStream(
  locationSettings: LocationSettings(
    accuracy: LocationAccuracy.high,
    distanceFilter: 30,  // emit only if moved > 30m (battery efficiency)
  )
).listen((position) {
  emit(LocationUpdated(position.latitude, position.longitude));
});
```

**On each update:**
1. Emit `LocationUpdated` → `DiscoveryBloc` refetches if moved > 30m
2. `NavigationBloc` checks arrival: `distance_to_dest < 30m`
3. Reverse geocode every 100m movement → update `areaName`

**Navigation mode:** higher accuracy, `distanceFilter: 5m`, switched when NavigationBloc starts.

**App pause/resume:** `WidgetsBindingObserver` in AppShell → stop on pause, restart on resume.

**Background mode (Phase-1):** NOT implemented. Push notifications handle background deal alerts via FCM (no background location required).

### 11.3 Area Name Display

```dart
// geocoding package
List<Placemark> placemarks = await placemarkFromCoordinates(lat, lng);
String areaName = placemarks.first.subLocality    // "Gulberg III"
                ?? placemarks.first.locality       // "Lahore"  
                ?? "Nearby";
```

Cached in `LocationBloc` state — not re-queried unless user moves > 100m. Displayed in discovery app bar.

---

## 12. MAP INTEGRATION

### 12.1 Mapbox Flutter Setup

Package: `mapbox_maps_flutter` (official Mapbox SDK for Flutter).
Token: `--dart-define=MAPBOX_TOKEN=<token>` at build time. Never in source code.
Style: `MapboxStyles.DARK` — built-in dark style matching app theme.

### 12.2 Vendor Pins Layer

```dart
// Custom PointAnnotations per vendor
for (final vendor in mapPins) {
  await pointAnnotationManager.create(
    PointAnnotationOptions(
      geometry: Point(coordinates: Position(vendor.lng, vendor.lat)),
      iconImage: _tierPinImageName(vendor.tier),  // pre-loaded asset
      iconSize: vendor.hasActivePromotion ? 1.3 : 1.0,
    ),
  );
}
```

**Tier pin images** (pre-rendered PNG assets in `assets/images/`):
- `silver_pin.png` — grey #9E9E9E rounded pin (32×40px)
- `gold_pin.png` — gold #FFC107
- `diamond_pin.png` — teal #00BCD4
- `platinum_pin.png` — gradient (orange→crimson, pre-rendered offline tool)

**Promotion pulsing ring:** separate `AnimatedWidget` overlay at same screen coordinates — Mapbox `PointAnnotation` doesn't support CSS animations, so native `AnimationController` used for ring.

### 12.3 On Pin Tap

```dart
// MapboxMap onTap listener
mapboxMap.setOnMapTapListener((point) async {
  final vendor = await _findNearestPin(point);  // within 44px radius
  if (vendor != null) {
    DiscoveryBloc.add(SelectVendor(vendor.id));
    // Show DraggableScrollableSheet
  }
});
```

**Bottom sheet:**
- `DraggableScrollableSheet(initialChildSize: 0.35, minChildSize: 0.1, maxChildSize: 0.6)`
- Content: drag handle, vendor name, category, distance, open status, promotion, two buttons

### 12.4 Filter Chips on Map

Horizontal `SingleChildScrollView` with category + status chips overlaid at map top.
Active chip: `AppColors.brandOrange` bg.
Filter change → DiscoveryBloc → refetch mapPins → reload PointAnnotations (fade transition).

### 12.5 Map Camera

```dart
// Initial fly-to on location granted:
mapboxMap.flyTo(
  CameraOptions(
    center: Point(coordinates: Position(lng, lat)),
    zoom: 15.0,
  ),
  MapAnimationOptions(duration: 1000),
);

// Zoom based on radius:
// 100m=17, 500m=15, 1km=14, 2km=13, 5km=12
```

---

## 13. SCREEN-BY-SCREEN PLAN

### 13.1 Splash Screen (< 1.5s)

```
Background: AppColors.brandBlack
Center: AirAds logo (80px) + flutter_animate:
  .fadeIn(duration: 400ms) + .scale(begin: Offset(0.9, 0.9), end: Offset(1, 1))

During splash:
  1. Hive.initFlutter() + open all boxes
  2. Check SecureStorage for tokens
  3. Firebase.initializeApp()
  4. Navigate: first launch → /landing, returning user → /discover
```

### 13.2 Landing / Onboarding (First Launch Only)

```
3-slide PageView onboarding (stored in Hive: 'onboarding_complete')

Slide 1 — AR Discovery:
  Dark gradient background + floating ARMarkerWidget simulations
  Title: "Discover What's Around You"
  Body: "Point your phone and see nearby vendors in your camera view."

Slide 2 — Voice Search:
  Dark bg + animated mic + Lottie voice_wave.json
  Title: "Just Say What You Want"
  Body: "'Cheap lunch near me' — we understand."

Slide 3 — Real Deals:
  Dark bg + deal card with pulsing CountdownTimerWidget
  Title: "Real Deals, Right Now"
  Body: "Active discounts from shops near you."

Navigation:
  Page indicator dots: AnimatedContainer width 24px (active) → 6px (inactive)
  "Skip" button: top-right TextButton
  "Next" / "Start Exploring →" button: bottom, gradient bg

On completion:
  Hive.box('settings').put('onboarding_complete', true)
  GoRouter.go('/discover') with guest token auto-initialized
```

### 13.3 Login Page (`/login`)

```
Scaffold, no AppBar (transparent status bar overlay)
Background: AppColors.darkBgPage

Column centered:
  AirAds logo (64px) + flutter_animate float
  Heading: "Welcome back, Explorer." (heading2, white)
  
  Form:
    TextFormField: email (keyboard: email, autocomplete: email)
    TextFormField: password (obscureText, suffix Eye icon toggle)
    "Forgot password?" TextButton (right-aligned)
    
    ElevatedButton: "Sign In" (gradient bg, fullWidth, 52px height, loading state)
    
    Divider row: "or" (12px tertiary text)
    
    OutlinedButton: "Continue as Guest →" (fullWidth, 52px)
      → guest token issued → GoRouter.go('/discover')
    
    TextButton: "New to AirAds? Register Free →" (brandOrange)

Error handling:
  Field validation: inline red text below each field (bodySmall, error color)
  Auth errors: SnackBar at bottom (brand surface color, not obscuring form)
```

### 13.4 Register Page (`/register`)

```
Form:
  First name (TextFormField)
  Email (TextFormField)
  Password (obscure) + LinearProgressIndicator (4 segments: red/orange/amber/green strength)
  Terms checkbox (required, links to terms URL)

Submit: "Create Account — It's Free" (gradient, fullWidth, 52px)

Success state (replaces form, no navigation):
  Lottie: arrival_checkmark.json (teal checkmark, 120px)
  "Check Your Email!" (heading2)
  "We sent a link to [email]." (bodyMedium secondary)
  Resend link with CountdownTimerWidget (60s cooldown, disabled until 0)
  TextButton "Back to Sign In"
```

### 13.5 Discovery Page (Main Shell)

```
BlocProvider tree at DiscoveryPage level:
  LocationBloc — starts on build
  DiscoveryBloc — listens to LocationBloc
  ARBloc — AR sub-view only
  VoiceBloc — global voice search

Layout:
  SafeArea top → Custom AppBar (100px)
  Body → IndexedStack (AR=0, Map=1, List=2):
    Preserves all sub-views mounted — AR session never destroyed on switch
  SafeArea bottom → AppShell BottomNavigationBar

Location permission states:
  Requesting: "Finding your location..." + skeleton card list
  Denied: info chip "Enable location for better results" + city-level results
  Error: OfflineBannerWidget equivalent for location error
```

### 13.6 AR View

Covered in Section 9 (Part 1). Key implementation notes:
- `ARBloc` initialized lazily on first AR view activation (not on app start)
- `IndexedStack` keeps AR session alive when switching to Map/List
- `CompassWidget` subscribes to `FlutterCompass.events` stream via `ARBloc`
- `RadiusSliderWidget` at bottom: `CupertinoSlider` (iOS) / `Slider` (Android) — value from `DiscoveryBloc`

### 13.7 Map View

Covered in Section 12. Key notes:
- `MapWidget` lazy-initialized (heavy) — only when Map view first selected
- Filter chips: `SingleChildScrollView(scrollDirection: Axis.horizontal)` overlaid
- `DraggableScrollableSheet` for pin taps
- Radius slider overlaid at bottom (same widget as AR view)

### 13.8 List View

```
CustomScrollView with SliverList

Header: SliverAppBar (transparent, pinned, flexibleSpace = filter chips row)
Sort: PopupMenuButton top-right of list header
  Options: "Best Match" | "Nearest" | "Active Deals"

SliverList delegate: SliverChildBuilderDelegate
  VendorCardWidget (88px height each)
  VendorCardSkeleton while loading (shimmer)

Infinite scroll:
  NotificationListener<ScrollNotification> → loadMore when scrolled 80% down
  BLoC event: FetchMoreVendors

Pull-to-refresh: RefreshIndicator wrapping CustomScrollView
  Color: AppColors.brandOrange
  Trigger: DiscoveryBloc.add(RefreshVendors())

Empty state: EmptyStateWidget (logo opacity 0.12 + context message + 2 action buttons)
```

### 13.9 Tag Browser Page (`/browse`)

```
Route: /browse (bottom nav tab 4)
Scaffold with AppBar: "Browse & Filter" + floating count chip

4 sections in SingleChildScrollView:

Section 1 — Hot Right Now:
  "🔥 What's Hot Right Now" label (labelMedium, secondary)
  SingleChildScrollView(horizontal): chips with deal count

Section 2 — By Intent:
  "✨ What are you looking for?" label
  GridView.count(crossAxisCount: 2, childAspectRatio: 2.5):
    InkWell card: emoji (28px) + label + vendor count
    Active: brand orange border + bg tint

Section 3 — By Category:
  GridView.count(crossAxisCount: 3)
  All category tags with counts

Section 4 — By Distance:
  3 ListTile-style cards (walking / nearby / in my area)
  Active: orange left border

Multi-select state: TagBrowserBloc
  FloatingActionButton (visible when tags > 0):
    "Show 23 Results →" (brandOrange bg)
    Count from preview query (debounced 300ms)
    On tap → DiscoveryBloc.add(SetFilters(selectedTags)) → GoRouter.go('/discover')
```

### 13.10 Vendor Profile Page (`/vendor/:id`)

```
CustomScrollView with SliverAppBar:
  expandedHeight: 220
  pinned: true
  flexibleSpace: FlexibleSpaceBar(
    background: CachedNetworkImage (cover, objectFit: cover)
                OR gradient fallback + category emoji
    stretchModes: [StretchMode.zoomBackground]  // parallax
  )
  Collapsed bar: "← [VendorName]" + distance + open status + voice bot icon

Collapsed to: sticky bar showing: distance · category · open/closed

SliverList content (6 sections):

1. ACTIVE PROMOTION CARD (if active):
   Container with gradient border (brandOrange tint)
   PromotionBadgeWidget (lg) + description + CountdownTimerWidget
   "Get Directions Now →" ElevatedButton (gradient, fullWidth)
   Urgent glow: BoxDecoration with BoxShadow (crimson, animated)

2. ABOUT:
   Description (ReadMoreText widget — 3 lines + "Show more" ExpandableText)
   Business hours: 7-column GridView (today highlighted orange)
   Contact: InkWell phone (→ url_launcher tel:) + website (→ launchUrl)
   Service chips: Row of ReadOnly chips

3. VIDEOS/REELS (if reels_count > 0):
   "📹 Videos ([n])" header
   SizedBox(height: 200):
     ListView.builder(scrollDirection: Axis.horizontal):
       GestureDetector thumbnail card (120×180px)
       First card: VideoPlayerWidget (autoplay muted, IntersectionObserver equivalent)
       Tap → push fullscreen reel player

4. LOCATION:
   ClipRRect(borderRadius: 12): StaticMapImage (Mapbox Static Images API URL)
   Tappable → GoRouter.push('/discover') with vendor pre-pinned
   Address text (bodySmall secondary)
   ElevatedButton "🧭 Get Directions →" (outlined, fullWidth)

5. VOICE BOT (if voice_bot.available):
   Card (darkBgElevated, rounded corners)
   Mic icon (40px, crimson AnimationController glow) + title + suggested queries
   ElevatedButton "Ask Now" → show ModalBottomSheet (VoiceBotSheet widget)

6. MORE NEARBY:
   "More [Category] Nearby" header + TextButton "See all →"
   SizedBox(height: 120):
     ListView.builder(horizontal): 6 compact VendorCardWidget

FloatingActionButton (positioned):
  Visible from load until Section 4 enters view (ScrollController position check)
  "🧭 Get Directions" (gradient bg, extended FAB)
  OnTap → GoRouter.push('/navigate/${vendor.id}')
```

### 13.11 Deals Page (`/deals`)

```
Scaffold:
  AppBar: "🔥 Active Near You" + AnimatedSwitcher count badge

  Filter bar: SingleChildScrollView(horizontal) chips

  Sort: trailing DropdownButton in AppBar ("Ending Soon" default)

  RefreshIndicator + ListView.builder:
    DealCardWidget (~130px height):
      Top row: PromotionBadgeWidget (lg) + CountdownTimerWidget (urgency colors)
      Middle: vendor name (bold) + category emoji
      Bottom: distance + open status + "Get Directions →" TextButton

  Urgency system:
    > 2h: normal styling
    1-2h: CountdownTimer color=AppColors.warning, card left-border amber
    < 1h: CountdownTimer color=AppColors.brandCrimson pulsing, card shadow red glow

Flash Deal Toast (OverlayEntry):
  Inserted via Overlay.of(context).insert(...)
  SlideTransition from top (AppDurations.spring, y: -1 → 0)
  Gradient container (orange → crimson)
  🔥 + message + "View →" + × dismiss
  Timer(8s) → auto-remove
  FlashAlertBloc tracks seen discount IDs (sessionStorage equivalent = in-memory Map)
```

### 13.12 Reels Page (`/reels`)

```
Full-screen Scaffold, no AppBar, no bottom nav (AppShell hides BottomNav when on Reels)

PageView(
  scrollDirection: Axis.vertical,
  physics: PageScrollPhysics(),
  controller: PageController(),
):
  ReelPageWidget (height: MediaQuery.of(context).size.height):

    Stack:
      [0] VideoPlayer (video_player + chewie, full-screen cover)
          autoInitialize: true, autoPlay: true, looping: false, volume: 0 (muted default)
      
      [1] GradientOverlay (bottom 40%: transparent → black)
      
      [2] Positioned bottom-left: vendor info column
          Text(vendor.name, bold 18px, white, shadow)
          TagChip widget (category, semi-transparent dark)
          Text("📍 ${distance}m away", 13px white)
      
      [3] Positioned bottom-right:
          ElevatedButton circle: "🧭" 48×48px, brandOrange bg
          OnTap → GoRouter.push('/navigate/:id')
      
      [4] Positioned bottom-center (if promotion):
          SlideTransition(begin: Offset(0, 1), end: Offset.zero, 600ms delay)
          Container pill: "🔥 20% OFF · Tap to visit →" (brandOrange bg)
          GestureDetector → GoRouter.push('/vendor/:id') + trackInteraction(PROMOTION_TAP)
      
      [5] Positioned top: 
          SizedBox(height: 3):
            AnimatedContainer width from 0 → screenWidth over video duration
            Color: brandOrange

GestureDetector on Stack:
  onTap: toggle pause/play
  onDoubleTap (left half): seek -5s
  onDoubleTap (right half): seek +5s

Page change:
  PageController.addListener → pause previous, play current
  ReelViewTracker: Duration startTime on page enter, POST on page exit

Right-edge scroll indicator: 5 dots (ScrollController position → active dot)
```

### 13.13 Navigation Page (`/navigate/:id`)

> **[AUDIT FIX — HIGH 1.19]** In-app Mapbox navigation is excellent but some users strongly prefer their default map app (Google Maps / Apple Maps / Waze). The navigation page must offer a choice.

```
Navigation Entry Bottom Sheet (shown BEFORE starting in-app nav):
  Triggered when user taps any "Get Directions" button anywhere
  
  DraggableScrollableSheet (initialChildSize: 0.38):
    Title: "🧭 Navigate to [VendorName]"
    
    Column of 3 options (ListTile style):
    
    Option A — In-App Navigation (default, highlighted):
      Leading: Mapbox logo (16px) + Icon(navigation)
      Title: "AirAds Navigation" (bold)
      Subtitle: "In-app walking guide with AR arrival"
      Trailing: "Recommended" chip (brandOrange bg, white 10px)
      OnTap → dismiss sheet → GoRouter.push('/navigate/\${vendor.id}')
    
    Option B — Google Maps:
      Leading: Google Maps logo asset
      Title: "Google Maps"
      Subtitle: "Opens Google Maps app"
      OnTap → launchUrl(Uri.parse('comgooglemaps://?daddr=\${lat},\${lng}&directionsmode=walking'))
              fallback: launchUrl(Uri.parse('https://maps.google.com/?daddr=\${lat},\${lng}&travelmode=walking'))
    
    Option C — Apple Maps (iOS only, Platform.isIOS check):
      Leading: Apple Maps icon
      Title: "Apple Maps"
      OnTap → launchUrl(Uri.parse('http://maps.apple.com/?daddr=\${lat},\${lng}&dirflg=w'))
    
    "Cancel" TextButton at bottom
```

```
In-App Navigation Screen (after Option A selected):
Full-screen Scaffold, no bottom nav

Stack:
  [0] MapWidget (full-screen, navigation-focused style)
      - User location: built-in pulsing teal dot (geolocate)
      - Destination: pulsing PointAnnotation (brandOrange)
      - Route: LineAnnotation (brandGradient colors, width: 5)
        DrawLine animation: dasharray animated in (1s)
      
  [1] NavigationHeaderWidget (Positioned top):
      Container(height: 90 + safeArea, color: darkBgSurface, blur filter)
      Column:
        "~ 4 min walk" (heading3, white) + "320m" (secondary)
        "Raja Burgers" (labelLarge, truncated, teal color)
      Positioned right: TextButton "Cancel" → NavigationBloc.add(CancelNavigation())
      
  [2] InstructionStripWidget (Positioned bottom):
      Container(height: 80 + safeArea, blur filter)
      Row:
        RotationTransition(turns: headingAnim): arrow icon (Lucide ArrowUp variant)
        Expanded Column:
          Text(currentInstruction, labelLarge, white bold)
          Text(nextInstruction, bodySmall, secondary)
      
  [3] VendorMiniCardWidget (Positioned: top + 90px, height: 56px):
      InkWell: thumbnail + vendor name + active promotion badge
      OnTap → AnimatedContainer height 56 → 200: full promotion card + voice bot button

Navigation updates:
  LocationBloc stream → NavigationBloc
  On position: recalculate distance, update ETA, camera follow user
  MapboxMap.easeTo follows user heading + position (heading lock)
  Arrival check: distance_to_dest < 30m → NavigationBloc.add(Arrived())

Arrival overlay (OverlayEntry, full-screen):
  Dark barrier (rgba 0.85)
  Lottie(arrival_checkmark.json, 140px height, repeat: false)
  "You've arrived at [Name]! 🎉" (heading2, white, centered)
  Active promotion card (if any) — compact version
  3 Column buttons:
    ElevatedButton "🔍 Find Another Place" → GoRouter.go('/discover')
    OutlinedButton "View Full Profile" → GoRouter.push('/vendor/:id')
    TextButton "Done" → Navigator.pop()
  
  Fire: trackInteraction(ARRIVAL) on show
```

### 13.14 Preferences / Me Page (Complete Guest/Logged-in Support)

> **[AUDIT FIX]** Guest mode must support preference persistence and proper capability distinction. Guests can access basic settings but not notification preferences or account management.

```
Route: /me (bottom nav) or /preferences (direct)

Scaffold AppBar: "Preferences" (or "⚙️ Me" for bottom nav entry)

Guest top card (if guest):
  Container (darkBgElevated, rounded, padding 20):
    Row: person icon (48px orange) + Column("Explorer" heading3, "Guest Mode" chip)
    SizedBox(height: 12)
    Row: ElevatedButton "Sign In →" + OutlinedButton "Register Free →"
    SizedBox(height: 8)
    Text("Your preferences are saved on this device only", 
         style: captionSecondary, textAlign: TextAlign.center)

Logged-in top card:
  CircleAvatar (brandOrange bg, initial letter, radius: 24) + display_name + email
  Subtitle: "Your preferences sync across all your devices"

ListView sections (ListTile grouped, StickyHeader or simple Padding titles):

Discovery Settings (Available to BOTH guest and logged-in):
  "Default View" → Radio group (AR/Map/List) as custom pill control
  "Search Radius" → CupertinoSlider (iOS) or Slider (Android), 5 tick labels
                    live preview "Seeing ~23 vendors" (debounced query)
  "Show Open Now Only" → CupertinoSwitch (iOS) / Switch (Android)
  "Default Category" → DropdownButton (styled)
  "Voice Search Language" → DropdownButton (English | اردو | Roman Urdu)

Notification Preferences (LOGGED-IN ONLY):
  If guest: 
    Container (darkBgSurface, rounded, padding 16):
      Icon(Icons.notifications_off, color: tertiary)
      SizedBox(height: 8)
      Text("Sign in to enable deal alerts and vendor updates", style: bodyMedium)
      SizedBox(height: 12)
      Row: ElevatedButton "Sign In →" (compact) + OutlinedButton "Register →" (compact)
  
  If logged-in:
    Master "All Notifications Off" SwitchListTile
    Nearby Deals SwitchListTile
    Flash Deals SwitchListTile  
    Vendor Updates SwitchListTile

Appearance (Available to BOTH guest and logged-in):
  Theme → SegmentedButton("Dark" | "Light" | "System")
  OnChanged → ThemeBloc → MaterialApp.themeMode → Hive.put

Privacy & Data:
  ExpansionTile "What we collect": 4 bullet points
  
  // Available to BOTH guest and logged-in
  ListTile "Clear Search History" → showDialog(confirm) → 
    If guest: clear local Hive storage only
    If logged-in: DELETE API + clear local Hive storage
    toast: "Search history cleared"
  
  // LOGGED-IN ONLY
  If logged-in:
    ListTile "Delete Account" (crimson) → confirmation flow
    ListTile "Export My Data" → GET export → saveFile

About:
  ListTile "Version 1.0.0" (no tap)
  ListTile "For Vendors →" → launchUrl(vendorPortalUrl)
  ListTile "Privacy Policy" → launchUrl
  ListTile "Terms of Service" → launchUrl
```

### 13.15 Guest Mode Preference Persistence

> **[AUDIT FIX]** Guests need preference persistence for good UX, but it must be local-only and clearly labeled.

**Guest Preference Storage Strategy:**

```dart
// In services/guestPreferencesService.dart
class GuestPreferencesService {
  static const String _guestPrefsBox = 'guest_preferences';
  
  // Guest preferences (local-only, never synced)
  static const Map<String, dynamic> _defaultGuestPrefs = {
    'defaultView': 'AR',
    'searchRadius': 800, // meters
    'showOpenNowOnly': false,
    'defaultCategory': 'all',
    'theme': 'dark',
    'voiceLanguage': 'english',
    'lastUpdated': null,
  };
  
  Future<void> initializeGuestPreferences() async {
    final box = await Hive.openBox(_guestPrefsBox);
    
    // Set defaults if first launch
    if (box.isEmpty) {
      for (final entry in _defaultGuestPrefs.entries) {
        await box.put(entry.key, entry.value);
      }
      await box.put('lastUpdated', DateTime.now().toIso8601String());
    }
  }
  
  Future<void> updateGuestPreference(String key, dynamic value) async {
    final box = await Hive.openBox(_guestPrefsBox);
    await box.put(key, value);
    await box.put('lastUpdated', DateTime.now().toIso8601String());
  }
  
  Future<T?> getGuestPreference<T>(String key) async {
    final box = await Hive.openBox(_guestPrefsBox);
    return box.get(key) as T?;
  }
  
  Future<void> clearGuestPreferences() async {
    final box = await Hive.openBox(_guestPrefsBox);
    await box.clear();
  }
  
  // Migration to logged-in preferences
  Future<Map<String, dynamic>> exportGuestPreferences() async {
    final box = await Hive.openBox(_guestPrefsBox);
    return Map<String, dynamic>.from(box.toMap());
  }
}
```

**Guest/Llogged-in State Management:**

```dart
// In BLoC preferences_bloc.dart
enum PreferencesMode { guest, loggedIn }

class PreferencesBloc extends Bloc<PreferencesEvent, PreferencesState> {
  PreferencesBloc() : super(PreferencesInitial()) {
    on<LoadPreferences>(_onLoadPreferences);
    on<UpdatePreference>(_onUpdatePreference);
    on<ClearSearchHistory>(_onClearSearchHistory);
    on<SignInFromPreferences>(_onSignInFromPreferences);
  }
  
  Future<void> _onLoadPreferences(LoadPreferences event, Emitter emit) async {
    emit(PreferencesLoading());
    
    final isGuest = authBloc.state is AuthGuest;
    
    if (isGuest) {
      // Load guest preferences from local Hive
      await GuestPreferencesService.initializeGuestPreferences();
      final guestPrefs = await GuestPreferencesService.exportGuestPreferences();
      
      emit(PreferencesLoaded(
        mode: PreferencesMode.guest,
        preferences: guestPrefs,
        canAccessNotifications: false,
        canAccessAccountManagement: false,
      ));
    } else {
      // Load logged-in preferences from API + local cache
      try {
        final apiPrefs = await preferencesRepository.getPreferences();
        emit(PreferencesLoaded(
          mode: PreferencesMode.loggedIn,
          preferences: apiPrefs,
          canAccessNotifications: true,
          canAccessAccountManagement: true,
        ));
      } catch (e) {
        emit(PreferencesError('Failed to load preferences'));
      }
    }
  }
  
  Future<void> _onUpdatePreference(UpdatePreference event, Emitter emit) async {
    final currentState = state;
    if (currentState is! PreferencesLoaded) return;
    
    if (currentState.mode == PreferencesMode.guest) {
      // Update local guest preferences only
      await GuestPreferencesService.updateGuestPreference(event.key, event.value);
      
      final updatedPrefs = Map<String, dynamic>.from(currentState.preferences);
      updatedPrefs[event.key] = event.value;
      
      emit(currentState.copyWith(preferences: updatedPrefs));
    } else {
      // Update logged-in preferences (API + local)
      try {
        await preferencesRepository.updatePreference(event.key, event.value);
        
        final updatedPrefs = Map<String, dynamic>.from(currentState.preferences);
        updatedPrefs[event.key] = event.value;
        
        emit(currentState.copyWith(preferences: updatedPrefs));
      } catch (e) {
        emit(PreferencesError('Failed to update preference'));
      }
    }
  }
}
```

**UI State Handling:**

```dart
// In preferences_page.dart
Widget _buildNotificationSection() {
  return BlocBuilder<PreferencesBloc, PreferencesState>(
    builder: (context, state) {
      if (state is PreferencesLoaded && state.mode == PreferencesMode.guest) {
        // Guest locked state
        return Container(
          margin: EdgeInsets.all(16),
          padding: EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Theme.of(context).dividerColor),
          ),
          child: Column(
            children: [
              Icon(Icons.notifications_off, size: 32, color: Theme.of(context).disabledColor),
              SizedBox(height: 8),
              Text('Sign in to enable notifications', style: Theme.of(context).textTheme.titleMedium),
              SizedBox(height: 8),
              Text('Get alerts for flash deals and vendor updates', 
                   style: Theme.of(context).textTheme.bodySmall,
                   textAlign: TextAlign.center),
              SizedBox(height: 16),
              Row(
                children: [
                  Expanded(child: ElevatedButton(
                    onPressed: () => GoRouter.push('/login'),
                    child: Text('Sign In'),
                  )),
                  SizedBox(width: 12),
                  Expanded(child: OutlinedButton(
                    onPressed: () => GoRouter.push('/register'),
                    child: Text('Register'),
                  )),
                ],
              ),
            ],
          ),
        );
      }
      
      // Logged-in notification switches
      return Column(
        children: [
          SwitchListTile(
            title: Text('All Notifications'),
            subtitle: Text('Turn off all notifications'),
            value: state.preferences['allNotificationsOff'] ?? false,
            onChanged: (value) => context.read<PreferencesBloc>().add(UpdatePreference('allNotificationsOff', value)),
          ),
          SwitchListTile(
            title: Text('Nearby Deals'),
            subtitle: Text('Alerts for deals near you'),
            value: state.preferences['nearbyDeals'] ?? true,
            onChanged: (value) => context.read<PreferencesBloc>().add(UpdatePreference('nearbyDeals', value)),
          ),
          // ... other notification switches
        ],
      );
    },
  );
}
```

**Sign-in Flow with Preference Migration:**

```dart
// When guest signs in, migrate their preferences
Future<void> _onSignInFromPreferences(SignInFromPreferences event, Emitter emit) async {
  try {
    // Export guest preferences
    final guestPrefs = await GuestPreferencesService.exportGuestPreferences();
    
    // Sign in
    await authRepository.signIn(event.email, event.password);
    
    // Send guest preferences to server as initial preferences
    await preferencesRepository.setInitialPreferences(guestPrefs);
    
    // Clear local guest preferences
    await GuestPreferencesService.clearGuestPreferences();
    
    // Reload preferences as logged-in user
    add(LoadPreferences());
  } catch (e) {
    emit(PreferencesError('Failed to sign in'));
  }
}
```

All setting saves:
- **Guest**: immediate → Hive local storage only (no API calls)
- **Logged-in**: immediate → Hive update → PUT /preferences/ (debounced 1s for sliders)

---

## 14. PUSH NOTIFICATIONS

### 14.1 Firebase Cloud Messaging Setup

- `firebase_messaging` + `firebase_core`
- Android: `google-services.json` in `android/app/`
- iOS: `GoogleService-Info.plist` in `ios/Runner/` + APNs key configured in Firebase Console

### 14.2 Notification Types

| Type | Trigger (Backend) | Tap Action |
|---|---|---|
| Flash Deal Alert | Celery task when Platinum flash deal starts | GoRouter.push('/deals') |
| Nearby Deal | Scheduled Celery batch (city-level estimate) | GoRouter.push('/deals') |
| Vendor Update | Vendor Portal action → FCM | GoRouter.push('/vendor/:id') |

### 14.3 Permission Request Flow

```
On first Discovery load (or first Me tab visit):
  NotificationPermissionBloc checks status

  If 'undetermined' (iOS) / 'denied' (Android 13+):
    Show pre-permission dialog:
      Icon: 🔔 (brandOrange, 48px)
      Title: "Stay in the Loop on Deals"
      Body: "Get alerted when a flash deal starts near you."
      CTA: "Enable Notifications" → system dialog
      Secondary: "Not Now" → dismissed, can enable later in Preferences

After grant: retrieve FCM token → store in Hive + optionally POST to backend
```

### 14.4 Foreground Notification Handling

```dart
FirebaseMessaging.onMessage.listen((RemoteMessage message) {
  // App is open — show local notification (not system notification)
  flutterLocalNotifications.show(
    message.hashCode,
    message.notification?.title,
    message.notification?.body,
    notificationDetails,
    payload: message.data['route'],
  );
});
```

### 14.5 Notification Tap Routing

```dart
// Background tap (app running):
FirebaseMessaging.onMessageOpenedApp.listen((message) {
  final route = message.data['route'];
  if (route != null) router.push(route);
});

// Killed state tap (app launched from notification):
final initial = await FirebaseMessaging.instance.getInitialMessage();
if (initial != null) {
  // Store route in AppBloc, navigate after app fully initialized
}
```

### 14.6 Real-time Promotion Updates Strategy

> **[AUDIT FIX]** Flutter plan was missing real-time promotion updates strategy. Backend provides 60-second TTL caching, but Flutter needs active polling and WebSocket fallback for true real-time updates.

**Real-time Update Architecture:**

```dart
// In services/realtimePromotionService.dart
class RealtimePromotionService {
  static const Duration _pollingInterval = Duration(seconds: 30); // Between backend cache updates
  static const Duration _websocketTimeout = Duration(seconds: 10);
  
  Timer? _pollingTimer;
  WebSocketChannel? _websocketChannel;
  final StreamController<PromotionUpdate> _updateController = 
      StreamController<PromotionUpdate>.broadcast();
  
  Stream<PromotionUpdate> get promotionUpdates => _updateController.stream;
  
  Future<void> startRealtimeUpdates(double lat, double lng, double radius) async {
    // Stop any existing updates
    stopRealtimeUpdates();
    
    // Try WebSocket first (most efficient)
    _tryWebSocketUpdates(lat, lng, radius);
    
    // Fallback to polling if WebSocket fails
    _startPollingUpdates(lat, lng, radius);
  }
  
  void _tryWebSocketUpdates(double lat, double lng, double radius) async {
    try {
      final wsUrl = Uri.parse('${Environment.wsBaseUrl}/ws/promotions/'
          '?lat=$lat&lng=$lng&radius=$radius');
      
      _websocketChannel = WebSocketChannel.connect(wsUrl);
      
      await _websocketChannel!.ready.timeout(_websocketTimeout);
      
      _websocketChannel!.stream.listen(
        (data) {
          final update = PromotionUpdate.fromJson(jsonDecode(data));
          _updateController.add(update);
          _updateLocalCache(update);
        },
        onError: (error) {
          print('WebSocket error, falling back to polling: $error');
          _websocketChannel?.close();
          _websocketChannel = null;
        },
        onDone: () {
          print('WebSocket closed, falling back to polling');
          _websocketChannel = null;
        },
      );
      
    } catch (e) {
      print('WebSocket connection failed: $e');
      _websocketChannel = null;
    }
  }
  
  void _startPollingUpdates(double lat, double lng, double radius) {
    _pollingTimer = Timer.periodic(_pollingInterval, (timer) async {
      try {
        final response = await dio.get('/api/v1/user-portal/promotions/realtime/', 
          queryParameters: {'lat': lat, 'lng': lng, 'radius': radius});
        
        final updates = (response.data['updates'] as List)
            .map((json) => PromotionUpdate.fromJson(json))
            .toList();
        
        for (final update in updates) {
          _updateController.add(update);
          _updateLocalCache(update);
        }
        
      } catch (e) {
        print('Polling failed: $e');
        // Don't stop polling on individual failures
      }
    });
  }
  
  void _updateLocalCache(PromotionUpdate update) {
    // Update cached vendor data with new promotion info
    final vendorCache = Hive.box('vendor_cache');
    final vendorKey = 'vendor_${update.vendorId}';
    
    if (vendorCache.containsKey(vendorKey)) {
      final vendor = Vendor.fromJson(vendorCache.get(vendorKey));
      final updatedVendor = vendor.copyWith(
        activePromotion: update.promotion,
        promotionLastUpdated: DateTime.now().toIso8601String(),
      );
      vendorCache.put(vendorKey, updatedVendor.toJson());
    }
    
    // Update promotions cache
    final promotionsCache = Hive.box('promotions_cache');
    promotionsCache.put('promotion_${update.promotionId}', update.promotion.toJson());
  }
  
  void stopRealtimeUpdates() {
    _pollingTimer?.cancel();
    _pollingTimer = null;
    
    _websocketChannel?.close();
    _websocketChannel = null;
  }
}

// Promotion update data model
class PromotionUpdate {
  final String promotionId;
  final String vendorId;
  final Promotion promotion;
  final String updateType; // 'created', 'updated', 'expired', 'cancelled'
  final DateTime timestamp;
  
  PromotionUpdate({
    required this.promotionId,
    required this.vendorId,
    required this.promotion,
    required this.updateType,
    required this.timestamp,
  });
  
  factory PromotionUpdate.fromJson(Map<String, dynamic> json) => PromotionUpdate(
    promotionId: json['promotion_id'],
    vendorId: json['vendor_id'],
    promotion: Promotion.fromJson(json['promotion']),
    updateType: json['update_type'],
    timestamp: DateTime.parse(json['timestamp']),
  );
}
```

**Integration with Discovery BLoC:**

```dart
// In discovery_bloc.dart
class DiscoveryBloc extends Bloc<DiscoveryEvent, DiscoveryState> {
  final RealtimePromotionService _realtimeService;
  StreamSubscription? _promotionSubscription;
  
  DiscoveryBloc(this._realtimeService) : super(DiscoveryInitial()) {
    on<StartRealtimePromotionUpdates>(_onStartRealtimeUpdates);
    on<StopRealtimePromotionUpdates>(_onStopRealtimeUpdates);
    on<PromotionUpdateReceived>(_onPromotionUpdateReceived);
  }
  
  Future<void> _onStartRealtimeUpdates(
    StartRealtimePromotionUpdates event, 
    Emitter emit
  ) async {
    if (state is DiscoveryLoaded) {
      final currentState = state as DiscoveryLoaded;
      
      // Start real-time updates
      await _realtimeService.startRealtimeUpdates(
        currentState.userLat,
        currentState.userLng,
        currentState.searchRadius,
      );
      
      // Listen for updates
      _promotionSubscription = _realtimeService.promotionUpdates.listen(
        (update) => add(PromotionUpdateReceived(update)),
      );
    }
  }
  
  Future<void> _onPromotionUpdateReceived(
    PromotionUpdateReceived event, 
    Emitter emit
  ) async {
    if (state is DiscoveryLoaded) {
      final currentState = state as DiscoveryLoaded;
      final update = event.update;
      
      // Update vendors list with new promotion info
      final updatedVendors = currentState.vendors.map((vendor) {
        if (vendor.id == update.vendorId) {
          return vendor.copyWith(
            activePromotion: update.promotion,
            promotionLastUpdated: update.timestamp.toIso8601String(),
          );
        }
        return vendor;
      }).toList();
      
      // Re-sort vendors based on new ranking (promotions affect ranking)
      final sortedVendors = _sortVendorsByRanking(updatedVendors);
      
      emit(currentState.copyWith(
        vendors: sortedVendors,
        lastPromotionUpdate: update.timestamp,
      ));
      
      // Show subtle notification for important updates
      if (update.updateType == 'created' && update.promotion.isFlashDeal) {
        _showFlashDealNotification(update);
      }
    }
  }
  
  void _showFlashDealNotification(PromotionUpdate update) {
    // Show in-app notification for new flash deals
    final notification = InAppNotification(
      title: '🔥 Flash Deal Started!',
      message: '${update.promotion.title} at ${update.promotion.vendorName}',
      type: NotificationType.flashDeal,
      action: () => GoRouter.push('/vendor/${update.vendorId}'),
    );
    
    // Add to UI state for display
    emit((state as DiscoveryLoaded).copyWith(
      pendingNotification: notification,
    ));
  }
}
```

**UI Real-time Updates:**

```dart
// In widgets/promotion_badge.dart
class PromotionBadge extends StatefulWidget {
  final Promotion? promotion;
  final String vendorId;
  
  const PromotionBadge({super.key, this.promotion, required this.vendorId});
  
  @override
  State<PromotionBadge> createState() => _PromotionBadgeState();
}

class _PromotionBadgeState extends State<PromotionBadge> 
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _slideController;
  StreamSubscription? _promotionSubscription;
  
  @override
  void initState() {
    super.initState();
    
    _pulseController = AnimationController(
      duration: Duration(seconds: 2),
      vsync: this,
    );
    
    _slideController = AnimationController(
      duration: Duration(milliseconds: 300),
      vsync: this,
    );
    
    // Listen for real-time promotion updates
    _promotionSubscription = context.read<RealtimePromotionService>()
        .promotionUpdates
        .where((update) => update.vendorId == widget.vendorId)
        .listen((update) {
      if (mounted) {
        setState(() {
          // Widget will rebuild with new promotion data
        });
        
        // Animate important updates
        if (update.updateType == 'created' && update.promotion?.isFlashDeal == true) {
          _pulseController.forward().then((_) => _pulseController.reverse());
        }
      }
    });
    
    // Start pulse animation for existing flash deals
    if (widget.promotion?.isFlashDeal == true) {
      _pulseController.repeat(reverse: true);
    }
  }
  
  @override
  void dispose() {
    _pulseController.dispose();
    _slideController.dispose();
    _promotionSubscription?.cancel();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    if (widget.promotion == null) return SizedBox.shrink();
    
    final promotion = widget.promotion!;
    
    return AnimatedBuilder(
      animation: Listenable.merge([_pulseController, _slideController]),
      builder: (context, child) {
        return Transform.scale(
          scale: 1.0 + (_pulseController.value * 0.1),
          child: SlideTransition(
            position: Tween<Offset>(
              begin: Offset(0, -0.5),
              end: Offset.zero,
            ).animate(CurvedAnimation(
              parent: _slideController,
              curve: Curves.elasticOut,
            )),
            child: Container(
              padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: promotion.isFlashDeal 
                    ? AppColors.brandOrange 
                    : AppColors.brandTeal,
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(
                    color: promotion.isFlashDeal 
                        ? AppColors.brandOrange.withOpacity(0.3)
                        : AppColors.brandTeal.withOpacity(0.3),
                    blurRadius: 8 * _pulseController.value,
                    spreadRadius: 2 * _pulseController.value,
                  ),
                ],
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (promotion.isFlashDeal) ...[
                    Icon(Icons.local_fire_department, 
                         color: Colors.white, size: 12),
                    SizedBox(width: 4),
                  ],
                  Text(
                    promotion.displayLabel,
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
```

**Background Real-time Updates:**

```dart
// In services/backgroundPromotionService.dart
class BackgroundPromotionService {
  static final BackgroundPromotionService _instance = BackgroundPromotionService._internal();
  factory BackgroundPromotionService() => _instance;
  BackgroundPromotionService._internal();
  
  // Background isolate for real-time updates when app is backgrounded
  static const String _isolateName = 'promotion_updates_isolate';
  
  Future<void> startBackgroundUpdates() async {
    if (await _isolateRunning()) return;
    
    ReceivePort receivePort = ReceivePort();
    
    await Isolate.spawn(_backgroundUpdateWorker, receivePort.sendPort);
    
    receivePort.listen((message) {
      if (message is Map && message['type'] == 'promotion_update') {
        // Handle background promotion update
        _handleBackgroundUpdate(message['data']);
      }
    });
  }
  
  static void _backgroundUpdateWorker(SendPort sendPort) {
    // Background worker that maintains WebSocket connection
    // and processes promotion updates even when app is backgrounded
    
    Timer.periodic(Duration(seconds: 30), (timer) async {
      try {
        // Check for promotion updates
        final updates = await _checkPromotionUpdates();
        
        if (updates.isNotEmpty) {
          sendPort.send({
            'type': 'promotion_update',
            'data': updates,
          });
        }
      } catch (e) {
        // Continue trying even on failures
      }
    });
  }
  
  void _handleBackgroundUpdate(Map<String, dynamic> updateData) {
    // Show notification for important updates
    for (final update in updateData['updates']) {
      if (update['is_flash_deal'] == true) {
        _showFlashDealNotification(update);
      }
    }
  }
  
  Future<void> _showFlashDealNotification(Map<String, dynamic> promotion) async {
    final flutterLocalNotificationsPlugin = FlutterLocalNotificationsPlugin();
    
    const androidDetails = AndroidNotificationDetails(
      'flash_deals_channel',
      'Flash Deals',
      channelDescription: 'Notifications for flash deals',
      importance: Importance.high,
      priority: Priority.high,
      color: AppColors.brandOrange,
    );
    
    const iosDetails = IOSNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );
    
    const notificationDetails = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );
    
    await flutterLocalNotificationsPlugin.show(
      DateTime.now().millisecondsSinceEpoch.remainder(100000),
      '🔥 Flash Deal Started!',
      promotion['title'],
      notificationDetails,
      payload: 'vendor_${promotion['vendor_id']}',
    );
  }
}
```

### 14.7 Notification Preferences Sync

- Local: `PreferencesBloc` → Hive immediate
- Remote: `PUT /preferences/` with notification settings
- If `all_off = true`: suppress local notification display (don't unsubscribe FCM — re-enable at any time)

---

## 15. OFFLINE MODE

### 15.1 What IS Cached (Hive)

| Data | Hive Key Pattern | TTL | Purpose |
|---|---|---|---|
| Nearby vendors | `discovery_${geohash}` | 24h | Show stale list offline |
| Vendor profiles (last 5) | `vendor_${id}` | 48h | Recently viewed vendors |
| User preferences | `settings` | No expiry | Always available |
| Tag list | `tags_cache` | 72h | Tag browser works offline |
| Search history | `search_history` | 30 days | Suggestions offline |

### 15.2 What is NOT Cached

- Live AR marker positions (always real-time)
- Active promotions (time-sensitive — no stale countdowns shown)
- Deals list (must be live for flash deals)
- Reel videos (too large)

### 15.3 Offline UX

```
ConnectivityBloc (connectivity_plus stream):

On disconnect:
  OfflineBannerWidget slides in (SlideTransition from top)
  Discovery: shows cached vendors with "Last updated [X] min ago" tag
  Promotions: hidden (no stale countdown data)
  AR: Simulated mode only, no API markers

On reconnect:
  OfflineBannerWidget slides out
  DiscoveryBloc.add(RefreshVendors()) automatic
  Toast: "Back online — refreshing results" (2s)
```

### 15.4 First-Launch Offline (Empty Cache)

> **[AUDIT FIX — HIGH 3.8]** First-ever app launch with no internet AND empty Hive cache requires its own handling, distinct from "was online, now offline."

```dart
// In DiscoveryBloc._onLoadNearbyVendors:
if (!await networkInfo.isConnected) {
  final cached = await localDataSource.getCached(params.geohash);
  if (cached == null || cached.isEmpty) {
    // True first-load offline — distinct empty state
    emit(DiscoveryFirstLoadOffline());
    return;
  }
}
```

`DiscoveryFirstLoadOffline` state renders:
```
Full-screen centered column:
  AirAds logo (80px, Opacity 0.15) + flutter_animate .fadeIn
  Text: "No internet connection" (heading3, white)
  Text: "Connect to the internet to discover nearby vendors." (bodyMedium, secondary)
  ElevatedButton "Try Again" (gradient, 52px) → DiscoveryBloc.add(LoadNearbyVendors())

NO skeleton loaders — they imply data is coming.
NO cached count chip — there is no cache to show.
```

### 15.4 Cache-First Repository Pattern

```dart
Future<Either<Failure, List<Vendor>>> getNearbyVendors(params) async {
  if (await networkInfo.isConnected) {
    try {
      final fresh = await remoteDataSource.getNearby(params);
      await localDataSource.cacheVendors(params.geohash, fresh);
      return Right(fresh);
    } catch (e) { /* fall through to cache */ }
  }
  final cached = await localDataSource.getCached(params.geohash);
  if (cached != null) return Right(cached);
  return Left(NetworkFailure());
}
```

---

## 16. PERFORMANCE CONSIDERATIONS

### 16.0 Crash Reporting (Firebase Crashlytics)

> **[AUDIT FIX — HIGH 3.2]** Without crash reporting, production crashes are invisible.

```dart
// In main.dart (after Firebase.initializeApp()):
await FirebaseCrashlytics.instance.setCrashlyticsCollectionEnabled(!kDebugMode);

// Capture Flutter framework errors:
FlutterError.onError = FirebaseCrashlytics.instance.recordFlutterError;

// Capture Dart async errors:
PlatformDispatcher.instance.onError = (error, stack) {
  FirebaseCrashlytics.instance.recordError(error, stack, fatal: true);
  return true;
};

// BLoC-level error reporting:
// In BlocObserver.onError:
FirebaseCrashlytics.instance.recordError(error, stackTrace, reason: 'BLoC error: \$bloc');
```

User identification for crash context (non-PII):
```dart
// Set user identifier (guest token or user UUID — NOT email/name)
FirebaseCrashlytics.instance.setUserIdentifier(authBloc.currentUserId ?? guestToken);
```

Add to `pubspec.yaml`: `firebase_crashlytics: ^3.4.0`

### 16.1 App Startup Target: < 2 Seconds

- Hive init: parallel boxes opened in `main()` before `runApp()`
- Firebase + Crashlytics: initialized synchronously before `runApp()` (required for crash capture)
- Fonts: preloaded via `pubspec.yaml` — no font flash
- Splash: native splash (Android `launch_background`, iOS `LaunchScreen.storyboard`)
- DiscoveryBloc: location request starts immediately on discovery page build

### 16.2 60 FPS Animation Rules

- All animations: `Transform` widget — GPU-composited, never `AnimatedPositioned` on hot paths
- AR marker updates: `CustomPainter` with `shouldRepaint: false` when data unchanged
- Video decode: `video_player` handles on separate isolate
- `ListView.builder` everywhere — never `Column(children: [...])`
- `const` constructors aggressively — prevents rebuild
- BLoC: `buildWhen` on all `BlocBuilder` — narrow rebuild scope

### 16.3 Memory Management

- Video player: `dispose()` on reel page exit (PageView off-screen page disposal)
- `CachedNetworkImage`: max 200 images memory cache, 500MB disk cache
- AR camera stream: `dispose()` in State.dispose()
- Location stream: `StreamSubscription.cancel()` in LocationBloc.close()
- Hive vendor profiles: max 5 stored (FIFO eviction)

### 16.4 App Size Targets

- Android AAB: < 30MB
- iOS IPA: < 35MB
- Achieved by: tree-shaking Material icons, no bundled map tiles, Lottie files < 100KB each, no large bundled images

### 16.5 Battery Efficiency

- Location: `distanceFilter: 30m` in discovery mode
- AR: `DeviceOrientationEvent` is hardware-sourced — negligible overhead
- FCM: platform-native push (no background polling)
- Hive reads: synchronous, zero async overhead for settings

### 16.6 AR Low-End Device Performance

> **[AUDIT FIX — HIGH 3.14]** Glassmorphism + 15 AR markers simultaneously will cause frame drops on low-end Android devices (4GB RAM target market).

```dart
// In ARBloc — device tier detection on init:
Future<DeviceTier> _detectDeviceTier() async {
  final info = await DeviceInfoPlugin().androidInfo; // or iosInfo
  final totalRam = info.totalMemory ?? 2000; // MB (Android 10+)
  if (totalRam >= 6000) return DeviceTier.high;
  if (totalRam >= 3000) return DeviceTier.mid;
  return DeviceTier.low;
}
```

Progressive quality by tier:

| Tier | Max Markers | BackdropFilter | flutter_animate | Float Animation |
|---|---|---|---|---|
| HIGH | 15 | `sigmaX: 12` | full | enabled |
| MID | 10 | `sigmaX: 6` | opacity only | enabled |
| LOW | 6 | disabled (solid Color(0xCC141414)) | none (Container) | disabled |

```dart
// ARMarkerWidget — conditional backdrop filter:
if (arBloc.deviceTier != DeviceTier.low)
  BackdropFilter(
    filter: ImageFilter.blur(
      sigmaX: arBloc.deviceTier == DeviceTier.high ? 12 : 6,
      sigmaY: arBloc.deviceTier == DeviceTier.high ? 12 : 6,
    ),
    child: markerContent,
  )
else
  markerContent // solid background only
```

Emit `DeviceTierDetected` in `ARBloc.ARInitializing` state — store in `ARState` for all widgets to read.

### 16.7 City / Area Picker (GPS Denied)

> **[AUDIT FIX — HIGH 1.8]** When GPS is denied, the LocationContext area name chip must open a city selector — not be a dead UI element.

```dart
// LocationBloc: emits LocationDenied with cityPickerRequired: true
// DiscoveryPage reacts:
BlocListener<LocationBloc, LocationState>(
  listener: (ctx, state) {
    if (state is LocationDenied || state is LocationTimeout) {
      showModalBottomSheet(
        context: ctx,
        isScrollControlled: true,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        builder: (_) => CityPickerSheet(),
      );
    }
  },
);
```

`CityPickerSheet` widget:
```
DraggableScrollableSheet (initialChildSize: 0.6, maxChildSize: 0.9):
  Drag handle (32×4px, AppColors.darkBorder, centered)
  Title: "Choose your area" (heading3, padding: 20)
  
  City row (SingleChildScrollView horizontal):
    FilterChip per city: "Lahore" | "Karachi" | "Islamabad"
    Active: AppColors.brandOrange bg
    Data from: GET /discovery/cities/ (CityBloc or FutureProvider)
  
  Area grid (GridView.count crossAxisCount:3, separated by 8px):
    Each: InkWell card (rounded 12, darkBgElevated)
      Column: area name (labelMedium bold) + vendor count (bodySmall secondary)
    Active: orange border (1.5px) + subtle orange bg tint
  
  Confirm button: "Explore [AreaName] →" (ElevatedButton gradient, 52px, fullWidth)
    OnTap:
      LocationBloc.add(SetManualLocation(lat: area.lat, lng: area.lng, name: area.name))
      Navigator.pop(context)
  
  Footer: "Enable GPS for precise results" (bodySmall tertiary, centered)
```

### 16.8 GDPR Consent Banner

> **[AUDIT FIX — HIGH 3.10]** First-use data consent required before location collection.

```dart
// In main.dart or DiscoveryPage init:
final consentGiven = Hive.box('settings').get('consent_v1', defaultValue: false);
if (!consentGiven) {
  // Show ConsentBottomSheet before any location or analytics call
  WidgetsBinding.instance.addPostFrameCallback((_) {
    showModalBottomSheet(
      context: navigatorKey.currentContext!,
      isDismissible: false,        // cannot tap outside to dismiss
      enableDrag: false,
      builder: (_) => ConsentBottomSheet(),
    );
  });
}
```

`ConsentBottomSheet` widget:
```
Container (AppColors.darkBgElevated, borderRadius top 24, padding 24):
  Text: "AirAds uses your location to show nearby vendors." (bodyMedium)
  Text: "We collect anonymous usage patterns to improve discovery." (bodySmall secondary)
  InkWell: "Read Privacy Policy" → launchUrl
  
  SizedBox(height: 20)
  
  Two buttons (Row, mainAxisAlignment: spaceBetween):
    OutlinedButton "Essential Only" (full flex):
      Records LOCATION consent, skips ANALYTICS consent
    ElevatedButton "Accept All" (gradient, full flex):
      Records all consent types
  
  On either:
    Hive.box('settings').put('consent_v1', true)
    POST ApiEndpoints.consentRecord for each consent type
    Navigator.pop()
```

---

## 17. iOS vs ANDROID DIFFERENCES

### 17.1 Permissions

| Permission | iOS (Info.plist) | Android (AndroidManifest) |
|---|---|---|
| Location | `NSLocationWhenInUseUsageDescription` | `ACCESS_FINE_LOCATION` |
| Camera | `NSCameraUsageDescription` | `CAMERA` |
| Microphone | `NSMicrophoneUsageDescription` | `RECORD_AUDIO` |
| Notifications | Runtime request (iOS 10+) | Auto < Android 13, runtime on 13+ |

All via `permission_handler` — unified API.

### 17.2 AR Implementation

| Feature | iOS | Android |
|---|---|---|
| AR SDK | ARKit (ar_flutter_plugin) | ARCore (ar_flutter_plugin) |
| Minimum OS | iOS 14.0 | Android 7.0 + ARCore support |
| Availability | Built-in on A9+ devices | Requires Google Play Services |

Both handled by `ar_flutter_plugin` — platform differences within plugin.

### 17.3 UI Differences

| Component | iOS | Android |
|---|---|---|
| Slider | `CupertinoSlider` | Material `Slider` |
| Switch | `CupertinoSwitch` | Material `Switch` |
| Alert | `CupertinoAlertDialog` | Material `AlertDialog` |
| Back gesture | Swipe-from-left (system) | Back button / gesture |
| Bottom padding | + home indicator height | + navigation bar height |

Implementation: `Platform.isIOS` check in preference-related widgets.

### 17.4 Deep Links

| Platform | Mechanism | Example URL |
|---|---|---|
| iOS | Universal Links (Associated Domains) | `https://app.airad.pk/vendor/uuid` |
| Android | App Links (Intent Filter) | Same URL |
| Fallback | HTTPS opens web User Portal | Same URL in browser |

`app_links` package handles both. Backend serves:
- `/.well-known/apple-app-site-association` (iOS)
- `/.well-known/assetlinks.json` (Android)

### 17.5 TTS Restriction

iOS: TTS only fires after user interaction (mic tap qualifies — satisfies restriction).
Android: No restriction.
Mitigation: TTS only triggered from VoiceBloc (which starts on mic tap).

---

## 18. APP STORE DEPLOYMENT REQUIREMENTS

### 18.1 Apple App Store

| Requirement | Details |
|---|---|
| App ID | `pk.airad.customerapp` registered in Apple Developer Portal |
| Signing | App Store Distribution provisioning profile |
| Privacy manifest | `PrivacyInfo.xcprivacy` (iOS 17+ policy, required) |
| Privacy labels | Location (when in use), Camera, Microphone — all disclosed |
| Age rating | 4+ (no objectionable content) |
| Screenshots | 6 per device size: iPhone 6.7" + 6.5" + iPad 12.9" |
| Categories | Primary: "Food & Drink" / Secondary: "Lifestyle" |

Screenshot content (minimum 6): AR view, Map view, Vendor Profile, Deals, Voice Search, Navigation arrival.

App description key phrases:
- "No account needed to start discovering"
- "AR camera shows nearby vendors in your surroundings"
- "Real-time deals from shops near you"

### 18.2 Google Play Store

| Requirement | Details |
|---|---|
| Package | `pk.airad.customerapp` |
| Keystore | Release keystore, stored securely outside repo |
| Target API | `targetSdk 34` (required for Play Store 2024+) |
| Privacy policy | Required URL (location/camera usage) |
| Data safety form | Location, Camera, Microphone — all disclosed |
| Content rating | ESRB: Everyone |
| Build format | AAB (not APK) |
| Feature graphic | 1024×500px (brand orange gradient + logo) |

### 18.3 Build Commands

```bash
# Android AAB (Play Store):
flutter build appbundle --release \
  --dart-define=API_BASE_URL=https://api.airad.pk/api/v1/user-portal \
  --dart-define=MAPBOX_TOKEN=${MAPBOX_TOKEN}

# iOS IPA (App Store):
flutter build ipa --release \
  --dart-define=API_BASE_URL=https://api.airad.pk/api/v1/user-portal \
  --dart-define=MAPBOX_TOKEN=${MAPBOX_TOKEN}
```

No hardcoded URLs or tokens in source code — all via `--dart-define`.

### 18.4 CI/CD (`.github/workflows/deploy-flutter.yml`)

Trigger: push to `main` (production) or `develop` (TestFlight / Internal track).
Steps: setup Flutter → `flutter test` → `flutter build appbundle` → upload to Play Store → `flutter build ipa` → upload to TestFlight.
Secrets: `MAPBOX_TOKEN`, `APPLE_CERTIFICATE`, `PLAY_STORE_KEY_JSON` — all GitHub Secrets.

---

## 19. BRANDING CONSISTENCY

### 19.1 Web Token → Flutter Constant Mapping

| Web CSS Token | Flutter Constant |
|---|---|
| `--brand-orange: #FF8C00` | `AppColors.brandOrange = Color(0xFFFF8C00)` |
| `--brand-crimson: #C41E3A` | `AppColors.brandCrimson = Color(0xFFC41E3A)` |
| `--brand-teal: #00BCD4` | `AppColors.brandTeal = Color(0xFF00BCD4)` |
| `--brand-black: #000000` | `AppColors.brandBlack = Color(0xFF000000)` |
| `--font-family: 'DM Sans'` | `fontFamily: 'DMSans'` (bundled assets) |
| `--space-2: 8px` | `AppSpacing.sm = 8.0` |
| `--radius-full: 9999px` | `BorderRadius.circular(999)` |
| `--transition-spring: 400ms` | `AppDurations.spring = Duration(milliseconds: 400)` |
| `--glass-bg: rgba(20,20,20,0.80)` | `Color(0xCC141414)` |
| `--glass-blur` | `BackdropFilter(filter: ImageFilter.blur(sigmaX:12, sigmaY:12))` |

### 19.2 Component Visual Parity

| Web Component | Flutter Widget |
|---|---|
| `VendorCard` | `VendorCardWidget` |
| `PromotionBadge` | `PromotionBadgeWidget` |
| `CountdownTimer` | `CountdownTimerWidget` |
| `TierBadge` | `TierBadgeWidget` |
| `DistanceBadge` | `DistanceBadgeWidget` |
| `SkeletonLoader` | `SkeletonLoaderWidget` (Shimmer effect) |
| `VoiceWave` | Lottie `voice_wave.json` |
| `ARMarker` | `ARMarkerWidget` |
| `TagChip` | `TagChipWidget` |
| `OfflineBanner` | `OfflineBannerWidget` |

### 19.3 AirAds Logo

Single source: `assets/images/airad_logo.png` — same logo as web portal.

| Context | Size | Treatment |
|---|---|---|
| Splash | 80px | Centered, animate in |
| App bar (compact) | 32px | Leading widget |
| Onboarding | 64px | Centered |
| Empty states | 60px | `Opacity(opacity: 0.12)` — watermark |

### 19.4 Dark Theme as Default

```dart
MaterialApp(
  themeMode: _getStoredTheme(),  // ThemeMode.dark if no preference stored
  theme: AppTheme.light,
  darkTheme: AppTheme.dark,
)
```

---

## 20. BUILD SEQUENCE & SESSIONS

| Session | Content | Est. Time |
|---|---|---|
| UP-FL-S1 | Flutter create, pubspec.yaml (all dependencies), analysis_options.yaml, DI registration (get_it + injectable), AppColors, AppTextStyles, AppSpacing, AppTheme (dark + light), GoRouter skeleton with all routes | 3h |
| UP-FL-S2 | All shared widgets: VendorCard, PromotionBadge, CountdownTimer, TierBadge, DistanceBadge, SkeletonLoader, TagChip, OfflineBanner, VoiceWave (Lottie) | 3h |
| UP-FL-S3 | Core layer: Dio + interceptors (AuthInterceptor, RetryInterceptor), all ApiEndpoints, Hive setup (all boxes), SecureStorage service, Failure/Exception hierarchy, NetworkInfo, PermissionService | 2h |
| UP-FL-S4 | Auth feature: AuthBloc, LoginPage, RegisterPage, LandingPage (3-slide onboarding), guest token flow, returnTo navigation | 3h |
| UP-FL-S5 | App shell: AppShell + BottomNav, DiscoveryPage shell (custom app bar, IndexedStack, LocationBloc integration), LocationBloc, ConnectivityBloc | 2h |
| UP-FL-S6 | AR feature: ARBloc, mode detection (Real vs Simulated), ARKitView/ARCoreView integration, ARMarkerWidget (collapsed + expanded), ARClusterWidget, CompassWidget, WalkingSafetyBanner, RadiusSliderWidget | 4h |
| UP-FL-S7 | Voice feature: VoiceBloc, SpeechToText integration, VoiceSearchOverlay (Lottie wave, transcript, suggestions), NlpUtils, flutter_tts, VoiceBotBottomSheet | 3h |
| UP-FL-S8 | Map feature: Mapbox setup, vendor pin layer (tier colors + promotion ring), filter chips overlay, DraggableScrollableSheet on tap, camera fly-to | 3h |
| UP-FL-S9 | List view: VendorCardWidget, SliverList, infinite scroll, sort control, pull-to-refresh, empty state | 2h |
| UP-FL-S10 | Tag browser: TagBrowserBloc, all 4 sections (hot/intent/category/distance), multi-select, floating FAB with count preview | 2h |
| UP-FL-S11 | Vendor profile: full CustomScrollView (SliverAppBar parallax, all 6 sections, voice bot sheet, reel thumbnails, FAB, share_plus) | 3h |
| UP-FL-S12 | Deals page: DealCardWidget with urgency system (3 levels), FlashDealOverlay (OverlayEntry), RefreshIndicator, empty state | 2h |
| UP-FL-S13 | Reels page: PageView vertical scroll, VideoPlayer + chewie, all overlay elements, view tracking, swipe-to-skip | 3h |
| UP-FL-S14 | Navigation feature: NavigationBloc, Mapbox route line, NavigationHeader, InstructionStrip, VendorMiniCard, ArrivalOverlay (Lottie checkmark), GoRouter deep links | 3h |
| UP-FL-S15 | Preferences/Me: all settings sections, PreferencesBloc, GDPR flows (delete/export), theme switching (ThemeMode live), notification prefs, guest vs logged-in differences | 2h |
| UP-FL-S16 | Push notifications: FCM setup (Android + iOS), foreground handler, background tap routing, killed-state routing, NotificationPermissionBloc, flutter_local_notifications | 2h |
| UP-FL-S17 | Offline mode: ConnectivityBloc, cache-first repositories, OfflineBanner integration, stale data labeling, auto-refresh on reconnect | 2h |
| UP-FL-S18 | QA + polish: all error states, all empty states, all loading states, `flutter analyze` = 0 warnings, `flutter test` passing, iOS/Android visual verification, `flutter build appbundle` success, `flutter build ipa` success | 3h |

**Total: 18 sessions, ~47-53 hours**

---

## 21. QUALITY GATE CHECKLIST

### Architecture
- [ ] Zero business logic in any widget file
- [ ] All BLoC events and states use Freezed (immutable, copyWith)
- [ ] All classes registered in get_it — no `new ClassName()` in widget files
- [ ] All API calls return `Either<Failure, T>` — never throw from repository layer

### Design System
- [ ] Zero hardcoded `Color(0xFF...)` values outside `app_colors.dart`
- [ ] DM Sans applied via `ThemeData.fontFamily` — not per-widget override
- [ ] Dark theme launches by default (verified on fresh install/emulator reset)
- [ ] Light theme: all components visually correct (switch in preferences, verify all screens)
- [ ] All shared widgets match web counterparts visually

### AR Experience
- [ ] Mode A (real AR): camera feed visible, markers positioned by compass bearing
- [ ] Mode B (simulated): premium gradient background, floating markers, no "error" shown
- [ ] Max 15 markers enforced client-side before render
- [ ] Clustering: groups ≥ 3 vendors within 8° bearing separation
- [ ] Walking safety: triggers on motion > 1.5 m/s², auto-dismisses 3s
- [ ] Compass: smooth rotation, no jitter, static if unavailable
- [ ] AR view: 30 FPS minimum on mid-range device (Pixel 5 / iPhone 12 equivalent)

### Voice
- [ ] Mic denied: graceful fallback to text input (no crash, no blank screen)
- [ ] Real-time transcript: words appear incrementally while speaking
- [ ] NLP extracts: category, price intent, time intent, action — verified with 10+ test phrases
- [ ] Vendor voice bot: only accessible on Gold+ vendors (403 handled gracefully for Silver)
- [ ] TTS plays response audio + mute toggle persisted across sessions

### Location & Map
- [ ] Pre-permission dialog shown before system dialog on first launch
- [ ] Location denied: fallback mode (no crash, city-level results, info chip shown)
- [ ] Map pins: correct tier colors for all 4 tiers
- [ ] Promotion pins: pulsing animation visible
- [ ] Pin tap: DraggableScrollableSheet opens, action buttons navigate correctly
- [ ] Camera flies to user location on permission grant (1 second animation)

### All Screens
- [ ] Splash → Landing/Discover navigation works (onboarding_complete flag respected)
- [ ] Auth: login, register, guest flow — all end-to-end paths work
- [ ] Discovery view switcher: AR ↔ Map ↔ List instant, no state loss, AR session alive
- [ ] Vendor profile: all 6 sections load, FAB hides on Location section scroll
- [ ] Deals: urgency color transitions correct at 2h and 1h thresholds
- [ ] Reels: video plays on enter, pauses on exit, view tracking fires on exit
- [ ] Navigation: route line drawn, arrival detected at 30m, Lottie animation plays
- [ ] Preferences: all settings save, theme change immediate, GDPR flows complete

### Notifications
- [ ] Pre-permission dialog shown before system dialog
- [ ] Foreground notification: local notification shown (not silent)
- [ ] Background tap: navigates to correct route
- [ ] Killed state tap: waits for init, then navigates
- [ ] "All off" preference: local notification display suppressed

### Technical Quality
- [ ] `flutter analyze` = 0 errors, 0 warnings
- [ ] `flutter test` all passing (unit: BLoC + usecases, widget: key components)
- [ ] `flutter build appbundle --release` = success
- [ ] `flutter build ipa --release` = success
- [ ] Zero hardcoded API URLs or tokens in source code
- [ ] Zero `print()` statements in non-debug code
- [ ] All `dispose()` methods called: Controllers, BLoCs, StreamSubscriptions
- [ ] Semantics labels on all interactive elements (accessibility)
- [ ] App size: Android AAB < 30MB, iOS IPA < 35MB

### Audit Fixes Verification
- [ ] Token refresh: concurrent 401s deduplicated — only ONE refresh call made (verify with mock)
- [ ] GoRouter/Hive race: Hive boxes fully open BEFORE `runApp()` (verify via startup sequence test)
- [ ] Navigation: bottom sheet offers Google Maps / Apple Maps / in-app options before starting nav
- [ ] GPS accuracy: positions with `accuracy > 100m` discarded (verify with mock position)
- [ ] GPS smoothing: EMA applied — no marker teleporting (visual test on walk)
- [ ] Cold GPS: CityPickerSheet shown after 10s without fix
- [ ] City picker: area tap → LocationBloc.SetManualLocation → discovery refetches with area coords
- [ ] Promotions strip: uses `/discovery/promotions-strip/` API (NOT flash-alert)
- [ ] Reels tab: bottom nav transparent overlay, NOT hidden entirely
- [ ] AR LOW tier: 6 markers max, no BackdropFilter, solid background (verify on 2GB RAM device)
- [ ] Firebase Crashlytics: crashes reported in Firebase Console (verify with test crash in debug)
- [ ] Consent banner: shown on first launch, cannot dismiss without choosing
- [ ] Consent data: POST to `/auth/consent/` on first GPS grant + registration
- [ ] HTTP 429: `RateLimitFailure` shown as SnackBar countdown (not spinner forever)
- [ ] Offline first-load: `DiscoveryFirstLoadOffline` state shown (no skeleton loaders)
- [ ] Deep links: vendor page opens from URL `airad.pk/vendor/<id>` (test on physical device)

---

*USER PORTAL FLUTTER PLAN — COMPLETE (Part 1 + Part 2)*
*Version: 1.0 | February 2026 | Source of Truth: AirAds_User_Portal_Super_Master_Prompt.md UP-0 through UP-13 + 03_AirAd_End_User_Functional_Document.md*
