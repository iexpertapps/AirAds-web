# AirAds — Super Master Prompt
## User Portal · End-to-End Full Stable Production Build
### Windsurf IDE · Autonomous Build Mode

---

> **How to Use:** Yeh poora document Windsurf ko ek baar deeply analyze karne ke liye do. Phir module by module kaam karo — har ek prompt block apne waqt par paste karo. Sab kuch ek saath mat bhejo. Windsurf intelligent hai — yeh intent aur architecture samajhta hai. Har module complete aur stable ho jaye, phir aglay par jao.

> **Tumhara kaam sirf yeh nahi ke yeh prompts padh lo aur bana lo — pehle poori cheez ko deeply analyze karo, samjho, apne liye plan banao, phir ek ek kar ke end-to-end full stable aur production enterprise grade product deliver karo. Yeh tumhari hundred percent responsibility hai.**

---

## 📋 TABLE OF CONTENTS

- **UP-0** — Project Identity, Authority & Global Rules
- **UP-1** — Design System & AirAds Branding (WOW Standard)
- **UP-2** — Landing Page (WOW · Airbnb DLS · Minimal · High Impact)
- **UP-3** — User Authentication (Separate · Standalone · Branded)
- **UP-4** — Discovery Home (AR Default · Map Option · Voice-First)
- **UP-5** — AR Discovery View (Web AR · Spatial Markers · Live Promotions)
- **UP-6** — Map & List View (Toggle · Nearby · Filters)
- **UP-7** — Voice Search & Natural Language Discovery
- **UP-8** — Tag-Based Browsing & Filtering
- **UP-9** — Vendor Profile & Detail View
- **UP-10** — Promotions & Deals Discovery
- **UP-11** — Navigation & Turn-by-Turn Directions
- **UP-12** — User Preferences & Settings
- **UP-13** — Final QA, Polish & Production Readiness

---

---

# PROMPT UP-0 — Project Identity, Authority & Global Rules

```
Yeh AirAds ka User Portal hai — ek standalone web application jo end customers use karte hain.

AirAds ek hyperlocal discovery platform hai jo nearby customers ko small vendors, 
street stalls, kiosks, aur local shops se real time mein connect karta hai.

AirAds ka core philosophy hai: "Nearby + Now"
Platform ka har feature, har screen, har interaction yeh ek sawaal answer karta hai:
"Mujhe abhi, mere paas, best value mein kya mil sakta hai?"

User Portal SIRF customers ke liye hai — woh log jo businesses discover karte hain.
Yeh Vendor Portal nahi hai. Yeh Admin Portal nahi hai.
Alag login, alag experience, alag purpose.

Is platform ki teen primary interaction modes hain:
1. AR-First Exploration — camera se spatial discovery
2. Voice-Driven Search — natural language queries
3. Tag-Based Browsing — category aur intent filtering

Core Design Principle:
Friction minimize karo. Speed to decision maximize karo.
User ko 10 seconds ke andar relevant vendor milna chahiye app open karne ke baad.

Teen types ke users hain platform par:
- Regular Users (Customers) — browse, discover, navigate karte hain
- Vendors — apni listing manage karte hain (alag portal)
- Platform Admins — system manage karte hain (alag portal)

Ranking algorithm jo har user ke liye results determine karta hai:
Relevance 30% + Distance 25% + Active Offer 15% + Popularity 15% + Subscription Tier 15%
Yeh users ko explain nahi karna — lekin har feature is logic ke according kaam kare.

Global Rules — inhe kabhi violate mat karna:
- User Portal ka login page BILKUL ALAG hoga — Vendor Portal se separate, Admin Portal se separate
- Full AirAds branding — orange, crimson, teal, black — logo se derive karo
- Airbnb Design Language System strictly follow karna hai — yeh non-negotiable hai
- Default view AR hoga — agar web par possible hai to. Map aur List ka option bhi hoga
- Landing page ka design itna strong hona chahiye ke koi bhi dekhe aur keh de "WOW — kya design hai"
- Landing page simple hoga — boht zyada content nahi. Main section mein video ya slides use karo — khud generate karo
- Landing page claude.ai jaisi feel honi chahiye — ek powerful search bar + mic button, clean, minimal
- Existing AirAds theme aur color scheme use karni hai — nayi invent mat karo
- Sab kuch end-to-end full stable aur production enterprise grade hona chahiye
- Koi bug nahi, koi shortcut nahi, koi placeholder nahi — mukammal product deliver karo
- Yeh tumhari hundred percent authority aur hundred percent responsibility hai
```

---

---

# PROMPT UP-1 — Design System & AirAds Branding (WOW Standard)

