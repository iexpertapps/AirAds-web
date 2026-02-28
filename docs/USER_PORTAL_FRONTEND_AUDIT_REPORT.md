# AirAd User Portal — Frontend Audit Report

**Date:** 2026-02-28
**Auditor:** Cascade AI (Deep Multi-Source Audit)
**Scope:** Full frontend implementation audit against Master Prompt, Backend Plans, and Frontend Plans
**Location:** `airaad/user-portal/`

---

## Audit Summary

| Category | Count | Critical | High | Medium | Low |
|---|---|---|---|---|---|
| **MISSING** | 26 | 5 | 12 | 7 | 2 |
| **OVERLOOKED** | 12 | 3 | 5 | 3 | 1 |
| **PARTIALLY IMPLEMENTED** | 8 | 2 | 4 | 2 | 0 |
| **WOW FACTOR COMPROMISED** | 7 | 2 | 3 | 2 | 0 |
| **TOTAL** | **53** | **12** | **24** | **14** | **3** |

---

## 1. MISSING — Not implemented at all

### M-01: Error Boundary Component
- **Location:** Entire app — no `ErrorBoundary` component exists
- **Source:** Frontend Plan Part 2, Critical Audit Fixes section
- **Problem:** No global error boundary wraps the app. Any unhandled React render error will crash the entire app with a white screen.
- **Expected:** A `<GlobalErrorBoundary>` wrapping the app in `main.tsx` with a branded fallback UI showing retry/home options.
- **Criticality:** 🔴 CRITICAL

### M-02: Active Promotions Strip on Discovery Page
- **Location:** `src/pages/discovery/DiscoveryPage.tsx`
- **Source:** Master Prompt UP-5, Frontend Plan Part 1
- **Problem:** The horizontal-scroll promotions strip at the top of the discovery page is completely missing. The API function `getPromotionsStrip()` exists in `src/api/discovery.ts` but is never called.
- **Expected:** A scrollable strip below the search bar showing active promotions with vendor name, headline, and countdown timer. Tapping navigates to vendor.
- **Criticality:** 🔴 CRITICAL

### M-03: Guest Mode Access to Preferences
- **Location:** `src/router.tsx` line 106-116
- **Source:** Frontend Plan Part 2, Master Prompt UP-12
- **Problem:** `/preferences` is behind `AuthOnlyRoute`, blocking ALL guest access. Plan explicitly states: "Guest Mode: Theme toggle, search radius, about — accessible without login."
- **Expected:** Preferences page accessible to both guest and logged-in users. Guest sees theme/radius/about only. Logged-in sees full settings + privacy + account.
- **Criticality:** 🔴 CRITICAL

### M-04: Flash Deal Toast Notifications
- **Location:** Not implemented anywhere
- **Source:** Frontend Plan Part 2, Deals Tab section
- **Problem:** No toast notifications for flash deals appearing while user is browsing. `getFlashDeals()` API exists but is never called.
- **Expected:** Periodic polling or WebSocket for flash deals. Toast notification with deal info, countdown, and tap-to-navigate.
- **Criticality:** 🟠 HIGH

### M-05: GDPR Consent Banner
- **Location:** Not implemented anywhere
- **Source:** Frontend Plan Part 2, Offline/GDPR section
- **Problem:** No consent banner for first-time visitors. Required for data collection compliance.
- **Expected:** A dismissible banner at the bottom of the page on first visit, with accept/decline options, persisted in localStorage.
- **Criticality:** 🟠 HIGH

### M-06: Vendor Voice Bot Section on Profile
- **Location:** `src/pages/vendor/VendorProfilePage.tsx`
- **Source:** Master Prompt UP-8, Frontend Plan Part 2
- **Problem:** Voice bot section completely missing from vendor profile. API `getVendorVoiceBot()` exists in `src/api/vendor.ts` but is never used.
- **Expected:** A "Ask About This Vendor" section with a chat-like UI where users type or speak questions and get AI responses about the vendor (menu, hours, deals).
- **Criticality:** 🟠 HIGH

### M-07: AR Compass and Distance Filter
- **Location:** `src/pages/discovery/DiscoveryPage.tsx`, AR view section
- **Source:** Master Prompt UP-5
- **Problem:** No compass indicator and no distance filter slider in AR view.
- **Expected:** A compass widget showing cardinal directions and a slider to filter markers by distance (50m–2km).
- **Criticality:** 🟠 HIGH

