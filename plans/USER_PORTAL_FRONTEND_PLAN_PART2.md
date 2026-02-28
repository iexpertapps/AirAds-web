# USER PORTAL FRONTEND PLAN — PART 2
## Map View, List View, Voice Search, Tag Browsing, Vendor Profile, Deals, Reels, Navigation, Preferences, Performance, Accessibility, QA

Part 2 of User Portal Frontend Plan. Part 1 covered: Application identity, tech stack, design system, component library, state management, routing, landing page, auth pages, discovery shell, AR view.

---

## TABLE OF CONTENTS (Part 2)

11. [Map View](#11-map-view)
12. [List View](#12-list-view)
13. [Voice Search UI/UX Flow](#13-voice-search-uiux-flow)
14. [Tag Browser](#14-tag-browser)
15. [Vendor Profile Page](#15-vendor-profile-page)
16. [Deals Tab](#16-deals-tab)
17. [Reels Feed](#17-reels-feed)
18. [Navigation Experience](#18-navigation-experience)
19. [User Preferences Page](#19-user-preferences-page)
20. [Responsive Design Strategy](#20-responsive-design-strategy)
21. [Performance Targets & Optimization](#21-performance-targets--optimization)
22. [Accessibility Requirements](#22-accessibility-requirements)
23. [Guest vs Logged-In Mode Differences](#23-guest-vs-logged-in-mode-differences)
24. [Build Sequence & Sessions](#24-build-sequence--sessions)
25. [Quality Gate Checklist](#25-quality-gate-checklist)

---

## 11. MAP VIEW

### 11.1 Mapbox GL JS Integration

Library: `mapbox-gl` — dynamically imported as a separate Vite chunk.
Token: `VITE_MAPBOX_TOKEN` in `.env` — never hardcoded in source.
Map style: `mapbox://styles/mapbox/dark-v11` (built-in dark), overridden with brand colors.

### 11.2 Vendor Pins (Custom DOM Elements)

Custom markers (DOM-based, not Mapbox symbols) — enables CSS animations:
```
Tier colors:
  Silver:   #9E9E9E pill marker
  Gold:     #FFC107 pill marker
  Diamond:  #00BCD4 (brand teal) pill marker
  Platinum: brand gradient (CSS linear-gradient) pill marker

Category emoji inside pin: 16px on white circle background
Active promotion ring:
  CSS keyframe: scale(1) → scale(1.4) + opacity(1) → opacity(0), 2s loop
  Ring color: var(--brand-orange)
  Applied to ::before pseudo-element of each promoted vendor marker
```

### 11.3 Pin Tap Behavior

```
Desktop (> 1024px): Right side panel slides in (320px, Framer Motion x: 320→0)
Mobile (≤ 1024px): Bottom sheet (Framer Motion drag, max-height: 60vh, drag handle at top)

Sheet content:
  Vendor name (bold 18px)
  Category chip (TagChip sm)
  DistanceBadge component
  "Open Now" green dot | "Closed" grey dot + hours
  PromotionBadge (lg) if active
  Two buttons (full width):
    "View Full Profile →" → /vendor/:id
    "🧭 Get Directions" → /navigate/:id (fires NAVIGATION interaction)
```

### 11.4 Filter Bar (Horizontal Scroll, Below Header)

```
Container: horizontal scroll, hidden scrollbar (custom scrollbar CSS)
Gap: 8px between chips

Chips: category slugs + status filters
  "🍕 Food" "☕ Coffee" "✂️ Services" "🛍️ Retail" "🔥 Deals"
  "Open Now 🟢" "Has Discount 🏷️" "Verified ✓"

Active chip: brand orange bg, white text, × icon to remove this specific filter
"Clear All" chip: var(--color-error) crimson — only visible when ≥ 1 filter active

Filter state: discoveryStore.activeTagSlugs → TanStack Query params → refetch mapPins
Pin update: filtered-out markers fade to opacity: 0 (transition 200ms), visible markers remain
```

---

## 12. LIST VIEW

### 12.1 Layout

```
CustomScrollView equivalent below sticky header.
Sort control (top-right): "Best Match" (default) | "Nearest" | "Active Deals"

Infinite scroll:
  TanStack useInfiniteQuery, page_size: 20
  IntersectionObserver on last visible card → fetchNextPage
  Loading more: 3 VendorCardSkeleton at bottom (shimmer, not spinner)

Pull-to-refresh (mobile):
  CSS overscroll-behavior: contain
  onscroll check: scrollY < -60 → trigger refetch
  Indicator: AirAds logo spinning (Framer Motion rotate, 1s linear loop)
```

### 12.2 Empty States

```
Container: centered, padding: 40px
  Logo: 60px, opacity: 0.12
  Context-aware messages:
    No tag match:    "No [food] places within [radius] right now."
    Open now filter: "No places open right now matching your filters."
    All empty:       "No vendors found in this area."
  Suggestion (14px secondary): "Try: expanding radius or removing filters."
  Two CTAs: "Expand Radius" | "Remove All Filters"
```

---

## 13. VOICE SEARCH UI/UX FLOW

### 13.0 Cross-Browser Compatibility

> **[AUDIT FIX — HIGH 1.13]** `SpeechRecognition` is unprefixed in Chrome/Edge but requires `webkitSpeechRecognition` in Safari (iOS and macOS). Safari is the dominant browser on iOS — this is a critical fix.

```typescript
// In useVoice.ts — hook initialization:
const SpeechRecognitionAPI =
  (window as any).SpeechRecognition ||
  (window as any).webkitSpeechRecognition ||
  null;

const isVoiceSupported = SpeechRecognitionAPI !== null;
```

Behavior matrix:
- **Chrome/Edge (desktop + Android):** `SpeechRecognition` — full support ✅
- **Safari (iOS 14.5+):** `webkitSpeechRecognition` — supported via prefix ✅
- **Safari (iOS < 14.5):** null — silent fallback to text input ✅
- **Firefox:** null — silent fallback to text input ✅

When `isVoiceSupported === false`:
- Mic button: rendered as normal search icon (not a mic), no pulsing
- On tap: focus text input directly (no error message — seamless degradation)
- Never show "Voice not supported" error — just silently become a text search button

### 13.1 Trigger & Listening Mode

```
Mic button: always visible in DiscoverySearchBar (compact, right side)
Also in landing page hero bar

On mic tap:
  1. DiscoverySearchBar expands (Framer Motion layout animation, spring)
  2. Dark overlay behind bar (opacity: 0 → 0.85, 150ms)
  3. Large pulsing mic icon (56px, brand crimson, 3 concentric rings pulsing outward)
  4. VoiceWave component activates (5 crimson bars, animated)
  5. Real-time transcript appears word by word (Framer Motion stagger 50ms per word)

X button or Escape: cancel → collapse back to normal search bar
```

### 13.2 After Speech

```
1. "Searching for: [transcript]" (500ms confirmation beat)
2. POST voice-search API
3. Brief spinner (< 200ms typical)
4. Overlay collapses
5. Results appear in active view (AR/Map/List) with filters applied
6. Filter chips update: extracted category chip appears in filter bar
```

### 13.3 Error States

```
Mic denied:
  Show mic-with-slash icon (no pulsing)
  "Microphone access needed for voice search."
  "You can type here instead →" — input auto-focused
  Never crash, seamless fallback to text search

No speech detected:
  "I didn't catch that. Try again or type below."
  Retry button (brand orange) + text input below

No results:
  "No matches for '[transcript]'. Try:"
  3 suggested query chips: "food nearby" | "open cafe" | "deals right now"
```

### 13.4 Voice Suggestions

```
Shown as floating chips above mic before listening starts (disappear when speech begins):
  "Cheap lunch near me" | "Open cafe right now" | "Salons with discounts" | "What's open nearby?"

Sources: user's recent voice queries (search-history API) OR hardcoded popular queries as fallback
Fade out: Framer Motion opacity 1→0 as soon as interim transcript appears
```

### 13.5 Vendor-Specific Voice Bot

```
Entry: "🎙️ Ask this place" button on Vendor Profile (only if voice_bot.available === true)
       Hidden completely for Silver vendors (backend enforces, frontend checks field)

Bottom Sheet (Framer Motion drag, 50vh):
  Header: "🎙️ Ask [Vendor Name]" + close button
  Mic icon (40px, crimson glow)
  Status text: "Tap the mic to ask a question"
  3 suggested queries (chips, tappable — auto-send):
    "What's the lunch special?" | "Are you open Sunday?" | "Do you deliver?"

  Q&A history (last 3 pairs):
    User Q: right-aligned (brand orange bg)
    Vendor A: left-aligned (var(--color-bg-elevated))

  TTS toggle: speaker icon (top-right of sheet) — uses SpeechSynthesis API
  On query: same listening flow as global voice (smaller scale)
  API response: voice_response text + follow_up_suggestions → rendered as next chips
```

---

## 14. TAG BROWSER

### 14.1 Trigger & Layout

```
Trigger: "Browse 🏷️" bottom nav tab (mobile) OR "See All Categories" link
Mobile: DraggableScrollableSheet (Framer Motion drag, max-height: 85vh, drag handle)
Desktop: Right panel (320px, persistent alongside discovery view)
```

### 14.2 Section 1 — What's Hot Right Now

```
Title: "🔥 What's Hot Right Now" (14px semibold secondary)
Horizontal scroll row:
  TagChip (hot variant — orange bg) per result
  Content: "[emoji] [label] ([active_deal_count] deals)"
  Example: "🍕 Pizza (12 deals)"
Skeleton: 4 shimmer chips while loading
```

### 14.3 Section 2 — By Intent

```
Title: "✨ What are you looking for?"
2-col grid (mobile) / 4-col grid (desktop), 80px height per cell

Intent items (from API by_intent):
  Quick Bite 🍔 | Morning Coffee ☕ | Late Night 🌙 | Budget Friendly 💰
  Open Now 🟢 | Has Discount 🏷️ | Near Me 📍 | New Places ✨

Card design:
  Background: var(--color-bg-elevated), border-radius: var(--radius-lg)
  Emoji: 28px centered top, Label: 12px centered bottom
  Vendor count: 11px tertiary text
  Active state: brand orange border (2px) + bg rgba(255,140,0,0.08)
```

### 14.4 Section 3 — By Category

```
Title: "📋 All Categories"
3-col grid (mobile) / 5-col (desktop), 60px height per cell
Same card style, smaller
Icon + label + nearby count
```

### 14.5 Section 4 — By Distance

```
Title: "📍 By Distance"
3 full-width horizontal cards:
  "Walking (under 5 min)" — radius_m: 400
  "Nearby (under 10 min)" — radius_m: 800
  "In my area" — radius_m: 2000

Card: icon left, label + vendor_count right
Active: orange left border (3px)
On select: updates discoveryStore.searchRadius → closes sheet → filtered results visible
```

### 14.6 Multi-Select State

```
Multiple tags can be selected simultaneously (OR logic per tag type, AND between types)
Selected tags: shown as chips with × in persistent bottom strip of sheet
"Clear All" button: appears when ≥ 1 tag active, crimson color

Floating preview counter:
  "23 places match" — updates in real-time as tags change
  TanStack Query preview query (debounced 300ms) fetches count only
  Shown above close button (mobile) / at top of panel (desktop)

On sheet close: filters already applied in discoveryStore → discovery view already filtered
```

---

## 15. VENDOR PROFILE PAGE

### 15.1 Page Structure

```
Route: /vendor/:id — full-screen scrollable, custom sticky header with parallax
Back: browser back OR explicit back arrow button (top-left overlay)
```

### 15.2 Cover + Sticky Header (Parallax)

```
Cover area: 220px (mobile) / 280px (desktop)
Content: <video autoPlay muted playsInline loop> OR <img> (object-fit: cover)
Fallback: CSS gradient based on category + emoji centered (64px)

Parallax: onScroll → cover translateY(scrollY * 0.4) — slower than page content scroll

Overlay at cover bottom:
  Gradient: transparent → rgba(0,0,0,0.8)
  Text: vendor name (bold 24px white), category chip, DistanceBadge
  TierBadge: top-right corner of cover

Active promotion banner (if active):
  Below cover, full width
  Background: rgba(255,140,0,0.12) → rgba(196,30,58,0.12) gradient border
  Border: 1px solid rgba(255,140,0,0.3)
  "🔥 [promotion_label] · Ends in [countdown]"
  CountdownTimer (urgency colors per threshold)

Cover overlay buttons:
  Top-left: back arrow (ghost, dark circle bg, 40px, safe area padding)
  Top-right: share button (ghost, dark circle bg, Web Share API)
```

### 15.3 Quick Stats Bar (Sticky Post-Cover)

```
Appears sticky (position: sticky top: 60px) once cover scrolls out of view
Background: var(--color-bg-nav), height: 44px

Content: [distance] · [category] · [Open/Closed] · [voice bot icon if available]
Open: green dot + "Open until [time]"
Closed: grey dot + "Opens [day] at [time]"
```

### 15.4 Section 1 — Active Promotion Card (Highest Priority)

```
Only shown if active_promotion !== null
Position: first content section — user came here because of a deal

Card:
  Background: linear-gradient(135deg, rgba(255,140,0,0.1), rgba(196,30,58,0.1))
  Border: 1px solid rgba(255,140,0,0.4), border-radius: var(--radius-xl)
  Padding: 24px

  PromotionBadge (lg): "30% OFF" or "Happy Hour" (top)
  Promotion description: e.g. "On all main course dishes. Dine-in only." (middle)
  Bottom row:
    Left: CountdownTimer (crimson glow when < 1h remaining, pulsing)
    Right: "Get Directions Now →" (primary gradient button, lg)

Urgent state (< 1h remaining):
  Card gets: box-shadow: 0 0 30px rgba(196,30,58,0.3)
  Entire card pulses very subtly (CSS opacity 1 → 0.9 → 1, 2s loop)
```

### 15.5 Section 2 — About

```
Business description:
  Max 3 lines visible, "Show more" toggle (Framer Motion height animation)
  Font: 15px, line-height: 1.6

Business hours visual grid:
  7-column grid (Mon–Sun), each: day abbreviation (13px) + hours (12px)
  Today: brand orange text + underline
  Closed day: "—" in var(--color-text-tertiary)
  "Open ✓" or "Closed" label above grid (teal or grey, 13px)

Contact row:
  Phone: Phone icon + number → tap = tel: link → fires CALL interaction tracking
  Website: Globe icon + domain → tap = window.open + fires VIEW tracking

Service pills (read-only chips):
  "🚚 Delivery" (teal bg) | "🏪 Pickup only" (grey)
  "🛵 Free delivery from PKR [amount]" if configured
```

### 15.6 Section 3 — Videos / Reels

```
Hidden entirely if reels_count === 0

Title: "📹 Videos ([count])"
Horizontal scroll grid (touch-friendly, momentum scroll):
  Each item: 120×180px portrait thumbnail
  First item on screen: autoplay (muted) via IntersectionObserver
  Others: static thumbnail with play button overlay

  Thumbnail overlays:
    Play icon (center, 28px white)
    Duration badge (bottom-right, dark bg pill): "9s"
    PromotionBadge (bottom-left) if reel has_promotion

On tap: fullscreen reel player — same component as ReelsPage, single reel view
```

### 15.7 Section 4 — Location Map

```
Mobile: Mapbox Static Images API thumbnail (300px height)
  → Tappable: "See on Full Map →" navigates to /discover?pin=vendor_id
Desktop: Interactive Mapbox map (240px height, same instance reused)
  → vendor pin + user location
  → zoom/navigate controls visible

Below map:
  Address: "23 MM Alam Road, Gulberg III, Lahore" (14px secondary)
  "🧭 Get Directions →" button (secondary outlined, full-width)
  "See on Full Map →" text link (13px)
```

### 15.8 Section 5 — Voice Bot

```
Visible only if voice_bot.available === true (hidden for Silver vendors)

Card:
  Background: var(--color-bg-elevated)
  Border: 1px solid var(--color-border), border-radius: var(--radius-lg)
  Padding: 20px

  Mic icon (40px, crimson glow) + "🎙️ Ask this place anything"
  Suggested queries (13px secondary): "Try: What's the lunch special? · Are you open Sunday?"
  "Ask Now" button → opens VoiceBotSheet (see Section 13.5)
```

### 15.9 Section 6 — More Nearby

```
Title: "More [Category] Nearby" + "See all [Category] →" link (brand orange)
Horizontal scroll: 6 vendor cards (VendorCard compact variant, 160px width each)
Each card: tappable → /vendor/:id
```

### 15.10 Floating Action Button (Mobile Only)

```
Position: fixed bottom (above bottom nav), width: calc(100% - 48px), margin: 0 24px
Height: 52px, border-radius: var(--radius-full)
Background: var(--brand-gradient)
Content: "🧭 Get Directions"
box-shadow: 0 4px 20px rgba(255,140,0,0.35)

Show/hide:
  Visible from page load until Location section (Section 4) is in viewport
  IntersectionObserver on Location section header element
  Framer Motion: y: 0 → 80 when hiding (slides down), 0 when visible

On tap: navigate to /navigate/:id
```

---

## 16. DEALS TAB

### 16.1 Layout

```
Route: /deals
Header: "🔥 Active Near You Right Now" + count badge ("12 active deals")
  Count badge: AnimatedNumber (Framer Motion counter) updates every 60 seconds

Filter strip (horizontal scroll):
  "All" | "Food" | "Retail" | "Services" | "⚡ Flash Deals"
  "⚡ Flash Deals" chip: red dot badge if any active flash deals

Sort control (right side): "Ending Soon" (default) | "Closest" | "Best Value"
```

### 16.2 Deal Card Design (~120px auto height)

```
Background: var(--color-bg-surface)
Border-radius: var(--radius-xl)
Padding: 20px

Layout:
  Top row: PromotionBadge (lg, left) + CountdownTimer (right)
  Middle: Business name (bold) + category emoji
  Bottom: distance + "Open Now" indicator + "Get Directions →" ghost button

Urgency color system:
  > 2h remaining: normal (no special styling)
  1-2h remaining: CountdownTimer color = #FFC107 (amber) + card left border amber
  < 1h remaining: CountdownTimer crimson + pulsing + card box-shadow crimson glow

On tap: navigate to /vendor/:id
"Get Directions →" button: navigate to /navigate/:id (fires NAVIGATION tracking)
```

### 16.3 Flash Deal Toast

```
Trigger: /discovery/flash-alert/ API returns a deal (polled every 60s via TanStack Query)

Toast (Framer Motion y: -80 → 0, spring):
  Position: fixed top-20px, left-right: 16px (full width - 32px)
  Background: linear-gradient(90deg, var(--brand-orange), var(--brand-crimson))
  Border-radius: var(--radius-xl)
  Content: 🔥 icon + "Flash Deal started [distance]m from you!" + sub-text vendor name
  Actions (right side): "View →" (white small button) + "×" dismiss

Auto-dismiss: 8 seconds (clearTimeout on manual dismiss)
Managed by: uiStore.toasts — same toast system as other notifications
Never re-shows same flash deal: FlashDealAlert API handles server-side, client tracks seen IDs in sessionStorage
```

### 16.4 Expired Deal Removal

```
When CountdownTimer hits 0:
  Framer Motion exit animation: opacity 1→0 (400ms) + height 0 (400ms)
  AnimatePresence handles clean unmount from DOM
  Count badge decrements (AnimatedNumber)
  If list becomes empty: empty state shown (same design as list view empty state)
  No "sorry, deal expired" message — silent removal
```

---

## 17. REELS FEED

### 17.1 Feed Layout

```
Route: /reels
Full-screen, edge-to-edge: no navbar, background pure black
Bottom nav: VISIBLE but overlay-style (positioned absolute over black, fades to transparent bg on Reels tab)
  → Bottom nav is never fully hidden — users must be able to switch tabs without swiping back
  → On Reels tab: bottom nav bg = rgba(0,0,0,0) so it blends with black feed
  → Active tab indicator still visible (brand orange)
Background: #000000 (pure black)

CSS scroll snap:
  Container: overflow-y: scroll; scroll-snap-type: y mandatory; height: 100vh
  Each reel item: scroll-snap-align: start; height: 100vh; overflow: hidden
```

### 17.2 Video Player

```
<video> element: width: 100%, height: 100%, object-fit: cover
autoPlay, muted (default), playsInline, loop: false

Interactions:
  Tap center: toggle play/pause
  Swipe up: next reel (scroll-snap handles)
  Swipe right: skip vendor (remove vendor's reels from current feed session)

Sound: tap anywhere = toggle mute (muted by default for browser autoplay policy)
Mute indicator: 🔇 icon fades in/out on toggle (Framer Motion, 500ms fade)
```

### 17.3 Reel Overlay Elements

```
Bottom-left (vendor info):
  Vendor name (DM Sans Bold 18px, white, text-shadow: 0 1px 4px rgba(0,0,0,0.8))
  Category: TagChip (sm, semi-transparent dark bg)
  Distance: "📍 200m away" (13px white)

Bottom-right (actions):
  "🧭 Get Directions" circle button: 48×48px, brand orange bg, white arrow icon
  On tap: navigate to /navigate/:id

Bottom-center (promotion CTA — if has_promotion):
  Slide-up pill animation (Framer Motion y: 60 → 0, spring, 600ms delay after load)
  "🔥 20% OFF · Tap to visit →" — brand orange bg, pill shape
  On tap: navigate to /vendor/:id (fires PROMOTION_TAP tracking)

Top: progress bar (3px brand orange, animated width: 0% → 100% over video duration)
  CSS transition: width linear based on video.currentTime / video.duration
```

### 17.4 Reel View Tracking

```
IntersectionObserver on each reel container:
  On enter viewport: record entry time
  On exit viewport: calculate watched_seconds = exitTime - entryTime
                    determine completed = watched_seconds >= (duration - 1)
                    determine cta_tapped (flag set on promotion CTA click)
                    POST /track/reel-view/ (fire-and-forget — ignore response)
```

---

## 18. NAVIGATION EXPERIENCE

### 18.1 "Get Directions" Tap Flow

```
From any location (AR marker, map pin, vendor card, vendor profile FAB):

Step 1: Fire tracking (async, non-blocking)
  POST /track/interaction/ {vendor_id, type: 'NAVIGATION', session_id, lat, lng}

Step 2: Platform detection + deep link attempt
  iOS device (navigator.userAgent check):
    Try Apple Maps: maps://?daddr={lat},{lng}&dirflg=w
    Fallback: Google Maps web
  
  Android:
    Try Google Maps app: intent://maps.google.com/...#Intent;package=com.google.android.apps.maps;end
    Fallback: comgooglemaps:// scheme
    Final fallback: web Google Maps
  
  Desktop:
    Open: https://www.google.com/maps/dir/{user_lat},{user_lng}/{dest_lat},{dest_lng}
    target="_blank" (new tab)
```

### 18.2 In-App Navigation (`/navigate/:id`)

```
Route: /navigate/:id
Full-screen Mapbox map (same instance, no page re-mount if already initialized)

Stack layout:
  [0] MapboxMap (full-screen, navigation-focused dark style)
      User location: geolocate (watchPosition, brand teal pulsing dot)
      Destination: brand orange pulsing PointAnnotation
      Route line: Mapbox route (or straight line fallback), brand gradient stroke 5px

  [1] NavigationHeader (sticky top, 80px + safe area):
      Background: var(--color-bg-surface) + backdrop-blur(8px)
      "~ 4 min walk" (bold 20px) + "320m remaining" (secondary 15px)
      "Raja Burgers" (truncated destination name)
      "Cancel" button (top-right, ghost)

  [2] InstructionStrip (fixed bottom, 80px + safe area):
      Background: var(--color-bg-surface) + backdrop-blur
      Direction arrow icon (rotates per instruction: ↑ ↗ → ↘ ↓)
      Current instruction: "Continue north on MM Alam Road" (bold 16px white)
      Next instruction: "In 100m, turn right" (secondary 13px)

  [3] VendorMiniCard (fixed, just below header, 56px):
      Vendor thumbnail (40px) + name + active promotion badge
      Tappable → expands to full vendor info (height animates to 200px)
```

### 18.3 Arrival Detection & Overlay

```
Client-side: useGeofence hook watches user position continuously
  When distance to destination < 30m → arrival detected

ArrivalOverlay (Framer Motion scale spring):
  Full-screen dark modal (rgba(0,0,0,0.85))
  AnimatedCheckmark SVG (Framer Motion pathLength 0→1, 400ms, brand teal stroke)
  "You've arrived at [Business Name]! 🎉" (bold 22px centered)
  
  Active promotion card (if active_promotion !== null):
    Same design as vendor profile Section 1 promotion card (compact)
    "Show this at checkout" helper text (13px secondary)
  
  3 action buttons (stacked):
    "🔍 Find Another Place" (secondary) → /discover
    "View Full Profile" (ghost) → /vendor/:id
    "Done" (ghost) → back to previous screen

Tracking: POST /track/interaction/ {type: 'ARRIVAL'} on arrival detection
```

---

## 19. USER PREFERENCES PAGE

### 19.1 Access Rules

```
Route: /preferences (also accessible via "Me 👤" bottom nav tab)

Guest access:
  Can access: theme, default view, search radius settings
  Cannot access: notification preferences (inline prompt to sign in)
  No redirect — stays on page with limited UI
  
Logged-in access: full page, all settings
```

### 19.2 Page Layout

```
Clean list view — no card wrappers on settings items (minimal visual noise)
Section dividers: 1px var(--brand-gradient) line + section title above
No nested navigation — everything on one scrollable page
  On change: updates discoveryStore.showOpenNowOnly → immediate refetch in active view

Default Category:
  Native <select> styled as dropdown
  "All Categories" (default) + full tag list
```

### 19.4 Notification Preferences (Logged-In Only)

```
If guest: entire section replaced with:
  Card (var(--color-bg-elevated)):
    "🔔 Notification Preferences"
    "Sign in to enable deal alerts and vendor updates."
    "Sign In →" button (primary, compact) | "Register Free →" (ghost, compact)
  No redirect — inline prompt

If logged-in:
  Master "All Notifications Off" toggle (top of section)
    When on: remaining toggles greyed + cursor: not-allowed

  Individual toggles (each with description):
    "Nearby Deals Alerts" — "Get alerted when you're near an active deal"
    "Flash Deal Alerts" — "Be first to know about limited-time flash deals"
    "Vendor Updates" — "Updates from vendors you've visited"
  
  All toggle changes: immediate PUT /preferences/ (debounced 1000ms)
```

### 19.5 Appearance Section

```
Theme:
  3-option segmented control: "🌙 Dark" | "☀️ Light" | "⚙️ System"
  On change: immediate DOM update (setAttribute 'data-theme') + localStorage
  
Language (Phase-1 — visual only):
  Shows "English" — greyed, tooltip: "More languages coming soon"
```

### 19.6 Privacy & Data Section

```
"What data we collect" — expandable section (Framer Motion height animation):
  Expanded content (4 plain-language bullets, no legalese):
    "📍 Your GPS location (only when app is open)"
    "🔍 What you search for (to improve suggestions)"
    "🏪 Which vendors you visit (to improve discovery)"
    "❌ Nothing else. No camera feed, no personal information."

"Clear my search history" — ListItem with danger TextButton
  On tap: AlertDialog "Are you sure? Your 24 recent searches will be deleted."
  On confirm: DELETE /preferences/search-history/ → 204 → success toast

"Delete my account" (logged-in only) — ListItem with danger TextButton
  On tap: AlertDialog with TextInput "Type 'DELETE' to confirm"
  Input validation before "Confirm" button enables
  On confirm: flow (confirmation code email → DELETE /auth/account/) → logout → landing

"Export my data" (logged-in only) — ListItem with download icon
  On tap: GET /auth/account/export/ → triggers download via blob URL
  Success toast: "Your data export is ready."
```

### 19.7 About Section

```
App version: "AirAds User Portal v1.0.0" (13px tertiary)
"For Vendors →" — opens vendor portal URL in new tab
"Privacy Policy" — opens external link
"Terms of Service" — opens external link
```

---

## 20. RESPONSIVE DESIGN STRATEGY

### 20.1 Breakpoints

```css
/* Consistent with existing portals */
--bp-sm:  375px   /* Small mobile */
--bp-md:  768px   /* Tablet threshold */
--bp-lg:  1024px  /* Desktop threshold */
--bp-xl:  1280px  /* Wide desktop */
```

### 20.2 Layout Behavior Per Breakpoint

| Component | Mobile (< 768px) | Tablet (768-1024px) | Desktop (> 1024px) |
|---|---|---|---|
| Discovery shell | Full-screen, bottom nav | Full-screen, bottom nav | Top nav, no bottom nav |
| AR View | Full-screen camera | Full-screen camera | Simulated AR |
| Map View | Full-screen, bottom sheet on tap | Full-screen, side sheet | Split: map + panel |
| List View | 1 column | 2 columns | 3 columns max |
| Vendor Profile | Full-screen scroll | Full-screen scroll | Split: detail left, map right |
| Tag Browser | Bottom sheet | Bottom sheet | Right panel (persistent) |
| Voice overlay | Full-screen | Centered modal | Centered modal |
| Landing hero bar | 90vw | 80vw | min(680px, 70vw) |
| Phone mockup slider | 240px wide | 280px wide | 320px wide |
| Social proof stats | Vertical stack | Horizontal | Horizontal |

### 20.3 Touch Target Rule (Non-Negotiable)

All interactive elements: **minimum 44×44px** (WCAG 2.5.5).
AR markers: minimum tap area 44×44px via padding + CSS click-area expansion.
Bottom navigation tabs: each tab area = screen width / 5, minimum 60px height.

### 20.4 No Horizontal Scroll Rule

```css
/* Applied globally */
body { overflow-x: hidden; }
```

Only exceptions: horizontal scroll *inside* explicitly scrollable containers (promotions strip, vendor thumbnail grid, tag chip rows). These containers: `overflow-x: auto`, parent clips them with `overflow: hidden`.

---

## 20A. ERROR BOUNDARY STRATEGY

> **[AUDIT FIX — CRITICAL 3.1]** Without error boundaries, any unhandled exception in React renders a blank white screen. Branded error recovery required for all views.

### Global Error Boundary

```typescript
// src/components/ErrorBoundary.tsx — class component (required for React error boundaries)
class ErrorBoundary extends React.Component<Props, {hasError: boolean; error: Error | null}> {
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Fire-and-forget error report (Sentry or equivalent)
    reportError(error, info);
  }
  render() {
    if (this.state.hasError) return <ErrorFallback error={this.state.error} onRetry={() => this.setState({hasError: false, error: null})} />;
    return this.props.children;
  }
}
```

**`ErrorFallback` component:**
```
Background: var(--color-bg-page)
Center column (max-width: 320px, centered vertically):
  AirAds logo (60px, opacity 0.8)
  "Something went wrong" (bold 20px, --color-text-primary)
  "We're looking into it. Tap to try again." (15px secondary)
  "Try Again" button (primary gradient, 48px, calls onRetry)
  "Go Home" ghost button → navigate('/')
```

**Route-level error boundaries:**
Each `React.lazy()` page wrapped in its OWN `<ErrorBoundary>` — so AR crash does not kill the whole app:
```typescript
<ErrorBoundary key="ar">
  <Suspense fallback={<ARSkeleton />}>
    <ARView />
  </Suspense>
</ErrorBoundary>
```

**AR-specific recovery:**
If ARView throws (camera API crash): error boundary catches it → shows branded fallback → auto-switches to Simulated AR mode after 1.5s.

Add `ErrorBoundary` to project structure in `src/components/dls/ErrorBoundary/`.

---

## 20B. GPS ACCURACY & EDGE CASES

> **[AUDIT FIX — HIGH 3.4]** Real-world GPS is not always clean. Plans must specify handling for inaccurate, bouncing, and cold-start GPS.

```typescript
// In useLocation.ts:

// 1. Accuracy threshold: discard positions with accuracy > 100m
navigator.geolocation.watchPosition(
  (pos) => {
    if (pos.coords.accuracy > 100) return; // discard inaccurate fix
    updatePosition(pos.coords.latitude, pos.coords.longitude);
  },
  onError,
  { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 }
);

// 2. GPS smoothing: exponential moving average (prevents teleporting markers)
const SMOOTHING = 0.3;
newLat = prevLat + SMOOTHING * (rawLat - prevLat);
newLng = prevLng + SMOOTHING * (rawLng - prevLng);

// 3. Cold GPS start timeout:
if (no fix within 10 seconds) {
  // Show CityPickerModal — let user pick area manually
  // Continue trying GPS in background
}

// 4. IP geolocation fallback (city-level only, not precise):
if (GPS_denied AND no area selected) {
  fetch('https://ipapi.co/json/').then(r => {
    discoveryStore.setAreaName(r.city);
    // Use approximate city center coordinates for discovery
    // Add " (approximate)" label to LocationContext display
  });
}
```

---

## 20C. HTTP 429 RATE-LIMIT UX

> **[AUDIT FIX — HIGH 3.5]** When discovery API rate limit is hit (60 req/min), users see a spinner that never resolves. Explicit 429 handling required.

```typescript
// In src/api/client.ts — Axios response interceptor:
if (error.response?.status === 429) {
  const retryAfter = parseInt(error.response.headers['retry-after'] || '10', 10);
  // Show toast: "Searching too fast — please wait Xs" with countdown
  uiStore.addToast({
    type: 'warning',
    message: `Slow down! Try again in ${retryAfter}s.`,
    duration: retryAfter * 1000,
  });
  // Do NOT retry automatically — let user trigger manually
  return Promise.reject(new RateLimitError(retryAfter));
}
```

RateLimitError caught by TanStack Query `onError` → discovery views show:
```
InfoCard: "You're searching too quickly."
CountdownTimer: "Try again in [Xs]" (counts down from retry-after)
Auto-refetch: triggered when countdown reaches 0 (useEffect + setInterval)
```

---

## 20D. OFFLINE FIRST-LOAD (EMPTY CACHE)

> **[AUDIT FIX — HIGH 3.8]** Current offline plan assumes "was previously online, now offline." Truly first load with no connection must also be handled.

```typescript
// In src/main.tsx — startup connectivity check:
const isOnline = navigator.onLine;
if (!isOnline) {
  // Before React even mounts: render static offline shell
  // This requires a service worker with offline fallback page
}
```

**Service Worker (offline first-load):**
```javascript
// public/sw.js — minimal service worker
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open('airad-shell-v1').then(cache =>
    cache.addAll(['/index.html', '/styles/dls-tokens.css', '/airad_icon.png'])
  ));
});

self.addEventListener('fetch', (e) => {
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request).catch(() => caches.match('/index.html'))
    );
  }
});
```

Register in `main.tsx`:
```typescript
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}
```

**When app loads offline with empty TanStack cache:**
```
Discovery page shows:
  OfflineBanner (top — slides in from top)
  "Offline — no cached data" state (distinct from the normal offline-with-cache state):
    AirAds logo (80px, opacity 0.15) centered
    "Connect to internet to discover vendors nearby"
    "Retry" button → window.location.reload()
  NO skeleton loaders (no data to expect)
```

Add `sw.js` to project structure in `public/sw.js`.

---

## 20E. GDPR CONSENT BANNER (FIRST USE)

> **[AUDIT FIX — HIGH 3.10]** Data collection requires informed consent on first use.

```
ConsentBanner component:
  Trigger: localStorage.getItem('consent_v1') === null (first visit)
  Position: fixed bottom: 0, full width, z-index: 200
  Background: var(--color-bg-elevated), top border: 1px brand gradient
  Padding: 16px 20px
  Framer Motion: y: 100 → 0 (slides up, 300ms smooth)
  
  Content:
    "AirAds uses your location to show nearby vendors."
    "We also collect anonymous usage patterns to improve discovery."
    Link: "Read our Privacy Policy"
  
  Two buttons (right-aligned, gap: 8px):
    "Essential Only" (ghost, md) — records LOCATION=true, ANALYTICS=false
    "Accept All" (primary gradient, md) — records all consent types
  
  On either action:
    localStorage.setItem('consent_v1', JSON.stringify({accepted: true, timestamp: Date.now()}))
    POST /api/v1/user-portal/auth/consent/ for each type
    Banner slides down (Framer Motion exit)
  
  Cannot be dismissed without choosing — no X button
  prefers-reduced-motion: no slide animation, appears instantly
```

Add `ConsentBanner` to `src/components/dls/ConsentBanner/`.
Mount in root `App.tsx` / `main.tsx` — always present until consent recorded.

---

## 20F. DEPLOYMENT CONFIGURATION

> **[AUDIT FIX — HIGH 1.22]** React Router requires all routes to serve `index.html` on direct URL access. Without this, `/vendor/uuid` returns 404 on Netlify/Vercel.

**Netlify (`public/_redirects`):**
```
/* /index.html 200
```

**Vercel (`vercel.json` in project root):**
```json
{
  "rewrites": [{"source": "/(.*)", "destination": "/index.html"}]
}
```

**Also required — SEO meta tags in `index.html`:**
```html
<head>
  <title>AirAds — Discover What's Near You</title>
  <meta name="description" content="Point your camera. Speak your craving. Discover nearby vendors in real-time with AirAds AR discovery." />
  <meta property="og:title" content="AirAds — Discover What's Near You" />
  <meta property="og:description" content="AR-first vendor discovery. Find food, shops, and deals near you instantly." />
  <meta property="og:image" content="https://app.airad.pk/og-preview.png" />
  <meta property="og:url" content="https://app.airad.pk" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="canonical" href="https://app.airad.pk" />
</head>
```

Add `_redirects` and `vercel.json` to project structure in `public/` and root respectively.

---

## 20G. MAPBOX TOKEN SECURITY

> **[AUDIT FIX — HIGH 3.6]** `VITE_MAPBOX_TOKEN` is embedded in the built JS bundle and visible to anyone. An unrestricted token gets abused leading to unexpected billing.

**Required action before deployment:**
1. In Mapbox account → Access Tokens → create a token with **URL restrictions**: `https://app.airad.pk`
2. Set `Allowed URLs` to only `https://app.airad.pk` and `http://localhost:5173` (dev)
3. Never use the default public token — always use a URL-restricted token
4. Rotate token if it appears in git history

Add to `.env.example`:
```
# IMPORTANT: This token MUST be URL-restricted in Mapbox account
# Allowed URLs: https://app.airad.pk, http://localhost:5173
# See: https://docs.mapbox.com/accounts/guides/tokens/
VITE_MAPBOX_TOKEN=pk.eyJ1...
```

---

## 20H. AR LOW-END DEVICE DEGRADATION

> **[AUDIT FIX — HIGH 3.14]** AR is the signature feature but glassmorphism + Framer Motion + 15 markers simultaneously will jank on low-end Android devices (dominant target market).

```typescript
// In useAR.ts — device capability detection:
const getDeviceTier = (): 'HIGH' | 'MID' | 'LOW' => {
  const memory = (navigator as any).deviceMemory; // GB (Chrome only)
  const cores = navigator.hardwareConcurrency || 2;
  if (memory >= 4 && cores >= 6) return 'HIGH';
  if (memory >= 2 && cores >= 4) return 'MID';
  return 'LOW';
};
```

Progressive AR quality rules:
| Device Tier | Max Markers | Backdrop-Filter | Framer Motion | Float Animation |
|---|---|---|---|---|
| HIGH | 15 | enabled (blur 12px) | full spring | enabled |
| MID | 10 | enabled (blur 6px) | opacity only | enabled |
| LOW | 6 | disabled (solid bg fallback) | none (CSS transitions) | disabled |

Implementation:
```typescript
// ARMarker.tsx — apply tier-based classes
<div
  className={cx(
    styles.marker,
    deviceTier === 'LOW' && styles.markerNoBlur,
    deviceTier === 'LOW' && styles.markerSolid
  )}
/>
```

Low-end solid bg fallback: `background: rgba(20, 20, 20, 0.95)` (no backdrop-filter).
This is undetectable by most users — glass effect is nice-to-have, not core UX.

---

## 21. PERFORMANCE TARGETS & OPTIMIZATION

### 21.1 Core Performance Metrics (From Requirements)

> **[AUDIT FIX — CRITICAL]** Master prompt specifies exact performance targets: Lighthouse 90+, 2s load, 60fps AR. These must be explicitly implemented and monitored.

### Target Metrics

**Lighthouse Performance Score: 90+**
- **Performance Budget:** < 2s initial load (FCP, LCP)
- **Accessibility Score:** 95+ (WCAG 2.1 AA)
- **Best Practices:** 90+
- **SEO:** 95+

**Load Time Targets:**
- **First Contentful Paint (FCP):** < 1.5s
- **Largest Contentful Paint (LCP):** < 2.0s
- **Time to Interactive (TTI):** < 3.5s
- **Cumulative Layout Shift (CLS):** < 0.1

**AR Performance: 60fps**
- **Camera feed:** 60fps on supported devices
- **Marker animations:** 60fps smooth transitions
- **Motion effects:** Respect `prefers-reduced-motion`

### 21.2 Performance Monitoring Implementation

```typescript
// In src/utils/performanceMonitor.ts
class PerformanceMonitor {
  private metrics: Map<string, number> = new Map();
  
  // Core Web Vitals monitoring
  measureLCP() {
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const lastEntry = entries[entries.length - 1];
      this.metrics.set('LCP', lastEntry.startTime);
      
      // Alert if LCP > 2s
      if (lastEntry.startTime > 2000) {
        this.reportPerformanceIssue('LCP', lastEntry.startTime);
      }
    }).observe({ entryTypes: ['largest-contentful-paint'] });
  }
  
  measureFID() {
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      entries.forEach((entry) => {
        this.metrics.set('FID', entry.processingStart - entry.startTime);
        
        // Alert if FID > 100ms
        if (entry.processingStart - entry.startTime > 100) {
          this.reportPerformanceIssue('FID', entry.processingStart - entry.startTime);
        }
      });
    }).observe({ entryTypes: ['first-input'] });
  }
  
  measureCLS() {
    let clsValue = 0;
    new PerformanceObserver((list) => {
      list.getEntries().forEach((entry) => {
        if (!(entry as any).hadRecentInput) {
          clsValue += (entry as any).value;
          this.metrics.set('CLS', clsValue);
          
          // Alert if CLS > 0.1
          if (clsValue > 0.1) {
            this.reportPerformanceIssue('CLS', clsValue);
          }
        }
      });
    }).observe({ entryTypes: ['layout-shift'] });
  }
  
  // AR FPS monitoring
  measureARFPS() {
    let frameCount = 0;
    let lastTime = performance.now();
    
    const measureFrame = () => {
      frameCount++;
      const currentTime = performance.now();
      
      if (currentTime - lastTime >= 1000) {
        const fps = frameCount;
        this.metrics.set('AR_FPS', fps);
        
        // Alert if FPS < 55
        if (fps < 55) {
          this.reportPerformanceIssue('AR_FPS', fps);
        }
        
        frameCount = 0;
        lastTime = currentTime;
      }
      
      requestAnimationFrame(measureFrame);
    };
    
    requestAnimationFrame(measureFrame);
  }
  
  private reportPerformanceIssue(metric: string, value: number) {
    // Send to monitoring service
    console.warn(`Performance issue: ${metric} = ${value}`);
    
    // Could send to Sentry, DataDog, etc.
    if (window.Sentry) {
      window.Sentry.captureMessage(`Performance issue: ${metric} = ${value}`, 'warning');
    }
  }
}

// Initialize monitoring
const performanceMonitor = new PerformanceMonitor();
performanceMonitor.measureLCP();
performanceMonitor.measureFID();
performanceMonitor.measureCLS();
```

### 21.3 Performance Budget Enforcement

```typescript
// In vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          ui: ['framer-motion', 'zustand'],
          maps: ['mapbox-gl'],
          ar: ['@ar-js/api'] // AR libraries chunked separately
        }
      }
    },
    chunkSizeWarningLimit: 1000 // Warn if chunks > 1MB
  },
  plugins: [
    // Performance budget plugin
    {
      name: 'performance-budget',
      generateBundle(options, bundle) {
        const totalSize = Object.values(bundle).reduce((acc, chunk) => 
          acc + (chunk.type === 'chunk' ? chunk.code.length : 0), 0);
        
        if (totalSize > 1024 * 1024) { // 1MB
          this.warn(`Bundle size ${Math.round(totalSize / 1024)}KB exceeds budget`);
        }
      }
    }
  ]
});
```

### 21.4 Optimization Strategies

**Image Optimization:**
- WebP format with fallbacks
- Lazy loading with IntersectionObserver
- Responsive images with srcset
- Compression: < 200KB per image

**Code Splitting:**
- Route-based splitting with React.lazy
- Feature-based splitting for AR components
- Dynamic imports for heavy libraries

**Caching Strategy:**
- Service Worker for static assets (1 year cache)
- API response caching with TanStack Query
- Browser storage for user preferences

---

## 22. ACCESSIBILITY REQUIREMENTS (WCAG 2.1 AA)

> **[AUDIT FIX — CRITICAL]** Master prompt requires WCAG compliance. This section ensures full accessibility implementation beyond basic touch targets.

### 22.1 WCAG 2.1 AA Compliance Checklist

**Perceivable (1.4)**
- **Color Contrast:** All text meets 4.5:1 contrast ratio
- **Text Resize:** 200% zoom remains functional
- **Audio Content:** Captions provided for all audio
- **Keyboard Focus:** Visible focus indicators on all interactive elements

**Operable (2.1)**
- **Keyboard Access:** Full keyboard navigation
- **No Keyboard Traps:** Focus can move in and out of all components
- **Timing:** Users can disable time limits
- **Motion Animation:** Respect `prefers-reduced-motion`

**Understandable (3.1)**
- **Readable Text:** Language identified, reading level appropriate
- **Predictable:** Navigation is consistent
- **Input Assistance:** Error identification and suggestions

**Robust (4.1)**
- **Compatible:** Works with assistive technologies
- **ARIA Roles:** Proper semantic markup

### 22.2 Implementation Details

**Focus Management:**
```typescript
// In src/hooks/useFocusManagement.ts
export const useFocusManagement = () => {
  const trapFocus = (container: HTMLElement) => {
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;
    
    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement.focus();
            e.preventDefault();
          }
        }
      }
    };
    
    container.addEventListener('keydown', handleTabKey);
    firstElement.focus();
    
    return () => container.removeEventListener('keydown', handleTabKey);
  };
  
  return { trapFocus };
};
```

**Screen Reader Support:**
```typescript
// In src/components/ARMarker.tsx
export const ARMarker: React.FC<ARMarkerProps> = ({ vendor, onSelect }) => {
  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${vendor.name}, ${vendor.category}, ${vendor.distance} meters away${vendor.hasActivePromotion ? ', has active promotion' : ''}`}
      aria-describedby={`vendor-${vendor.id}-details`}
      onClick={() => onSelect(vendor)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          onSelect(vendor);
        }
      }}
    >
      {/* Marker content */}
      <div id={`vendor-${vendor.id}-details`} className="sr-only">
        {vendor.description}
      </div>
    </div>
  );
};
```

**Reduced Motion Support:**
```css
/* In src/styles/accessibility.css */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  
  /* Disable parallax effects */
  .parallax-container {
    transform: none !important;
  }
  
  /* Disable pulsing animations */
  .pulse-animation {
    animation: none !important;
  }
}
```

**Color Contrast Implementation:**
```css
/* In src/styles/colors.css */
:root {
  /* High contrast colors for WCAG compliance */
  --text-primary: #000000; /* 21:1 contrast on white */
  --text-secondary: #595959; /* 7:1 contrast on white */
  --text-tertiary: #767676; /* 4.5:1 contrast on white */
  
  /* Brand colors with sufficient contrast */
  --brand-orange: #FF8C00; /* 3.1:1 contrast on white - needs enhancement */
  --brand-orange-text: #000000; /* Use black text on orange */
  
  /* Ensure all interactive elements meet contrast */
  .button-primary {
    background: var(--brand-orange);
    color: #000000; /* High contrast text */
  }
  
  .button-secondary {
    background: transparent;
    color: var(--brand-orange);
    border: 2px solid var(--brand-orange);
  }
}
```

### 22.3 Accessibility Testing

```typescript
// In src/utils/accessibilityTester.ts
export const runAccessibilityTests = () => {
  // Test color contrast
  const testContrast = (element: HTMLElement) => {
    const styles = window.getComputedStyle(element);
    const color = styles.color;
    const backgroundColor = styles.backgroundColor;
    
    // Use contrast calculation library
    const contrast = getContrastRatio(color, backgroundColor);
    
    if (contrast < 4.5) {
      console.warn(`Low contrast detected: ${contrast}:1`, element);
    }
  };
  
  // Test keyboard accessibility
  const testKeyboardAccess = () => {
    const interactiveElements = document.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    interactiveElements.forEach((element) => {
      if (!element.hasAttribute('aria-label') && 
          !element.hasAttribute('aria-labelledby') &&
          !(element as HTMLElement).textContent) {
        console.warn('Missing accessible label:', element);
      }
    });
  };
  
  // Run tests
  document.querySelectorAll('*').forEach(testContrast);
  testKeyboardAccess();
};
```

### 22.4 ARIA Implementation

**Landmark Roles:**
```html
<!-- Page structure with landmarks -->
<header role="banner">
  <nav role="navigation" aria-label="Main navigation">
    <!-- Navigation content -->
  </nav>
</header>

<main role="main">
  <section aria-labelledby="discovery-heading">
    <h1 id="discovery-heading">Discover Nearby Vendors</h1>
    <!-- Discovery content -->
  </section>
</main>

<aside role="complementary" aria-label="Filters">
  <!-- Filter content -->
</aside>

<footer role="contentinfo">
  <!-- Footer content -->
</footer>
```

**Live Regions:**
```typescript
// In src/components/LiveRegion.tsx
export const LiveRegion: React.FC<{ message: string }> = ({ message }) => {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="sr-only"
    >
      {message}
    </div>
  );
};

// Usage in search results
const [searchStatus, setSearchStatus] = useState('');
<LiveRegion message={`Found ${results.length} vendors`} />
```

---

## 23. PERFORMANCE TARGETS & OPTIMIZATION

### 21.1 Lighthouse Score Targets

| Metric | Target |
|---|---|
| Performance | ≥ 90 |
| Accessibility | ≥ 90 |
| Best Practices | ≥ 90 |
| SEO (Landing Page) | ≥ 85 |
| LCP | < 2.5s |
| INP | < 200ms |
| CLS | < 0.10 |

### 21.2 Bundle Splitting Strategy

```
Vite chunk strategy (vite.config.ts manualChunks):
  landing/    → separate chunk (~80-100KB gzipped)
  ar/         → separate chunk (device API wrappers)
  mapbox/     → separate chunk (~600KB gzipped, on-demand only)
  auth/       → small shared chunk
  preferences → small chunk
  vendor-*    → grouped discovery chunk
  
All pages: React.lazy() + Suspense (skeleton fallback per page shape)
```

### 21.3 Animation Performance Rules

- All CSS animations: `transform` + `opacity` ONLY — never `width`, `height`, `top`, `left`
- Framer Motion variants: defined as constants outside component functions (no re-creation on render)
- AR markers: `will-change: transform` applied (GPU layer promotion)
- `requestAnimationFrame` for AR compass rotation updates — never `setInterval`
- `prefers-reduced-motion` media query: all animations have static fallback state

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

### 21.4 Image Optimization

- All vendor thumbnails: `loading="lazy"` attribute
- Vendor cover images on profile page: `fetchpriority="high"` (above fold)
- Mapbox static images: CDN-served, no local download
- Zero external image assets on landing page

### 21.5 TanStack Query Optimization

Aggressive `staleTime` to prevent unnecessary re-fetches:
- AR markers: `staleTime: 0` (always re-validate, `refetchInterval: 5000`)
- Nearby vendors: `staleTime: 15000`, `refetchInterval: 30000`
- Vendor detail: `staleTime: 300000` (5 min)
- Tags: `staleTime: 120000` (2 min)
- Deals: `staleTime: 0`, `refetchInterval: 60000`

Background refetch on window focus: enabled for AR markers and deals only.

### 21.6 Crash Reporting Integration

> **[AUDIT FIX — HIGH 3.2]** Without crash reporting, production bugs are invisible.

```typescript
// In src/main.tsx — Sentry initialization (before React mount):
import * as Sentry from '@sentry/react';

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,  // from .env
  environment: import.meta.env.MODE,
  tracesSampleRate: 0.1,  // 10% performance traces
  beforeSend(event) {
    // Strip any PII before sending
    delete event.user?.email;
    delete event.user?.ip_address;
    return event;
  },
});
```

Add `VITE_SENTRY_DSN` to `.env.example`. Add `@sentry/react` to `package.json`.
Captures: unhandled React errors (via ErrorBoundary `componentDidCatch`), unhandled promise rejections, network errors above threshold.

---

## 22. ACCESSIBILITY REQUIREMENTS

### 22.1 WCAG AA Compliance (Non-Negotiable)

Color contrast:
- All text on brand orange backgrounds: minimum 4.5:1 ratio — verified at design time
- AR marker text on glassmorphism: minimum 4.5:1 against average glass background
- White text on crimson/orange: verified ✓
- High contrast mode (System preference): respected automatically via CSS `prefers-contrast`

### 22.2 Keyboard Navigation

- Full tab order: landing → navbar → search bar → CTA → page sections
- Discovery: Tab moves through visible vendor cards in logical order
- AR markers: keyboard-focusable (tabIndex=0), Enter/Space to expand
- All modals: focus trapped inside (focus-trap-react or manual implementation)
- Escape key: closes all modals, overlays, bottom sheets
- All custom controls (ViewSwitcher, TagChips, slider): keyboard-operable with arrow keys

### 22.3 Screen Reader Support

- All interactive elements: meaningful `aria-label` attributes
- AR view: `aria-live="polite"` region announces "12 vendors found nearby"
- Voice listening state: `aria-live="assertive"` announces "Listening" → "Searching"
- Countdown timers: `aria-live="polite"` — updates without interrupting reading flow
- Dynamic content: `aria-atomic`, `aria-relevant` applied appropriately

### 22.4 Focus Management

- On modal open: focus moves to first interactive element inside modal
- On modal close: focus returns to trigger element
- On route change: focus moves to page `<h1>` (useEffect in router)
- Skip-to-main-content: `<a href="#main-content">Skip to main content</a>` at top of every page (matches existing portal pattern)

---

## 23. GUEST VS LOGGED-IN MODE DIFFERENCES

### 23.1 Feature Matrix

| Feature | Guest Mode | Logged-In Mode |
|---|---|---|
| Discovery (AR/Map/List) | ✅ Full access | ✅ Full access |
| Voice Search | ✅ Full access | ✅ Full access |
| Tag Browsing | ✅ Full access | ✅ Full access |
| Vendor Profiles | ✅ Full access | ✅ Full access |
| Deals Tab | ✅ Full access | ✅ Full access |
| Reels Feed | ✅ Full access | ✅ Full access |
| Navigation | ✅ Full access | ✅ Full access |
| Vendor Voice Bot | ✅ Full access | ✅ Full access |
| Preferences (theme, view, radius) | ✅ | ✅ |
| Notification preferences | ❌ Inline sign-in prompt | ✅ Full |
| Search history sync | Local sessionStorage only | ✅ Server-synced |
| Account deletion | ❌ N/A | ✅ GDPR flow |
| Data export | ❌ N/A | ✅ JSON download |

### 23.2 Guest UI Indicators

```
Avatar area ("Me 👤" bottom tab or top-right):
  Guest: generic person icon
  On tap: opens preferences page with non-intrusive sign-in callout at top

Logged-in:
  Avatar: 32×32px circle, DM Sans Bold initial letter, brand orange bg
  "Hi, [First Name]" subtitle (15px secondary, one line)

Rule: Login is NEVER forced. Guest user is never blocked, redirected unexpectedly,
      or shown intrusive modals demanding sign-up.
```

---

## 24. BUILD SEQUENCE & SESSIONS

| Session | Content | Est. Time |
|---|---|---|
| UP-FE-S1 | Project setup: `airaad/user-portal/`, package.json, tsconfig, vite.config, DLS tokens CSS, global CSS, animations CSS, Zustand stores, Axios client, router skeleton | 2-3h |
| UP-FE-S2 | All DLS components: Button, SearchBar, TagChip, SkeletonLoader, Toast, VoiceWave, DistanceBadge, PromotionBadge, TierBadge, Logo, CountdownTimer, OfflineBanner | 2-3h |
| UP-FE-S3 | All API client files, all hooks (useLocation, useAR, useVoice, useGeofence, useOffline), all utility files (formatters, geo, nlp, constants) | 1.5h |
| UP-FE-S4 | Landing page: all 7 sections (Navbar, Hero, Phone Slider x4, Three Modes, Social Proof, CTA, Footer) — full animations, mobile responsive | 3-4h |
| UP-FE-S5 | Auth: LoginPage (two-panel, guest mode, form validation), RegisterPage (strength indicator, success screen), returnTo handling | 1.5h |
| UP-FE-S6 | Discovery shell: DiscoveryPage, sticky header, ViewSwitcher, LocationContext, PromotionsStrip, bottom nav, location permission flow, empty states, offline state | 2-3h |
| UP-FE-S7 | AR View: mode detection (real vs simulated), ARCanvas, ARMarker (collapse/expand), ARCluster, ARCompass, ARRadiusSlider, WalkingSafetyOverlay | 3-4h |
| UP-FE-S8 | Map View: Mapbox integration, vendor pins by tier, promotion rings, filter bar, bottom sheet/side panel on tap | 2-3h |
| UP-FE-S9 | List View: infinite scroll, sort control, VendorCard, VendorCardSkeleton, pull-to-refresh, empty states | 1.5h |
| UP-FE-S10 | Voice Search UI: listening overlay, transcript reveal, error states, suggestions, VoiceBotSheet | 2h |
| UP-FE-S11 | Tag Browser: 4 sections, multi-select state, live count preview, bottom sheet / right panel | 1.5h |
| UP-FE-S12 | Vendor Profile: all 6 sections, parallax cover, promotion card countdown, reels scroll, location map, voice bot, more nearby, FAB | 3h |
| UP-FE-S13 | Deals page: deal cards, urgency system (3 levels), flash deal toast, expired animation | 2h |
| UP-FE-S14 | Reels page: full-screen vertical scroll-snap feed, video player, overlays, view tracking | 2h |
| UP-FE-S15 | Navigation: NavigationPage, in-app Mapbox directions, ArrivalOverlay, deep-link routing | 2h |
| UP-FE-S16 | Preferences: all 5 sections, guest vs logged-in, GDPR flows, theme switching | 1.5h |
| UP-FE-S17 | Final QA: all error states, all empty states, all loading states, `tsc --noEmit` = 0, `vite build` success, Lighthouse verify | 2h |

**Total: 17 sessions, 35-45 hours**

---

## 25. QUALITY GATE CHECKLIST

### Design System
- [ ] Zero hardcoded hex colors in any component or CSS module file
- [ ] All colors via `var(--token-name)` CSS custom properties
- [ ] Dark theme: all components visually correct (test with data-theme="dark")
- [ ] Light theme: all components visually correct (test with data-theme="light")
- [ ] DM Sans font applied globally — no system fonts visible anywhere
- [ ] All spacing values: multiples of 4px minimum, 8px standard

### Landing Page
- [ ] WOW test: core value communicated within 3 seconds of load
- [ ] 4-slide phone mockup: auto-plays, crossfades, loops, swipe works
- [ ] Hero search bar: hover + focus glow animations visible
- [ ] Quick tags navigate to /discover with correct filter pre-selected
- [ ] All animations respect `prefers-reduced-motion`
- [ ] Lighthouse Performance ≥ 90, LCP < 2.5s

### Discovery & AR
- [ ] AR mode detection: real camera vs simulated — seamless (no "detection" screen shown)
- [ ] AR markers: render correctly, float animation, tap to expand, action buttons work
- [ ] Cluster: groups when 3+ vendors within 8° bearing, expands on tap
- [ ] Walking safety overlay: triggers on motion, auto-dismisses in 3s
- [ ] View switcher: AR → Map → List — instant, smooth, discoveryStore state preserved
- [ ] Promotions strip: shows when active, hides when none (animated)
- [ ] Location permission: pre-prompt explanation before system dialog

### Voice Search
- [ ] Global voice: mic tap → listen → transcript word-by-word → results — full E2E
- [ ] Mic denied: graceful fallback to text input (no crash)
- [ ] Vendor voice bot: visible only on Gold+ vendors
- [ ] TTS: plays response audio, mute toggle works, Escape closes sheet

### Map & List
- [ ] Map loads centered on user GPS (or fallback city center if denied)
- [ ] Pins colored correctly per tier (Silver/Gold/Diamond/Platinum)
- [ ] Promotion pins: pulsing ring visible
- [ ] Pin tap: sheet/panel opens correctly on mobile and desktop
- [ ] Infinite scroll: loads more on scroll, skeleton while loading
- [ ] Pull-to-refresh: triggers on mobile

### Vendor Profile
- [ ] All 6 sections load and display correctly
- [ ] CountdownTimer counts in real-time (accurate to second)
- [ ] Reels section hidden when reels_count === 0
- [ ] Voice bot section hidden for Silver vendors
- [ ] FAB hides when Location section is visible (IntersectionObserver)
- [ ] Share button: Web Share API works (fallback clipboard copy)

### Deals & Reels
- [ ] Urgency color system: normal → amber → crimson — color changes at correct thresholds
- [ ] Flash deal toast: appears, auto-dismisses in 8s, never repeats same deal
- [ ] Expired deals: silently removed (no "expired" screen)
- [ ] Reels video: autoplay muted, tap to pause/unmute
- [ ] Reel view tracking: fires on exit from viewport

### Navigation & Preferences
- [ ] Platform-specific deep links: Google Maps / Apple Maps / web fallback — all work
- [ ] Arrival: detected at 30m, overlay appears, promotion shown if active
- [ ] Preferences: all settings save immediately (or debounced for sliders)
- [ ] Guest: notification section shows sign-in prompt (no redirect)
- [ ] Account deletion: GDPR flow complete (code → confirm → logout → landing)

### Technical Quality
- [ ] `tsc --noEmit` = 0 errors
- [ ] `vite build` = success (no TypeScript errors, no build failures)
- [ ] Zero `console.log` in production build
- [ ] Zero `any` type annotations
- [ ] Zero hardcoded hex in CSS modules
- [ ] Zero inline `style={}` in JSX
- [ ] WCAG AA: 4.5:1 contrast verified on all text
- [ ] All touch targets ≥ 44×44px
- [ ] No horizontal scroll at any breakpoint on any page

### Audit Fixes Verification
- [ ] Token refresh: concurrent 401s deduplicated — only ONE `doRefresh()` called (verify with mock interceptor test)
- [ ] HTTP 429: `Retry-After` header parsed → SnackBar countdown shown, request not retried automatically
- [ ] Promotions strip: uses `GET /discovery/promotions-strip/` (NOT flash-alert), separate query key
- [ ] City picker: opens when location denied/timeout, area tap → discoveryStore updated, results refetch
- [ ] Voice Safari fallback: `webkitSpeechRecognition` used on Safari iOS — mic button works without error
- [ ] Voice Firefox: mic button silently becomes text search icon — no crash, no error message
- [ ] Error boundaries: `<DiscoveryErrorBoundary>` wraps AR/Map/List — single view crash doesn't kill whole page
- [ ] GDPR consent banner: shown on first load (no prior localStorage key), cannot be dismissed without choosing
- [ ] Consent POST fired to `/auth/consent/` before any location or analytics call
- [ ] Offline first-load: `OfflineFirstLoad` empty state shown — no skeletons, no spinners on true offline+empty cache
- [ ] Offline reconnect: `OfflineBanner` dismisses, auto-refetch fires, "Back online" toast shown
- [ ] Sentry: error captured in Sentry dashboard (verify with deliberate throw in dev/staging)
- [ ] SPA routing: `/vendor/:id` deep-linked URL loads correctly from cold start (Netlify `_redirects` or Vercel config active)
- [ ] Mapbox token: restricted to `app.airad.pk` domain in Mapbox dashboard (manual verification step)
- [ ] Navigation bottom sheet: shows Google Maps / in-app options BEFORE starting navigation
- [ ] AR low-end: `BackdropFilter` disabled on `prefers-reduced-motion` OR when `devicePixelRatio < 2` as proxy heuristic

---

*USER PORTAL FRONTEND PLAN — COMPLETE (Part 1 + Part 2)*
*Version: 1.0 | February 2026 | Source of Truth: AirAds_User_Portal_Super_Master_Prompt.md UP-0 through UP-13*