```
User Portal ke liye complete AirAds design system set up karo.
Yeh sab se important step hai — baaki sab kuch is foundation par build hoga.
Yeh step skip ya shortcut mat karo.

BRAND IDENTITY — Pehle yeh padho:
AirAds ka logo (airad_icon3x.png) — 3 overlapping organic petal shapes on pure black:
  - Top Petal:   Warm Orange  → #FF8C00  (energy, discovery, primary actions)
  - Left Petal:  Deep Crimson → #C41E3A  (passion, alerts, brand identity)
  - Right Petal: Vibrant Teal → #00BCD4  (trust, success, verified)
  - Background:  Pure Black   → #000000

Yeh 3 colors + black — yahi poora AirAds brand hai.
Har UI decision is logo se nikalta hai.
Quality bar: Airbnb, Linear.app, Vercel Dashboard — premium, clean, purposeful.

DESIGN TOKENS:
Brand primitives (theme-independent):
  Brand Orange: #FF8C00 aur iske light/dark variants
  Brand Crimson: #C41E3A aur iske light/dark variants
  Brand Teal: #00BCD4 aur iske light/dark variants
  Brand Gradient: 135deg, orange → crimson → teal

Dark Theme (default — premium feel aur outdoor readability):
  Page background: near-black
  Surface/cards: dark elevated surfaces
  Sidebar: pure black (logo background match)
  Active nav: brand orange highlight
  Text: high contrast white hierarchy

Light Theme (toggle option):
  Page background: light grey
  Surface/cards: white
  Matching semantic colors with adjusted contrast

Spacing scale: 8px base unit — sab spacing is scale se hogi
Border radius: consistent scale — sm, md, lg, xl, full
Typography: DM Sans — Google Fonts se load karo
Transitions: fast (150ms), base (200ms), spring (bouncy, 400ms)

Shared Components — sirf CSS custom properties use karo, kabhi hardcoded colors nahi:
  - Button (primary gradient, secondary, ghost, danger — sizes sm/md/lg — all states)
  - Search Bar (hero size — large, prominent, with mic button integrated)
  - Vendor Card (discovery card with distance, discount badge, category tag)
  - AR Marker (floating overlay style for web AR)
  - Tag Chip (selectable, filterable)
  - Voice Wave Animation (listening state visual)
  - Skeleton Loader (shimmer — kabhi blank white flash nahi)
  - Toast Notifications (positioned, colored by type)
  - Distance Badge (live updating)
  - Promotion Badge (urgent, attention-grabbing)
  - Logo Component (animated float variant for hero sections)

Theme Toggle: system preference detect karo, localStorage mein save karo.
Default: dark (outdoor use ke liye better, premium feel).

Typography: DM Sans apply karo everywhere. Kabhi system fonts directly mat use karo.

CRITICAL: Koi bhi component file mein ek bhi hardcoded hex color nahi hogi.
Sirf CSS custom properties (var(--token-name)).
Yahi theme switch ko instant aur perfect banata hai.
```

---

---

# PROMPT UP-2 — Landing Page (WOW · Airbnb DLS · Minimal · High Impact)