### M-08: AR Walking Safety Overlay
- **Location:** `src/pages/discovery/DiscoveryPage.tsx`, AR view section
- **Source:** Master Prompt UP-5
- **Problem:** No walking safety overlay warning users to watch their surroundings while using AR.
- **Expected:** A semi-transparent "Watch your step" overlay that appears periodically or when the device detects walking motion.
- **Criticality:** 🟡 MEDIUM

### M-09: AR Marker Clustering
- **Location:** `src/pages/discovery/DiscoveryPage.tsx`, AR view section
- **Source:** Master Prompt UP-5
- **Problem:** No marker clustering when multiple vendors are close together. All markers render independently, which can cause visual clutter.
- **Expected:** Markers within `AR_DEFAULTS.clusterThreshold` (30px) should cluster into a single bubble showing count, expandable on tap.
- **Criticality:** 🟡 MEDIUM

### M-10: Map View Filter Bar
- **Location:** `src/pages/discovery/DiscoveryPage.tsx`, map view section
- **Source:** Frontend Plan Part 2
- **Problem:** No filter bar on the map view. Users cannot filter by category, distance, open now, or tier.
- **Expected:** A horizontal filter bar below the map header with pill-style filter chips.
- **Criticality:** 🟠 HIGH

### M-11: Map View Bottom Sheet / Side Panel
- **Location:** `src/pages/discovery/DiscoveryPage.tsx`, map view section
- **Source:** Frontend Plan Part 2
- **Problem:** Clicking a map pin navigates away from the map via `window.location.href`. Plan requires a bottom sheet (mobile) or side panel (desktop) showing vendor preview.
- **Expected:** Tapping a pin opens a draggable bottom sheet with vendor card, quick actions (directions, call, save), and "View Profile" button.
- **Criticality:** 🟠 HIGH

### M-12: List View Infinite Scroll
- **Location:** `src/pages/discovery/DiscoveryPage.tsx`, list view section
- **Source:** Frontend Plan Part 2
- **Problem:** All vendor results load at once with no pagination. No infinite scroll implementation.
- **Expected:** Initial load of `pageSize: 20`, with `IntersectionObserver`-based infinite scroll loading more as user scrolls.
- **Criticality:** 🟠 HIGH

### M-13: List View Pull-to-Refresh
- **Location:** `src/pages/discovery/DiscoveryPage.tsx`, list view section
- **Source:** Frontend Plan Part 2
- **Problem:** No pull-to-refresh gesture on mobile list view.
- **Expected:** Touch-based pull-to-refresh with a branded spinner animation.
- **Criticality:** 🟡 MEDIUM

### M-14: Navigation Deep Linking to Native Apps
- **Location:** `src/pages/navigation/NavigationPage.tsx`
- **Source:** Frontend Plan Part 2
- **Problem:** Only in-app Mapbox navigation available. No fallback to native map apps.
- **Expected:** "Open in Google Maps / Apple Maps / Waze" buttons before in-app navigation starts.
- **Criticality:** 🟠 HIGH

### M-15: Preferences — Clear History / Delete Account / Export Data
- **Location:** `src/pages/preferences/PreferencesPage.tsx`
- **Source:** Frontend Plan Part 2, Master Prompt UP-12
- **Problem:** Privacy & Data section is completely missing. API functions exist (`clearSearchHistory`, `requestDataExport`, `requestAccountDeletion`, `requestDeletionCode`) but none are used.
- **Expected:** A "Privacy & Data" section with clear history button, export data button, and delete account flow (OTP confirmation).
- **Criticality:** 🟠 HIGH

### M-16: Preferences — Language Selection
- **Location:** `src/pages/preferences/PreferencesPage.tsx`
- **Source:** Master Prompt UP-12
- **Problem:** No language selection in appearance settings.
- **Expected:** Language dropdown with at least English and Urdu options.
- **Criticality:** 🟡 MEDIUM

### M-17: navigationStore (Zustand)
- **Location:** `src/store/` — no `navigationStore.ts` exists
- **Source:** Frontend Plan Part 1
- **Problem:** NavigationPage uses local `useState` for all navigation state. No centralized store.
- **Expected:** A `navigationStore` with destination, route, steps, currentStep, isNavigating, ETA.
- **Criticality:** 🟡 MEDIUM

### M-18: Rate Limit UX
- **Location:** Entire app
- **Source:** Frontend Plan Part 2, Critical Audit Fixes
- **Problem:** `apiClient` dispatches `CustomEvent('airad:rate-limit')` on 429, but nothing listens for it. `uiStore` has `rateLimitUntil` but it's never set.
- **Expected:** A banner or modal showing "Too many requests — please wait X seconds" with a countdown timer.
- **Criticality:** 🟡 MEDIUM

### M-19: Guest Token Acquisition
- **Location:** `src/main.tsx`
- **Source:** Frontend Plan Part 1, Backend Plan
- **Problem:** `getGuestToken()` API function exists in `src/api/auth.ts` but is never called. Guest users have no token — discovery API calls may fail.
- **Expected:** On app init, if no auth token exists, acquire a guest token and store it via `authStore.setGuestToken()`.
- **Criticality:** 🟠 HIGH

### M-20: Session Analytics Start
- **Location:** `src/main.tsx`
- **Source:** Frontend Plan Part 1
- **Problem:** `startSession()` API function exists in `src/api/analytics.ts` but is never called. No session tracking.
- **Expected:** Call `startSession()` on app mount.
- **Criticality:** 🟢 LOW

### M-21: Behavioral Ranking Client Tracking
- **Location:** Not implemented
- **Source:** Frontend Plan Part 1
- **Problem:** Plan specifies an initial behavioral ranking enhancement strategy with client-side tracking of user behavior. No tracking events are sent (except `recordInteraction` which is only called on call/share).
- **Expected:** Track events for: vendor_view, deal_view, reel_view, search, tag_select, navigation_start, direction_request.
- **Criticality:** 🟡 MEDIUM

### M-22: Vendor Profile Gallery/Media Viewer
- **Location:** `src/pages/vendor/VendorProfilePage.tsx`
- **Source:** Master Prompt UP-8, Frontend Plan Part 2
- **Problem:** `VendorDetail` type has `gallery_urls` but they are never displayed. No gallery or media viewer component.
- **Expected:** A scrollable gallery section showing vendor photos with lightbox zoom.
- **Criticality:** 🟡 MEDIUM

### M-23: Vendor Profile Full Business Hours
- **Location:** `src/pages/vendor/VendorProfilePage.tsx` lines 128, 228-230
- **Source:** Master Prompt UP-8
- **Problem:** Only today's hours are shown. Users cannot see the full weekly schedule.
- **Expected:** An expandable section showing all 7 days with today highlighted.
- **Criticality:** 🟢 LOW

### M-24: Reels Infinite Scroll / Pagination
- **Location:** `src/pages/reels/ReelsPage.tsx`
- **Source:** Frontend Plan Part 2
- **Problem:** All reels load at once. `getReelsFeed` accepts `page` param but it's always 1.
- **Expected:** Load initial batch, fetch next page as user scrolls near the end.
- **Criticality:** 🟠 HIGH

### M-25: Preferences Backend Sync
- **Location:** `src/pages/preferences/PreferencesPage.tsx`
- **Source:** Frontend Plan Part 2
- **Problem:** All preference changes are local only (Zustand persist). API functions `getUserPreferences()` and `updateUserPreferences()` exist but are never called.
- **Expected:** On mount, fetch preferences from backend. On change, PATCH to backend. Fall back to local if offline.
- **Criticality:** 🟠 HIGH

### M-26: Search Bar Autocomplete / Suggestions
- **Location:** `src/pages/discovery/DiscoveryPage.tsx`
- **Source:** Frontend Plan Part 1, Master Prompt UP-5
- **Problem:** `getSearchSuggestions()` API exists but is never used. Search bar on discovery is `readOnly`.
- **Expected:** Interactive search bar with debounced autocomplete suggestions dropdown.
- **Criticality:** 🟠 HIGH

---

## 2. OVERLOOKED — Implemented but rules violated