```
AirAds User Portal ka public-facing Landing Page banao.

DESIGN MANDATE:
Koi bhi is page par aaye aur pehle 3 seconds mein keh de: "WOW — kya design hai."
Airbnb.com quality. Premium, clean, purposeful. Clutter nahi. Corporate feel nahi.
Simple hona chahiye — boht zyada content nahi. Visuals aur micro-copy kaam karein.
User ko instantly samajh aaye ke AirAds kya hai aur kaise kaam karta hai.

SECTION 1 — NAVBAR (Sticky):
Pure black background (logo background match).
Left: AirAds logo + wordmark brand orange mein.
Center: Navigation links — "How It Works", "For Vendors", "Sign In"
Right: "Start Exploring" CTA — gradient pill button (orange → crimson).
Scroll ke baad: backdrop blur + subtle border.
Mobile: hamburger menu with full-screen slide-in.

SECTION 2 — HERO (Full Viewport — Claude.ai Style):
Yeh page ka heart hai. Claude.ai jaise feel honi chahiye — ek powerful, centered, minimal experience.

Layout: Full viewport height. Dark background. Everything centered.

Large ambient gradient glow background — brand colors ka soft radial glow
(orange glow left, teal glow right — subtle, not distracting).

Animated AirAds logo — top center, medium size, gentle float animation.

H1 Headline (very large, bold):
"Discover What's Near You,
Right Now."
"Near You" gradient text (orange → crimson).

Subheadline (1-2 lines max, secondary color, centered):
"Point your camera. Speak your craving. Walk to the deal."

HERO SEARCH BAR — Yahi is page ka WOW moment hai:
  Claude.ai jaise — wide, rounded, centered, prominent.
  Left: location pin icon
  Center: placeholder text — "Search for food, shops, deals nearby..."
  Right: Mic button (gradient circle, pulsing when listening)
  Below bar: Quick tags row — "🍕 Food" "☕ Coffee" "✂️ Salon" "🛍️ Shopping" "🔥 Deals"
  Hover state: bar glows with brand orange shadow
  Focus state: bar expands slightly, glow intensifies
  This is the PRIMARY action — user types or speaks their intent here.

Below search bar:
Small text: "No signup needed · Works in your browser · Finds what's open now"

SECTION 3 — HOW AIROADS WORKS (Auto-Playing Slides — Self-Generated):
Section title: "Three Ways to Discover"
Subtitle: "Pick the one that feels right."

Yahan ek AUTO-PLAYING SLIDESHOW banao — 4 seconds per slide, smooth crossfade.
Phone mockup frame ke andar slides play hongi — bahar nahi.
Slides khud generate karo (Framer Motion + SVG + CSS — koi external video nahi):

SLIDE 1 — AR Discovery:
Phone mockup andar: camera view simulate karo CSS gradient se.
Business name tags float kar rahe hain (SVG floating labels):
  "🍔 Raja Burgers — 120m" (orange tag, animated entrance from right)
  "☕ The Coffee Lab — 80m" (teal tag, animated from left)
  "✂️ Style Studio — 200m" (crimson tag, animated from top)
Tags continuously float up, slight rotation — alive feel.
Text neeche: "Point your camera. See what's around you."

SLIDE 2 — Voice Search:
Phone mockup andar: dark screen, centered mic icon with pulsing rings (brand crimson).
Voice wave animation (5 bars, dancing — Framer Motion).
Text appearing word by word: "cheap biryani near me"
Then: Results sliding up — 3 vendor cards with distances.
Text neeche: "Just say what you're craving."

SLIDE 3 — Deals & Promotions:
Phone mockup andar: Map view with orange pins.
One pin expands into a card: "🔥 30% OFF · Al Baik · 150m · Ends in 2h"
Countdown timer ticking (CSS animation).
Text neeche: "Real-time deals from nearby shops."

SLIDE 4 — Navigate & Arrive:
Phone mockup andar: Clean turn-by-turn navigation line.
Destination marker pulses with brand teal.
"Walk 2 minutes north" text visible.
Text neeche: "One tap to get there."

Slide dots below: 4 dots, active = brand orange.
Swipe-enabled on mobile. Pause on hover. Loop continuously.

SECTION 4 — THREE MODES EXPLAINED:
Background: pure black. Full width.

3 large horizontal tiles (desktop) / vertical stack (mobile):
Each tile: large icon animation + title + 2-line description.

Tile 1 — AR Mode:
Icon: Camera with AR dots floating out (SVG, animated on scroll into view).
Title: "AR Camera Discovery"
Body: "Open your camera and see nearby businesses floating in your real world view. Tap any marker to learn more."
Border: left 3px brand orange.

Tile 2 — Voice Mode:
Icon: Microphone with sound wave rings.
Title: "Just Speak"
Body: "Say what you want in plain language. 'Cheap lunch near me' or 'open salon right now' — we understand."
Border: left 3px brand crimson.

Tile 3 — Map Mode:
Icon: Map with animated pins dropping.
Title: "See The Map"
Body: "Classic map view with all nearby vendors pinned. Filter by category, distance, or active deals."
Border: left 3px brand teal.

SECTION 5 — SOCIAL PROOF (Minimal):
3 numbers, large, centered:
"500+" vendors · "3 cities" · "Real-time" deals
Animated count-up on scroll into view.
Below: "No account needed to start exploring."

SECTION 6 — FINAL CTA:
Full-width dark section.
Brand gradient soft background (low opacity).
H2: "What's Near You Right Now?"
Large search bar (same as hero — repeat it here).
Small text: "Or just tap to open the live map →"

SECTION 7 — FOOTER:
Pure black. Gradient divider at top (brand gradient, 2px).
Left: Logo + tagline "Nearby + Now"
Right: "For Vendors →" link, Privacy Policy, Terms.
Bottom: © 2026 AirAds.

PERFORMANCE RULES:
- All animations: prefers-reduced-motion respect karo
- Lazy load everything below fold
- Scroll animations: whileInView, once: true
- Zero external images — all SVG or CSS generated
- No walls of text — if it takes more than 5 seconds to read a section, trim it
```

---

---

# PROMPT UP-3 — User Authentication (Separate · Standalone · Branded)

```
AirAds User Portal ka authentication system banao.
Yeh BILKUL ALAG hoga Vendor Portal aur Admin Portal se — alag URL, alag design, alag flow.

IMPORTANT PRINCIPLE:
Bahut saare features bina login ke kaam karein — browsing, AR view, map, voice search.
Login sirf tab chahiye jab user personalization ya saved preferences chahiye.
"No signup needed to explore" — yeh brand promise hai.

GUEST MODE (Default):
Jab koi landing page par aaye — directly explore kar sake bina login ke.
"Start Exploring" button directly discovery screen par le jaaye.
Koi forced login wall nahi.

LOGIN PAGE (/user/login):
Yeh Vendor Portal ke /login se bilkul alag URL par hoga.
Full-page, centered layout. Dark background. AirAds branding.
Large logo (animated float) + tagline: "Welcome back, Explorer."
Fields: Email + Password (show/hide toggle).
OR: "Continue as Guest — No account needed →" prominent link.
Social login option: "Sign in with Google" (if configured).
Link: "New to AirAds? It's free →" → register page.
On success: Return to wherever user was before, or discovery screen.

REGISTER PAGE (/user/register):
Simple, minimal form:
  Name (first name only — keep it friendly)
  Email
  Password (strength indicator)
  "I agree to Terms" checkbox
No lengthy forms. No phone number required. No address required.
After register: Email verification link sent → success screen.

POST-LOGIN STATE:
Persistent header shows: small avatar/initial + "Hi, [Name]" — not intrusive.
Discovery experience is identical — login just adds personalization layer.
Logout: Clears session, returns to guest mode — discovery still works.

PAGE STRUCTURE:
Both login and register pages: 
  Left panel (desktop): Brand panel — pure black, logo, tagline, 3 trust points
  Right panel: Form
  Mobile: Full screen form with logo at top
  
Trust points on left panel:
  "✓ Free to explore, always"
  "✓ No credit card, ever"
  "✓ Your location stays private"
```

---

---

# PROMPT UP-4 — Discovery Home (AR Default · Map Option · Voice-First)

```
User Portal ka main Discovery Screen banao — jahan sab kuch hota hai.

YAHI APPLICATION KA HEART HAI. Yeh screen perfectly kaam kare.

DEFAULT STATE — AR VIEW:
Jab user "Start Exploring" kare ya login kare:
  Browser location permission request karo.
  Agar granted: Immediately AR view activate karo.
  Agar denied: Map view par fallback karo (gracefully, no crash, no blank screen).

AR VIEW (Web mein):
  Agar browser WebXR ya DeviceOrientationEvent support karta hai: 
    Real AR — camera feed par business markers overlay karo.
  Agar support nahi (desktop, ya permission denied):
    Simulated AR — gradient background + floating animated business cards
    jo real AR jaisi feel dein. Koi "not supported" error screen nahi.
    User ko seamless experience milni chahiye — technology limitation visible nahi honi chahiye.

VIEW SWITCHER — Prominent, always visible:
  3 toggle buttons (pill shape, sticky top):
    📷 AR  |  🗺️ Map  |  📋 List
  Active view: brand orange background.
  Switching is instant with smooth transition.
  User ka preference remember karo (localStorage).

TOP SEARCH BAR (Persistent, always visible):
  Same style as landing page hero bar — wide, rounded.
  Left: GPS pin icon (tapping opens city selector if location denied).
  Center: "Search nearby..." placeholder.
  Right: Mic button (voice search trigger — see UP-7).
  This bar is always accessible — top of screen, no matter what view.

LOCATION CONTEXT:
  "Near Gulberg, Lahore" — current area name shown below search bar.
  Tapping it: Opens location picker (manual city/area selector).

ACTIVE PROMOTIONS STRIP:
  Horizontal scrollable strip below search bar (when promotions are live nearby):
  Each chip: "🔥 30% OFF · Raja Burgers · 2 min walk"
  Tapping a chip: Opens that vendor's detail directly.
  Strip only shows when active promotions exist nearby — auto-hides otherwise.

LOADING STATE:
  First load: Skeleton cards with shimmer — never blank screen.
  AR markers: Fade in as data loads — not a sudden pop.
  "Finding vendors near you..." subtle text during initial GPS fix.

EMPTY STATE (No vendors found):
  Large AirAds logo (low opacity watermark).
  "No vendors found nearby."
  "Try expanding the search area or browse by category."
  Two CTA buttons: "Expand Radius" + "Browse Categories"
  Never show a blank white screen.

OFFLINE STATE:
  Persistent top banner: "You're offline — showing last known results."
  Cached results still visible.
  Retry button when connection restores.
```

---

---

# PROMPT UP-5 — AR Discovery View (Web AR · Spatial Markers · Live Promotions)