### O-01: Hardcoded Hex Colors in TSX
- **Location:** `src/pages/navigation/NavigationPage.tsx` lines 167, 171, 175
- **Source:** Master Prompt Design Rules, "Zero hardcoded hex colors"
- **Problem:** Three hardcoded hex colors: `#3B82F6` (route line), `#10B981` (origin marker), `#EF4444` (destination marker).
- **Expected:** Use DLS tokens: `var(--brand-teal)` for route, `var(--color-success)` for origin, `var(--brand-crimson)` for destination.
- **Criticality:** 🔴 CRITICAL

### O-02: Hardcoded Hex Color in CSS Module
- **Location:** `src/pages/navigation/NavigationPage.module.css` line 327
- **Source:** Master Prompt Design Rules
- **Problem:** `.stopBtn:hover` uses `#dc2626` instead of a CSS variable.
- **Expected:** `var(--brand-crimson)`.
- **Criticality:** 🔴 CRITICAL

### O-03: `any` Type Usage
- **Location:** `src/pages/navigation/NavigationPage.tsx` line 57
- **Source:** TypeScript strict mode, Frontend Plan quality standards
- **Problem:** `(s: any)` for Mapbox directions API response mapping.
- **Expected:** Define a proper `MapboxDirectionsStep` interface.
- **Criticality:** 🟡 MEDIUM

### O-04: `console.error` in Production Code
- **Location:** `src/pages/discovery/DiscoveryPage.tsx` line 145
- **Source:** Production standards, "No AI slop"
- **Problem:** `console.error('Camera access error:', error)` left in production code.
- **Expected:** Remove or replace with proper error tracking.
- **Criticality:** 🟠 HIGH

### O-05: `window.location.href` Instead of React Router
- **Location:** `src/pages/discovery/DiscoveryPage.tsx` lines 306, 425, 624
- **Source:** SPA architecture, React Router v6 best practices
- **Problem:** Four uses of `window.location.href = '/vendor/...'` causing full page reloads instead of client-side navigation.
- **Expected:** Use React Router's `useNavigate()` hook or `<Link>` components.
- **Criticality:** 🔴 CRITICAL

### O-06: Inline Styles in Multiple Components
- **Location:** Multiple files (see list below)
- **Source:** Master Prompt "Zero inline styles", Frontend Plan DLS rules
- **Problem:** Inline `style={{}}` used in:
  - `VendorProfilePage.tsx` line 96: `style={{ padding, display, flexDirection, gap }}`
  - `VendorCard.tsx` line 35: `style={{ background: TIER_COLORS[...] }}`
  - `TierBadge.tsx` line 13: `style={{ color, borderColor }}`
  - `LandingPage.tsx` line 198: `style={{ color: mode.color }}`
  - `DiscoveryPage.tsx` lines 282, 429, 633: tier color inline styles
  - `ReelsPage.tsx` lines 178, 184, 257: scroll snap and width styles
- **Expected:** Use CSS custom properties (e.g., `--tier-color`) or CSS classes. Dynamic values via `style` attribute with CSS custom properties are acceptable.
- **Criticality:** 🟠 HIGH

### O-07: Map Style Not Theme-Aware
- **Location:** `src/pages/discovery/DiscoveryPage.tsx` line 71, `NavigationPage.tsx` line 134
- **Source:** Frontend Plan Part 1, Design System
- **Problem:** Map always uses `'mapbox://styles/mapbox/streets-v12'` regardless of dark/light theme. Constants define `MAP_DEFAULTS.style` (dark) and `MAP_DEFAULTS.styleLight` but they are never used.
- **Expected:** Use `MAP_DEFAULTS.style` for dark theme and `MAP_DEFAULTS.styleLight` for light theme, switching dynamically.
- **Criticality:** 🟠 HIGH

### O-08: Search Bar is Read-Only
- **Location:** `src/pages/discovery/DiscoveryPage.tsx` line 335
- **Source:** Master Prompt UP-5 "persistent search bar"
- **Problem:** Discovery search input has `readOnly` attribute. Users cannot type to search — only voice is available.
- **Expected:** Interactive search bar with text input, debounced API call, and autocomplete suggestions.
- **Criticality:** 🟠 HIGH

### O-09: Tag Browser Apply Does Nothing
- **Location:** `src/pages/discovery/DiscoveryPage.tsx` lines 256-260
- **Source:** Frontend Plan Part 2, Tag Browser section
- **Problem:** `handleTagsApply` closes the modal but doesn't filter vendors. Comment: "Here you would typically update the search with selected tags".
- **Expected:** Apply selected tags to the nearby vendors query, refetch with tags parameter.
- **Criticality:** 🟠 HIGH