```
AR Discovery experience banao — User Portal ka most iconic feature.

WEB AR APPROACH:
Two modes (detect automatically, user ko pata na chale):

MODE A — Real AR (mobile browser with camera access):
  Camera feed background.
  DeviceOrientationEvent use karo direction ke liye.
  Vendor markers float in 3D space at correct compass bearing.
  Distance dynamically updates as user moves.

MODE B — Simulated AR (desktop, or camera denied):
  Dark gradient background (simulate outdoor depth).
  Animated floating vendor cards in a semi-arc arrangement.
  Parallax effect on mouse move (desktop).
  Gyroscope effect on mobile tilt.
  Feels like AR even without camera — seamless, not a fallback message.

AR MARKER DESIGN:
Each vendor is a floating card in AR space:
  Card shape: rounded pill/card with subtle glassmorphism (dark bg, blur).
  Content: Business name (bold) + category emoji + distance ("120m") + discount badge.
  Discount badge: "🔥 20% OFF" — brand orange background, pulsing glow.
  Subscription indicator: Small colored dot (silver/gold/diamond/platinum).
  Size: Closer vendors = larger markers, further = smaller (depth illusion).
  
On tap/click:
  Card expands smoothly (Framer Motion spring animation).
  Expanded state shows: full name, category, hours, active promotion, quick actions.
  Quick action buttons: "Directions 🧭" "Call 📞" "View Profile →"

AR MARKER CLUSTERING:
  Agar multiple vendors bohut paas hain: Group them into a cluster marker.
  Cluster shows: count badge + category icons.
  Tapping cluster: Slight zoom in + expand into individual markers.

WALKING SAFETY:
  Agar motion sensor detect kare ke user chal raha hai (accelerometer):
  Semi-transparent overlay: "👀 Watch where you're walking!"
  Auto-dismiss after 3 seconds, then re-shows if user keeps moving.

COMPASS/DIRECTION INDICATOR:
  Small compass rose — top right corner.
  Shows which direction user is facing.
  Markers adjust in real-time as device rotates.

DISTANCE FILTER:
  Slider at bottom: 100m — 500m — 1km — 2km (default: 500m).
  Changing radius: Markers fade in/out with smooth transition.

PERFORMANCE:
  Max visible markers at once: 15 (beyond 15 = cluster or hide further ones).
  Marker position updates: 60fps smooth, not jerky.
  Never freeze or stutter — if performance issue, reduce marker complexity, not framerate.
```

---

---

# PROMPT UP-6 — Map & List View (Toggle · Nearby · Filters)

```
Map View aur List View banao — AR ke alternatives as requested.

MAP VIEW:
Mapbox GL JS (or equivalent) use karo.
Centered on user's current GPS location.
Pulsing blue dot: user's location.

Vendor Pins:
  Orange pins: unclaimed / basic vendors.
  Gold pins: Gold tier vendors.
  Teal pins: Verified vendors.
  Pulsing ring around pins: Active promotion right now.
  
Clicking a pin:
  Bottom sheet slides up (mobile) / side panel opens (desktop).
  Shows: Vendor name, category, distance, current promotion if any.
  "View Full Profile →" button.
  "Get Directions →" button.

Map Controls:
  Top-right: Zoom in/out, "Center on me" button.
  Bottom: Radius selector (same as AR view).

Filter Bar (horizontal scrollable, below map):
  Category chips: "🍕 Food" "☕ Coffee" "✂️ Services" "🛍️ Retail" "🔥 Deals"
  Filter chips: "Open Now" "Under 500m" "Has Discount" "Verified"
  Active filters: brand orange background, × to remove.
  "Clear All" when any filter active.

Tapping filter: Map pins update instantly — filtered out pins fade/disappear with animation.

LIST VIEW:
Clean vertical list of nearby vendors.
Sort options (top right): "Nearest" | "Best Match" | "Active Deals"

Vendor Card (list item):
  Left: Square thumbnail (business logo or category icon).
  Right top: Business name (bold) + category tag.
  Right middle: Distance + area name.
  Right bottom: Active promotion badge OR "No current deals" (grey).
  Far right: Tier badge (silver/gold/diamond/platinum — small).
  Card border: glows brand orange when active promotion is running.

Infinite scroll — load more on scroll, no pagination buttons.
Pull to refresh (mobile).
Skeleton loaders while fetching more.

Empty state per filter: 
  "No food places within 500m right now."
  "Try: expanding radius or removing 'Open Now' filter."
  Two action buttons, not dead ends.
```

---

---

# PROMPT UP-7 — Voice Search & Natural Language Discovery

```
Voice Search system banao — dono: global search aur vendor-specific voice bot.

GLOBAL VOICE SEARCH:
Trigger: Mic button in search bar (always visible).

On Tap:
  Search bar expands to full-width voice input mode.
  Background: dark overlay with brand gradient glow.
  Center: Large pulsing mic icon (brand crimson rings pulsing outward).
  Text: "Listening... say what you're looking for"
  Voice wave visualization: 5 animated bars (up/down like equalizer).

While Listening:
  Real-time transcription appears below mic: "cheap pizza near me..."
  Web Speech API use karo (SpeechRecognition).
  Fallback for unsupported browsers: Auto-switch to text input, no crash.

After Capture:
  Show what was understood: "Searching for: cheap pizza near me"
  Send to discovery with extracted filters.
  Results appear with active filters shown as chips.

Error States:
  Microphone denied: "Microphone access needed for voice search. You can also type here."
  Didn't understand: "I didn't catch that. Try again or type it below."
  No results: "No matches found. Try: 'food nearby' or 'open restaurants'"
  
VENDOR-SPECIFIC VOICE BOT:
On vendor profiles where voice bot is configured (Gold/Diamond/Platinum vendors):
  A "🎙️ Ask this place" button visible in vendor detail.
  Tapping: Compact bottom sheet opens.
  Same mic/listening experience.
  Query sent to that vendor's voice bot specifically.
  Response shows as text bubble + plays as audio (SpeechSynthesis).
  Query history: last 3 questions shown below.
  
Voice Bot indicator on vendor cards:
  Small mic icon badge on cards where voice bot is active.
  Tooltip: "This place has a voice assistant"

QUERY EXAMPLES (show as suggestions when mic opens, disappear on listen):
  "Cheap lunch near me"
  "Open cafe right now"
  "Salons with discounts today"
  "Pizza under 500 rupees"
```

---

---

# PROMPT UP-8 — Tag-Based Browsing & Filtering

```
Tag-Based Browsing system banao — users jo directly search nahi karna chahte unke liye.

TAG BROWSER (Bottom sheet on mobile, side panel on desktop):
Trigger: "Browse" tab in bottom navigation OR "See All Categories" link.

SECTION 1 — What's Hot Right Now:
  Horizontal scrollable chips with active counts.
  Orange chips = vendors actively running promotions in this category.
  Example: "🔥 Pizza (12 active deals)" "☕ Coffee (7 active deals)"
  
SECTION 2 — By Intent:
  Grid of intent cards (2 columns mobile, 4 desktop).
  Each card: Large emoji + short label.
  "Quick Bite 🍔" "Morning Coffee ☕" "Late Night 🌙" "Budget Friendly 💰"
  "Open Now 🟢" "Has Discount 🏷️" "Near Me 📍" "New Places ✨"

SECTION 3 — By Category:
  Full grid of all categories.
  Icon + name. Tap to filter.
  Category counts shown (how many vendors nearby).

SECTION 4 — By Distance:
  Simple options: "Walking (under 5 min)" "Nearby (under 10 min)" "In my area"

MULTI-SELECT:
  Users can select multiple tags to combine filters.
  Each selected tag appears as a chip in a persistent filter bar.
  Individual × to remove each chip.
  "Clear All" removes all at once.

RESULTS UPDATE:
  As tags are selected, discovery screen (AR/Map/List) updates in real time.
  A floating indicator shows updated count: "23 places match"
  On sheet close: filtered results already visible.

SYSTEM TAGS (Not visible to users — internal only):
  New vendor boost, trending, verified — these affect ranking invisibly.
  Users see results affected by these tags, not the tags themselves.
```

---

---

# PROMPT UP-9 — Vendor Profile & Detail View

```
Vendor Profile screen banao — jab user kisi vendor par tap kare tab yeh khule.

SCREEN STRUCTURE:
Scrollable screen. Sticky top header. Content below.

STICKY HEADER:
  Hero media: Cover photo or video (16:9). If none: gradient with category emoji.
  Overlaid bottom: Business name (large, bold, white) + category tag + distance.
  Active promotion banner (if running): "🔥 20% OFF · Ends in 1h 23m" — pulsing, orange.
  Back button: top left.
  Share button: top right.
  Tier badge: small, top right corner.

QUICK STATS BAR (below header, sticky on scroll):
  Distance · Category · Open/Closed status · Voice bot icon (if available).

SECTION 1 — Active Promotion (if any):
  Prominent card. Brand orange gradient background.
  Promotion details: type, value, what it applies to.
  Countdown timer if time-limited.
  "Get Directions Now →" CTA — urgent, large.

SECTION 2 — About:
  Business description.
  Business hours: Visual weekly grid — today highlighted, open/closed clear.
  Phone number: Tap to call.
  Website: Tap to open.
  Service options: "We offer delivery" / "Pickup available" (toggle indicators).

SECTION 3 — Videos / Reels:
  Horizontal scrollable video grid.
  Autoplay first video (muted, no autoplay sound).
  Tap to fullscreen.
  If no videos: Section hidden (no empty state shown here — clean).

SECTION 4 — Location:
  Embedded map (static thumbnail on mobile, interactive on desktop).
  Exact pin location.
  "Get Directions →" button.
  "See on Full Map →" link.

SECTION 5 — Voice Bot (if configured):
  "🎙️ Ask this place anything" — card with mic button.
  "Try: What's the lunch special? · Are you open Sunday? · Do you deliver?"

SECTION 6 — More Nearby:
  Horizontal scroll: Other vendors in same category nearby.
  "See all [Category] nearby →" link.

FLOATING ACTION BUTTON (Mobile):
  Sticky at bottom: "🧭 Get Directions" — brand gradient, large, full-width.
  Disappears when user has scrolled to location section (not redundant).
```