### O-10: Hero Stats Hardcoded
- **Location:** `src/pages/landing/LandingPage.tsx` lines 92-106
- **Source:** Frontend Plan Part 1, Social Proof section
- **Problem:** "500+ Vendors", "15+ Cities", "4.8 Rating" are hardcoded strings.
- **Expected:** Fetch from backend API or use constants that can be updated.
- **Criticality:** 🟡 MEDIUM

### O-11: Map Pins Use Emoji Instead of Custom DOM Pins
- **Location:** `src/pages/discovery/DiscoveryPage.tsx` lines 277-308
- **Source:** Frontend Plan Part 2, Map View section
- **Problem:** Map markers use basic `📍` emoji. Plan requires tier-colored custom DOM pins with pulsing animation for active promotions.
- **Expected:** Custom-styled DOM markers colored by tier (`TIER_COLORS`), with CSS pulse animation for vendors with active promotions.
- **Criticality:** 🟡 MEDIUM

### O-12: Vendor Profile No Floating Action Button
- **Location:** `src/pages/vendor/VendorProfilePage.tsx`
- **Source:** Frontend Plan Part 2, Vendor Profile section
- **Problem:** No floating action button (FAB) for quick navigation. Plan specifies a persistent FAB with directions icon.
- **Expected:** A `position: fixed` FAB in bottom-right with navigation icon, branded shadow (`--shadow-fab`).
- **Criticality:** 🟡 MEDIUM

---

## 3. PARTIALLY IMPLEMENTED — Feature exists but incomplete

### P-01: AR View — No Spatial Positioning
- **Location:** `src/pages/discovery/DiscoveryPage.tsx` lines 384-448
- **Source:** Master Prompt UP-5, Frontend Plan Part 2
- **Problem:** Camera feed works and AR markers load from API. But:
  - Markers are positioned as static floating divs, NOT spatially based on bearing/distance
  - No `DeviceOrientationEvent` integration for heading-based positioning
  - No proximity-based marker sizing (closer = larger)
  - Desktop fallback (simulated AR with gradient background + floating cards) not implemented
- **Expected:** On mobile: position markers using bearing + distance from API. On desktop: gradient background with randomly positioned cards that animate smoothly.
- **Criticality:** 🔴 CRITICAL

### P-02: Voice Search — No Interim Display or Suggestions
- **Location:** `src/pages/discovery/DiscoveryPage.tsx` lines 539-646
- **Source:** Frontend Plan Part 2, Voice Search section
- **Problem:** Basic speech-to-text works but:
  - `interimTranscript` from `useVoice` is never displayed (only final transcript shown)
  - No suggestion chips for common queries
  - Voice error display is minimal
  - No animated waveform responding to actual audio levels
- **Expected:** Real-time interim text, suggestion chips, animated waveform visualization.
- **Criticality:** 🟠 HIGH

### P-03: Tag Browser — No Section Distinction or Preview Counter
- **Location:** `src/pages/discovery/DiscoveryPage.tsx` lines 648-727
- **Source:** Frontend Plan Part 2, Tag Browser section
- **Problem:** Tags load and display by section, but:
  - No visual distinction for "What's Hot Right Now" section (should have special styling/icons)
  - No floating preview counter showing "View X vendors" as tags are selected
  - Selected tags don't filter vendors (see O-09)
- **Expected:** Hot section with flame icon and gradient background. Floating counter pill with vendor count.
- **Criticality:** 🟠 HIGH

### P-04: Deals Page — No Urgency Coding or Countdown Timers
- **Location:** `src/pages/deals/DealsPage.tsx`
- **Source:** Frontend Plan Part 2, Deals Tab section
- **Problem:** Deal cards show basic time remaining text, but:
  - No urgency color coding (red if <2h, orange if <6h, etc.)
  - `CountdownTimer` component exists but is NOT used on deal cards
  - No deal image display (always shows `<Percent>` icon placeholder)
  - No graceful removal animation when a deal expires
- **Expected:** Each deal card shows a countdown timer, urgency-colored border, deal image, and smoothly fades out on expiry.
- **Criticality:** 🟠 HIGH