---

---

# PROMPT UP-10 — Promotions & Deals Discovery

```
Promotions aur Deals discovery experience banao.

DEALS TAB (in bottom navigation):
Dedicated "Deals" view — shows all currently active promotions nearby.

LAYOUT:
  Top: "Active Near You Right Now" + live count badge (updates every 60 seconds).
  Filter strip: "All" | "Food" | "Retail" | "Services" | "Flash Deals"
  Sort: "Ending Soon" | "Closest" | "Best Value"

DEAL CARDS:
  Larger than regular vendor cards — promotion is the hero.
  Top: Promotion badge (large) — "30% OFF" or "Happy Hour" or "Buy 1 Get 1"
  Business name + category below.
  Distance + "Open Now" indicator.
  Countdown timer if ending within 2 hours: "⏰ Ends in 1h 47m"
  Urgency color coding: 
    > 2h remaining: normal
    1-2h: amber glow
    < 1h: crimson pulsing glow
  "Get Directions →" quick action on card.

FLASH DEAL ALERT (optional, can be dismissed):
  If user is within 200m of a flash deal starting:
  Toast notification slides in from top: "🔥 Flash Deal just started 150m from you!"
  Tapping opens that vendor directly.

EXPIRED DEALS:
  Graceful: Expired deal cards automatically disappear from this view.
  No "sorry, deal expired" dead ends.

EMPTY STATE:
  "No active deals near you right now."
  "Check back at lunch time — that's when most deals go live."
  Time-aware suggestion (morning = check at lunch, evening = check tomorrow morning).
```

---

---

# PROMPT UP-11 — Navigation & Turn-by-Turn

```
Navigation experience banao — vendor tak pahunchne ke liye.

"GET DIRECTIONS" TAP:
  From any vendor card or profile — single tap.
  
BEHAVIOR OPTIONS (in order of preference):
  Option A: In-app map navigation (if Mapbox routing available).
  Option B: Deep link to Google Maps / Apple Maps app.
  Option C: Web Google Maps directions (always works as fallback).
  
Auto-detect: Agar Google Maps app installed hai → open that. Otherwise web.

IN-APP NAVIGATION (if implemented):
  Full-screen map.
  User's pulsing blue dot.
  Destination: brand orange pulsing marker with business name.
  Route line: brand gradient (orange → teal).
  Turn-by-turn text instructions: bottom panel.
  Estimated walk time + distance: top of screen.
  "Cancel Navigation" → back to previous screen.

ARRIVAL DETECTION:
  When user is within 30m of destination:
  Gentle overlay: "You've arrived at [Business Name]! 🎉"
  Option to view active promotion again.
  "Navigate again" option for another nearby vendor.

DURING NAVIGATION — Vendor Info Accessible:
  Persistent mini-card at top: business name + active promotion (don't lose context).
  Tap to expand to full vendor profile (doesn't stop navigation).
```

---

---

# PROMPT UP-12 — User Preferences & Settings

```
User Preferences aur Settings screen banao — minimal, purposeful.

ACCESSIBLE FROM: Top navigation avatar → "Preferences"
GUEST USERS: Can access limited preferences (theme, default view, radius).
LOGGED-IN USERS: Full preferences available.

SETTINGS SECTIONS:

DISCOVERY SETTINGS:
  Default View: AR / Map / List (radio — remembers choice)
  Search Radius: Slider (100m — 5km, default 500m)
  Show Open Now Only: Toggle (default off)
  Default Category: "All" or select a category preference

NOTIFICATION PREFERENCES (logged-in only):
  Nearby Deals Alerts: Toggle
  Flash Deal Alerts: Toggle
  Vendor Updates (saved vendors): Toggle
  All Notifications Off: Master toggle

APPEARANCE:
  Theme: Dark / Light / System Default
  Language: (future — placeholder for now)

PRIVACY & DATA:
  "What data we collect" — plain language explanation, no legalese.
  "Clear my search history" — one button.
  "Delete my account" — if logged in. Requires confirmation.
  "Export my data" — if logged in. JSON download.

ABOUT:
  App version.
  "For Vendors → List Your Business" — link to Vendor Portal.
  Privacy Policy / Terms of Service links.

DESIGN:
  Clean, minimal list view.
  Section dividers with subtle gradient lines (brand gradient, 1px, low opacity).
  No unnecessary options. Every setting shown must have a clear user benefit.
```

---

---

# PROMPT UP-13 — Final QA, Polish & Production Readiness

```
Poori AirAds User Portal ki complete quality pass karo.
Senior QA engineer ki tarah — brutal, no-compromise.

YEH CHEEZAIN VERIFY KARO:

EXPERIENCE FLOW:
  Landing page se discovery tak: har step smooth, har transition polished.
  Guest flow: koi bhi landing page par aaye → AR/map pe ho jaaye without login — zero friction.
  Login flow: alag URL, alag design, complete branding, works end-to-end.
  Switching views (AR → Map → List): instant, smooth, state preserved.

SEARCH & DISCOVERY:
  Text search returns relevant results, updates in real time.
  Voice search: captures, transcribes, filters — works on Chrome, Edge, Safari.
  Tag filters: apply, combine, remove — results update live.
  Radius change: markers/pins update without full reload.
  Empty states: descriptive, actionable, never blank.

AR VIEW:
  Mobile browser with camera: Real AR markers appear.
  Desktop / camera denied: Simulated AR — seamless, no error message.
  Markers: distance correct, click expands, quick actions work.
  Safety overlay: appears when motion detected.
  Clusters: work correctly when multiple vendors overlap.

MAP VIEW:
  Map loads centered on user location.
  Pins render with correct colors by tier.
  Active promotion pins have pulsing ring.
  Clicking pin: bottom sheet/side panel opens correctly.
  Filters update map pins in real-time.

VENDOR PROFILE:
  All sections load correctly.
  Active promotion countdown: counts down in real-time.
  Videos play inline (muted autoplay).
  Voice bot: opens, records, responds.
  Get Directions: works (launches maps app or in-app navigation).

PERFORMANCE:
  Landing page: Lighthouse 90+ score.
  Discovery screen: loads within 2 seconds of GPS fix.
  AR markers: 60fps, no stutter.
  Image skeletons everywhere — no white flash.
  Offline mode: banner shows, cached results visible, no crash.
  
RESPONSIVE:
  Mobile (375px): Everything usable with thumb. Touch targets 44×44px min.
  Tablet (768px): Layouts adapt correctly.
  Desktop (1280px): Full experience with side panels.
  No horizontal scroll anywhere on any breakpoint.

BRANDING CONSISTENCY:
  Zero hardcoded hex colors in any component.
  Every interactive element: hover + focus state visible.
  Focus rings: brand orange (keyboard accessibility).
  All images: alt text present.
  Color contrast: WCAG AA minimum everywhere.
  AirAds logo: present in navbar, footer, loading states, empty states.

AUTHENTICATION:
  User portal login (/user/login) completely separate from vendor portal (/login).
  Guest mode works perfectly without login.
  Login → returns to previous context (not just dashboard).
  Logout → guest mode continues working.
  Token refresh: works silently in background.

ENVIRONMENT:
  All sensitive keys in environment variables — nothing hardcoded.
  .env.example file with all required variable names.
  Production build: zero TypeScript errors, zero console errors.
  Vercel/Netlify config: all routes redirect to index.html (React Router).

FINAL CHECK — THE WOW TEST:
  Show the landing page to someone who has never seen AirAds.
  They should say "WOW — kya design hai" within 3 seconds.
  They should understand what AirAds does within 10 seconds.
  If either fails → redesign, don't ship.
```

---

---

## 📌 BUILD SEQUENCE

```
Yeh order follow karo — ek step complete hone ke baad agla shuru karo:

1.  UP-0  → Pehle bhejo (global context set karta hai)
2.  UP-1  → Design system (koi bhi UI kaam shuru hone se pehle — non-negotiable)
3.  UP-2  → Landing page (first WOW impression)
4.  UP-3  → Authentication (separate, standalone)
5.  UP-4  → Discovery home shell (core layout + view switcher)
6.  UP-5  → AR view (main feature — sabse zyada time dو)
7.  UP-6  → Map + List view
8.  UP-7  → Voice search
9.  UP-8  → Tag browsing
10. UP-9  → Vendor profile
11. UP-10 → Deals discovery
12. UP-11 → Navigation
13. UP-12 → Preferences
14. UP-13 → Final QA (bilkul aakhir mein — sab banne ke baad)
```

---

## 📌 AUTHORITY DOCUMENTS

```
Har design decision ke liye yeh documents ground truth hain:
- AirAd End User Functional Document — user journeys, personas, feature specs
- AirAd Vendor Functional Document — vendor tiers, features available per tier
- AirAd Data Collection & Seed Data — geographic structure, tag system
- AirAd Admin Operations Document — governance, content policies
- AirAd WOW Design Prompt — visual design standards
- airad_icon3x.png — brand color source of truth

In documents mein jo likha hai woh final hai.
Koi assumption nahi. Koi shortcut nahi.
Jo produce hoga woh end-to-end full stable aur in requirements ke mutabiq hoga.
Yeh tumhari hundred percent authority aur hundred percent responsibility hai.
```

---

*AirAds User Portal Super Master Prompt v1.0 | February 2026*