### P-05: Vendor Profile — No Parallax or Sticky Header
- **Location:** `src/pages/vendor/VendorProfilePage.tsx`
- **Source:** Master Prompt UP-8, Frontend Plan Part 2
- **Problem:** Vendor profile loads and displays data correctly, but:
  - No parallax scroll effect on cover image
  - No sticky header that condenses on scroll
  - Gallery images not displayed
  - Voice bot section missing
  - Business hours only show today
- **Expected:** Cover image parallax on scroll. Header becomes sticky with condensed vendor name + tier badge on scroll. Full feature set.
- **Criticality:** 🟠 HIGH

### P-06: Reels Page — Non-functional Like, No Playback Progress
- **Location:** `src/pages/reels/ReelsPage.tsx`
- **Source:** Frontend Plan Part 2, Reels Feed section
- **Problem:** Video feed with scroll-snap works, but:
  - Like button (`<Heart>`) has no onClick handler, no API call, no state toggle
  - Progress bar shows reel index (`(index+1)/total`) instead of actual video playback progress
  - No infinite scroll pagination
  - No double-tap-to-like gesture
- **Expected:** Functional like with heart animation, actual video progress bar, pagination, double-tap gesture.
- **Criticality:** 🟡 MEDIUM

### P-07: Navigation — No GPS-Based Arrival Detection
- **Location:** `src/pages/navigation/NavigationPage.tsx`
- **Source:** Frontend Plan Part 2, Navigation section
- **Problem:** Navigation works with Mapbox directions, but:
  - Arrival detection is manual (user clicks "End Navigation") instead of GPS proximity-based
  - No live location tracking during navigation (map doesn't update user position)
  - No "Open in Google Maps" fallback
- **Expected:** `watchPosition` during navigation, auto-detect arrival within 50m, trigger celebration + recording.
- **Criticality:** 🟡 MEDIUM

### P-08: Preferences — Local Only, No Backend Sync
- **Location:** `src/pages/preferences/PreferencesPage.tsx`
- **Source:** Frontend Plan Part 2, Preferences section
- **Problem:** All settings persist only in localStorage via Zustand. API functions `getUserPreferences()` and `updateUserPreferences()` are never called. Settings are lost on device change.
- **Expected:** Fetch preferences on mount (for authenticated users), PATCH on change, fallback to local.
- **Criticality:** 🟠 HIGH

---

## 4. WOW FACTOR COMPROMISED — Below expected quality standard

### W-01: Landing Page — Not "Claude.ai" Minimal Feel
- **Location:** `src/pages/landing/LandingPage.tsx`
- **Source:** Master Prompt UP-3
- **Problem:** Master prompt explicitly says: "Landing page claude.ai jaisi feel honi chahiye — ek powerful search bar + mic button, clean, minimal." And: "Main section mein video ya slides use karo."

  Current landing page is a standard marketing page with:
  - No prominent search bar in hero section
  - No video or animated slides in hero
  - No social proof section (separate from hero stats)
  - Standard card-based layout instead of minimal, powerful design
- **Expected:** A hero section with a large, centered search bar + mic button (like Claude.ai), background video or animated gradient, minimal text, and a striking first impression.
- **Criticality:** 🔴 CRITICAL

### W-02: AR View — Not Immersive
- **Location:** `src/pages/discovery/DiscoveryPage.tsx`, AR section
- **Source:** Master Prompt UP-5
- **Problem:** AR is the signature feature but current implementation is:
  - Just a camera feed with static floating divs
  - No glassmorphism on markers (no `backdrop-filter`)
  - No spatial positioning (all markers in same area)
  - No smooth animations or transitions
  - No proximity-based sizing
- **Expected:** Glassmorphism markers with blur effect, spatially positioned based on bearing, size varying by distance, smooth entrance animations, immersive camera overlay.
- **Criticality:** 🔴 CRITICAL

### W-03: Map View — Generic Pins
- **Location:** `src/pages/discovery/DiscoveryPage.tsx`, map section
- **Source:** Frontend Plan Part 2
- **Problem:** Map uses emoji `📍` markers instead of branded custom DOM pins. No pulsing animation for promotions. No visual tier distinction on the map.
- **Expected:** Custom circular pins with tier-color borders, vendor logo/initial inside, pulsing glow animation for vendors with active promotions.
- **Criticality:** 🟠 HIGH

### W-04: Vendor Profile — Flat and Basic
- **Location:** `src/pages/vendor/VendorProfilePage.tsx`
- **Source:** Master Prompt UP-8
- **Problem:** Profile page looks like a basic information page rather than a premium, immersive experience. No parallax, no sticky transitions, no floating elements, no animations.
- **Expected:** Cover image with parallax scroll, smooth header transition, animated entrance of sections, floating navigation FAB.
- **Criticality:** 🟠 HIGH

### W-05: Reels — Missing Polish
- **Location:** `src/pages/reels/ReelsPage.tsx`
- **Source:** Frontend Plan Part 2
- **Problem:** Basic video scroll works but lacks the TikTok-level polish:
  - No smooth transition animations between reels
  - No heart animation on like
  - No double-tap gesture
  - Progress bar doesn't track actual playback
- **Expected:** Buttery smooth transitions, interaction animations, actual video progress tracking.
- **Criticality:** 🟡 MEDIUM

### W-06: Voice Search — Missing Animation
- **Location:** `src/pages/discovery/DiscoveryPage.tsx`, voice modal
- **Source:** Master Prompt UP-6, Frontend Plan Part 2
- **Problem:** Voice search has a basic pulsing animation. No actual waveform responding to audio input levels. No suggestion chips. No smooth state transitions.
- **Expected:** Audio-reactive waveform visualization, smooth state machine transitions (idle → listening → processing → results), suggestion chips.
- **Criticality:** 🟡 MEDIUM

### W-07: Deals Page — No Urgency Feel
- **Location:** `src/pages/deals/DealsPage.tsx`
- **Source:** Frontend Plan Part 2
- **Problem:** Deal cards look static and uniform. No urgency indicators, no countdown timers, no visual hierarchy between expiring-soon and long-running deals.
- **Expected:** Red-bordered cards for <2h, orange for <6h, countdown timers on each card, flash deal badge with animation.
- **Criticality:** 🟠 HIGH

---

## 5. Code Quality Issues

| Issue | Location | Severity |
|---|---|---|
| Hardcoded hex `#3B82F6`, `#10B981`, `#EF4444` | `NavigationPage.tsx:167,171,175` | 🔴 CRITICAL |
| Hardcoded hex `#dc2626` | `NavigationPage.module.css:327` | 🔴 CRITICAL |
| `any` type | `NavigationPage.tsx:57` | 🟡 MEDIUM |
| `console.error` in production | `DiscoveryPage.tsx:145` | 🟠 HIGH |
| `window.location.href` (4 occurrences) | `DiscoveryPage.tsx:306,425,624` | 🔴 CRITICAL |
| Inline styles (10+ occurrences) | Multiple files | 🟠 HIGH |
| Read-only search bar | `DiscoveryPage.tsx:335` | 🟠 HIGH |
| Tag apply does nothing | `DiscoveryPage.tsx:256-260` | 🟠 HIGH |

---

## 6. Priority Fix Order

### Phase 1 — Critical Blockers (Must fix first)
1. **M-01** Error Boundary
2. **O-01** + **O-02** Hardcoded hex colors
3. **O-05** `window.location.href` → React Router
4. **M-03** Guest access to preferences
5. **M-19** Guest token acquisition

### Phase 2 — Core Feature Gaps
6. **W-01** Landing page WOW redesign (search bar + video hero)
7. **W-02** + **P-01** AR view glassmorphism + spatial positioning
8. **M-02** Promotions strip on discovery
9. **O-08** + **M-26** Interactive search bar + autocomplete
10. **O-09** + **P-03** Tag browser apply + preview counter
11. **M-10** + **M-11** Map filter bar + bottom sheet
12. **M-12** + **M-13** Infinite scroll + pull-to-refresh
13. **W-03** Custom map pins

### Phase 3 — Feature Completion
14. **P-04** + **W-07** Deals urgency coding + countdown timers
15. **M-04** Flash deal toasts
16. **P-05** + **W-04** Vendor profile parallax + sticky header
17. **M-06** Vendor voice bot
18. **M-22** + **M-23** Gallery + full business hours
19. **O-12** Floating action button
20. **P-06** + **W-05** Reels polish
21. **M-14** + **P-07** Navigation deep links + GPS arrival

### Phase 4 — Polish & Compliance
22. **P-02** + **W-06** Voice search polish
23. **M-05** GDPR consent banner
24. **M-15** Preferences privacy section
25. **M-25** + **P-08** Preferences backend sync
26. **M-18** Rate limit UX
27. **O-03** + **O-04** + **O-06** Code quality fixes
28. **O-07** Theme-aware map style
29. **M-20** + **M-21** Session analytics + behavioral tracking
30. **O-10** Dynamic hero stats
31. **M-16** + **M-17** Language selection + navigation store

---

## 7. Files Audited

| File | Lines | Issues Found |
|---|---|---|
| `src/main.tsx` | 48 | M-01, M-19, M-20 |
| `src/router.tsx` | 135 | M-03 |
| `src/styles/dls-tokens.css` | 298 | Clean ✓ |
| `src/styles/shared.css` | — | Clean ✓ |
| `src/pages/landing/LandingPage.tsx` | 269 | W-01, O-06, O-10 |
| `src/pages/auth/LoginPage.tsx` | 156 | Clean ✓ |
| `src/pages/auth/RegisterPage.tsx` | 125 | Clean ✓ |
| `src/pages/discovery/DiscoveryPage.tsx` | 731 | M-02, M-07–09, M-10–13, M-26, O-04–06, O-08–09, O-11, P-01–03, W-02–03, W-06 |
| `src/pages/vendor/VendorProfilePage.tsx` | 308 | M-06, M-22–23, O-06, O-12, P-05, W-04 |
| `src/pages/deals/DealsPage.tsx` | 216 | M-04, P-04, W-07 |
| `src/pages/reels/ReelsPage.tsx` | 280 | M-24, O-06, P-06, W-05 |
| `src/pages/navigation/NavigationPage.tsx` | 415 | M-14, M-17, O-01–03, P-07 |
| `src/pages/preferences/PreferencesPage.tsx` | 301 | M-15–16, M-25, P-08 |
| `src/pages/error/NotFoundPage.tsx` | 22 | Clean ✓ |
| `src/store/authStore.ts` | 68 | Clean ✓ |
| `src/store/discoveryStore.ts` | 74 | Clean ✓ |
| `src/store/uiStore.ts` | 62 | Clean ✓ |
| `src/store/preferencesStore.ts` | 38 | Clean ✓ |
| `src/hooks/useLocation.ts` | 100 | Clean ✓ |
| `src/hooks/useVoice.ts` | 150 | Clean ✓ |
| `src/hooks/useOnline.ts` | 23 | Clean ✓ |
| `src/hooks/useMediaQuery.ts` | 35 | Clean ✓ |
| `src/api/client.ts` | 153 | Clean ✓ |
| `src/api/discovery.ts` | 114 | Clean ✓ |
| `src/api/vendor.ts` | 40 | Clean ✓ |
| `src/api/auth.ts` | 38 | Clean ✓ |
| `src/api/deals.ts` | 32 | Clean ✓ |
| `src/api/reels.ts` | 19 | Clean ✓ |
| `src/api/navigation.ts` | 25 | Clean ✓ |
| `src/api/preferences.ts` | 56 | Clean ✓ |
| `src/api/analytics.ts` | 24 | Clean ✓ |
| `src/api/geo.ts` | 17 | Clean ✓ |
| `src/types/api.ts` | 204 | Clean ✓ |
| `src/queryKeys.ts` | 46 | Clean ✓ |
| `src/utils/formatters.ts` | 98 | Clean ✓ |
| `src/utils/constants.ts` | 60 | Clean ✓ |
| `src/components/dls/*` (8 components) | ~320 | O-06 (TierBadge, VendorCard, SkeletonLoader) |
| `index.html` | 24 | Clean ✓ |

---

**Total Issues: 53**
**Critical: 12 | High: 24 | Medium: 14 | Low: 3**

_Report generated by deep multi-source analysis against:_
- _AirAds_User_Portal_Super_Master_Prompt.md (UP-0 through UP-13)_
- _USER_PORTAL_FRONTEND_PLAN_PART1.md_
- _USER_PORTAL_FRONTEND_PLAN_PART2.md_
- _USER_PORTAL_BACKEND_PLAN_PART1.md + PART2.md (API contracts)_
