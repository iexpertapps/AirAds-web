# AirAd — FRONTEND MASTER PLAN
## Admin Portal + Vendor Portal (Standalone) — React 18 + TypeScript 5
### Airbnb Design Language System (DLS) — Non-Negotiable

**Version:** 2.0 — Full Rebuild  
**Date:** February 2026  
**Status:** AUTHORITATIVE — Supersedes `02_FRONTEND_PLAN.md`
**Subscription Ref:** `requirements/AirAd Phase-1 – Tiered Vendor Subscription Architecture-2.md`
**Value Ladder:** Visibility (Silver) → Control (Gold) → Automation (Diamond) → Dominance (Platinum)

---

## TABLE OF CONTENTS

1. [Current State Audit](#1-current-state-audit)
2. [Architecture Overview — Two Separate Applications](#2-architecture-overview)
3. [Tech Stack](#3-tech-stack)
4. [Shared DLS Design System](#4-shared-dls-design-system)
5. [Application 1 — Admin Portal (Stabilize + Extend)](#5-admin-portal)
6. [Application 2 — Vendor Portal (New Build)](#6-vendor-portal)
7. [Vendor Portal Landing Page — WOW Factor](#7-vendor-portal-landing-page)
8. [Vendor Portal Subscription Module — Stripe](#8-vendor-portal-subscription-module)
9. [Vendor Portal Claim Flow](#9-vendor-portal-claim-flow)
10. [Vendor Portal Dashboard & Features](#10-vendor-portal-dashboard--features)
11. [Build Sequence & Sessions](#11-build-sequence--sessions)
12. [Quality Gate Checklist](#12-quality-gate-checklist)

---

## 1. CURRENT STATE AUDIT

### Admin Portal — ~90% Complete

| Page | Status | Notes |
|---|---|---|
| Login | ✅ | JWT auth, role-based redirect |
| Platform Health Dashboard | ✅ | 6 hero cards, charts, map, system alerts |
| Geo Management | ✅ | Country → City → Area → Landmark tree |
| Tags Management | ✅ | CRUD, system tags read-only, filters |
| Vendors List + QC Queue | ✅ | Dense table, filters, bulk actions |
| Vendor Detail (6 tabs) | ✅ | Overview, photos, visits, tags, analytics, notes |
| Imports | ✅ | CSV upload, Google Places, status tracking |
| Field Operations | ✅ | Visit table, photos, agent filter |
| QA Dashboard | ✅ | GPS drift flags, duplicate detection |
| Audit Log | ✅ | Immutable log, JSON diff viewer |
| User Management | ✅ | SUPER_ADMIN only, create/edit/unlock |

### Known Issues

1. React Router v7 deprecation warnings (6x) — need v6 syntax cleanup
2. Dashboard recent activity timestamps show "—" instead of formatted dates
3. Logout returns 400 from backend (cosmetic — session still clears)
4. Some pages may have stale data after E2E audit fixes

### Vendor Portal — 0% (New Build Required)

Everything from scratch: landing page, auth, claim flow, dashboard, discounts, analytics, voice bot, subscription management.

---

## 2. ARCHITECTURE OVERVIEW

### Two Separate Applications, One Shared DLS

```
airaad/frontend/              ← EXISTING Admin Portal (stabilize + extend)
  src/
    components/dls/           ← Shared DLS components (extract to package later)
    pages/                    ← Admin pages
    ...

airaad/vendor-portal/         ← NEW Vendor Portal (standalone app)
  src/
    components/dls/           ← Copy of shared DLS (same tokens + components)
    components/landing/       ← Landing page components
    components/portal/        ← Portal-specific components
    pages/
      landing/                ← Public landing page
      auth/                   ← Vendor login (OTP)
      onboarding/             ← Claim + setup wizard
      dashboard/              ← Vendor dashboard
      discounts/              ← Discount management
      analytics/              ← Analytics dashboard
      voicebot/               ← Voice bot configuration
      subscription/           ← Subscription management
      profile/                ← Business profile editing
      reels/                  ← Reel management
    ...
```

**Why separate apps:**
- Vendor Portal has its own login system — no overlap with admin
- Completely different navigation, layout, and user flow
- Different auth mechanism (OTP vs email/password)
- Landing page is public-facing — different SEO and performance needs
- Can be deployed to different subdomains (e.g., `vendor.airad.pk` vs `admin.airad.pk`)

---

## 3. TECH STACK

### Shared Between Both Apps

| Tool | Purpose |
|---|---|
| **Vite + React 18 + TypeScript 5** | Framework |
| **React Router v6** | Routing (fix v7 deprecation warnings) |
| **Zustand** | Global state (auth + UI) |
| **TanStack Query v5** | API data fetching + caching |
| **Axios** | HTTP client with JWT interceptor |
| **React Hook Form + Zod** | Forms + validation |
| **lucide-react** | Icons (stroke-width: 1.5, never filled) |
| **Recharts** | Charts (line, bar, donut, heatmap) |
| **Leaflet + react-leaflet** | Maps + GPS components |

### Vendor Portal Additional

| Tool | Purpose |
|---|---|
| **Framer Motion** | Landing page animations + transitions |
| **@stripe/stripe-js + @stripe/react-stripe-js** | Stripe checkout integration |
| **Swiper** | Landing page hero carousel/slides |
| **react-intersection-observer** | Scroll-triggered animations |
| **lottie-react** | Micro-animations for landing page |
| **react-countup** | Animated statistics counters |
| **react-hot-toast** | Toast notifications |
| **@tanstack/react-table** | Advanced data tables |

---

## 4. SHARED DLS DESIGN SYSTEM

### 4.1 Design Tokens (`dls-tokens.css`)

```css
:root {
  /* Brand Colors — AirAd Identity */
  --color-rausch: #FF5A5F;      /* Primary CTA — max 1 per view */
  --color-babu: #00A699;         /* Success / approved states */
  --color-arches: #FC642D;       /* Warning / pending states */
  --color-hof: #484848;          /* Primary text */
  --color-foggy: #767676;        /* Secondary text */
  --color-white: #FFFFFF;
  
  /* Neutrals */
  --color-grey-50: #F7F7F7;
  --color-grey-100: #F0F0F0;
  --color-grey-200: #EBEBEB;
  --color-grey-300: #DDDDDD;
  --color-grey-400: #AAAAAA;
  
  /* Semantic */
  --color-success-text: #008A05;  --color-success-bg: #E8F5E9;
  --color-warning-text: #C45300;  --color-warning-bg: #FFF3E0;
  --color-error-text: #C13515;    --color-error-bg: #FFEBEE;
  --color-info-text: #0077C8;     --color-info-bg: #E3F2FD;

  /* Typography */
  --font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;

  /* Spacing (8px grid) */
  --space-1: 4px;  --space-2: 8px;  --space-3: 12px;  --space-4: 16px;
  --space-5: 20px; --space-6: 24px; --space-8: 32px;  --space-10: 40px;
  --space-12: 48px; --space-16: 64px; --space-20: 80px; --space-24: 96px;

  /* Animation */
  --duration-fast: 150ms;
  --duration-normal: 250ms;
  --duration-slow: 400ms;
  --ease-standard: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-decelerate: cubic-bezier(0.0, 0, 0.2, 1);
  --ease-accelerate: cubic-bezier(0.4, 0, 1, 1);

  /* Layout */
  --sidebar-width: 240px;
  --topbar-height: 64px;
  --content-max-width: 1280px;
  --landing-max-width: 1440px;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### 4.2 Non-Negotiable DLS Rules

1. **CSS custom properties ONLY** — never hardcode hex values in components
2. **`--color-rausch` for primary CTAs only** — max 1 per view
3. **`--color-babu` for success/approved** states
4. **`--color-arches` for warnings/pending** states
5. **8px base spacing grid** — no arbitrary pixel values
6. **DM Sans typography** only
7. **WCAG 2.1 AA** — 4.5:1 body text, 3:1 large text
8. **All tables: empty state + skeleton loading** — NEVER spinners for content areas
9. **All interactive elements: keyboard navigable** with visible focus ring
10. **`prefers-reduced-motion`:** disable ALL animations
11. **Sidebar nav: `border-radius: 0 100px 100px 0`** (pill-right)
12. **No icon-only buttons without `aria-label`**
13. **lucide-react ONLY** for icons, stroke-width: 1.5, never filled
14. **AirAd branding consistent** — same colors, typography, visual identity on EVERY page

### 4.3 DLS Component Library

All components built BEFORE any pages. Each with full TypeScript props, keyboard navigation, and aria attributes.

| Component | Spec |
|---|---|
| **Button** | Primary (rausch), Secondary (outlined), Destructive, Ghost. Heights: 32/40/48px |
| **Badge** | Success (babu), Warning (arches), Error, Info, Neutral. 24px height, 12px radius |
| **Table** | Sortable, paginated, EmptyState + SkeletonRows, 56px row height, checkbox column |
| **Input/Select/Textarea** | 40px height, 8px radius, rausch focus ring, error state with icon |
| **Modal** | backdrop-blur 4px, 16px radius, focus trap, ESC close, 480/640/80vw widths |
| **Drawer** | 640px right-side, same overlay as Modal, focus trap |
| **Sidebar** | 240px fixed, pill-right nav items, role-based visibility |
| **Toast** | Top-right, auto-dismiss 4s, success/error/warning/info with icon, stackable |
| **EmptyState** | Illustration + heading + subheading + CTA button |
| **SkeletonTable** | Animated skeleton rows matching column widths |
| **GPSInput** | lat/lng inputs + draggable Leaflet marker |
| **Card** | 16px radius, subtle shadow, hover lift effect |
| **Tabs** | Horizontal tab bar with indicator, lazy loading content |
| **ProgressBar** | Animated fill, percentage label, color variants |
| **Avatar** | Circle image with fallback initials, size variants |
| **Chip** | Removable tag, selected/unselected states, icon support |

---

## 5. ADMIN PORTAL

### Status: Stabilize + Extend for Phase B

### 5.1 Fix Known Issues

| Issue | Fix |
|---|---|
| React Router v7 deprecation warnings | Audit all `<Route>` usage, use v6 patterns |
| Dashboard timestamps show "—" | Fix date formatting in recent activity feed |
| Logout 400 error | Handle 400 gracefully in authStore.logout() |
| Stale data after E2E fixes | Verify all TanStack Query cache invalidation |

### 5.2 Phase B Admin Extensions

**New Admin Pages:**

1. **Claim Review Queue** (`/admin/claims/`)
   - Table: Vendor Name, Claimer Phone/Email, Claim Type (OTP/Manual), Days Waiting, Status
   - Expandable row: verification evidence (photos, GPS proximity), approve/reject buttons
   - Filter: status (PENDING/APPROVED/REJECTED), claim_type, date range

2. **Content Moderation** (`/admin/moderation/`)
   - Tabbed interface: Reels | Discounts | User Reports
   - Reels tab: video preview player, approve/reject with reason, strike counter
   - Discounts tab: flagged promotions (>75%, >10/day), remove with notification
   - Reports tab: user-submitted reports with category, vendor link, action buttons

3. **Subscription Overview** (`/admin/subscriptions/`)
   - Distribution donut chart: Silver/Gold/Diamond/Platinum
   - Upgrade/downgrade trend line (30 days)
   - Revenue metrics (MRR, churn rate)
   - Individual vendor subscription details table

4. **Notification Management** (`/admin/notifications/`)
   - Template editor: create/edit notification templates
   - Send history log with delivery status
   - Manual broadcast option (SUPER_ADMIN only)

5. **KPI Dashboard** (`/admin/kpis/`)
   - **Acquisition Tab:** Claim rate (% of listings claimed, target 15%), verification completion rate (target 80%), avg time to first reel, daily new claims chart, weekly claim trend
   - **Engagement Tab:** Weekly active vendors (target 60%), avg reels per vendor (target 4/month), active campaign rate (target 40%), avg logins per week
   - **Monetization Tab:** Gold upgrade rate (target 10%), Diamond upgrade rate (target 5%), monthly churn rate (target <10%), ARPU (target PKR 2,500), MRR total, subscription distribution donut, upgrade funnel visualization
   - **Platform Health Tab:** Total AR views monthly, avg vendor views, discovery-to-navigation rate, voice search usage rate, content moderation backlog
   - Each metric shows: current value, target, trend arrow (↑↓), sparkline chart (30 days)
   - Color coding: green (on target), amber (within 20%), red (below 20%)

### 5.3 Admin Dashboard Extensions

Add to existing Platform Health Dashboard:
- Subscription distribution card
- Active discounts count
- Claim queue backlog count
- Content moderation queue count
- Voice bot adoption rate
- KPI summary strip: claim rate, WAV, churn rate, MRR (links to full KPI page)

---

## 6. VENDOR PORTAL

### 6.1 Project Structure

```
airaad/vendor-portal/
├── public/
│   ├── favicon.ico              # AirAd icon
│   ├── og-image.jpg             # Social share image
│   └── videos/                  # Landing page video assets
├── src/
│   ├── styles/
│   │   ├── dls-tokens.css       # Shared DLS tokens
│   │   ├── landing.css          # Landing page specific styles
│   │   └── portal.css           # Portal specific styles
│   ├── components/
│   │   ├── dls/                 # Full DLS component library (shared)
│   │   │   ├── Button.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Table.tsx
│   │   │   ├── Input.tsx / Select.tsx / Textarea.tsx
│   │   │   ├── Modal.tsx / Drawer.tsx
│   │   │   ├── Toast.tsx + ToastProvider.tsx
│   │   │   ├── Card.tsx / Tabs.tsx / ProgressBar.tsx
│   │   │   ├── EmptyState.tsx / SkeletonTable.tsx
│   │   │   └── Avatar.tsx / Chip.tsx / Toggle.tsx
│   │   ├── landing/             # Landing page components
│   │   │   ├── Navbar.tsx       # Transparent → solid on scroll
│   │   │   ├── HeroSection.tsx  # Video/animated slides
│   │   │   ├── HowItWorksSection.tsx
│   │   │   ├── TierPreviewSection.tsx
│   │   │   ├── SocialProofSection.tsx
│   │   │   ├── CTASection.tsx
│   │   │   └── Footer.tsx
│   │   ├── portal/              # Portal-specific components
│   │   │   ├── PortalSidebar.tsx
│   │   │   ├── PortalTopBar.tsx
│   │   │   ├── SubscriptionBadge.tsx
│   │   │   ├── FeatureGate.tsx  # Wraps premium features with upgrade prompt
│   │   │   ├── ProfileCompleteness.tsx
│   │   │   ├── DiscountCard.tsx
│   │   │   ├── ReelCard.tsx
│   │   │   └── UpgradePrompt.tsx
│   │   └── shared/
│   │       ├── MapPicker.tsx    # Leaflet map with draggable pin
│   │       ├── PhoneInput.tsx   # Country code + phone with validation
│   │       ├── OTPInput.tsx     # 6-digit OTP boxes
│   │       ├── FileUpload.tsx   # Drag-and-drop with preview
│   │       └── VideoPlayer.tsx  # Reel player component
│   ├── layouts/
│   │   ├── LandingLayout.tsx    # Navbar + content + footer (no sidebar)
│   │   └── PortalLayout.tsx     # Sidebar + topbar + content area
│   ├── pages/
│   │   ├── landing/
│   │   │   └── LandingPage.tsx  # The WOW page
│   │   ├── auth/
│   │   │   ├── LoginPage.tsx    # Phone OTP login
│   │   │   └── VerifyOTPPage.tsx
│   │   ├── onboarding/
│   │   │   ├── ClaimSearchPage.tsx    # Find your business
│   │   │   ├── ClaimVerifyPage.tsx    # OTP or photo upload
│   │   │   ├── ProfileSetupPage.tsx   # Complete business profile
│   │   │   └── WelcomePage.tsx        # Setup complete, go to dashboard
│   │   ├── dashboard/
│   │   │   └── DashboardPage.tsx      # Main vendor dashboard
│   │   ├── profile/
│   │   │   └── ProfileEditPage.tsx    # Edit business info, hours, services
│   │   ├── discounts/
│   │   │   └── DiscountsPage.tsx      # Discount management (calendar + list)
│   │   ├── analytics/
│   │   │   └── AnalyticsPage.tsx      # Tier-gated analytics
│   │   ├── voicebot/
│   │   │   └── VoiceBotPage.tsx       # Voice bot configuration
│   │   ├── reels/
│   │   │   └── ReelsPage.tsx          # Reel management + upload
│   │   └── subscription/
│   │       └── SubscriptionPage.tsx   # Plan management + Stripe
│   ├── store/
│   │   ├── authStore.ts         # Vendor auth (OTP-based)
│   │   ├── vendorStore.ts       # Current vendor data
│   │   └── uiStore.ts           # Sidebar, toast queue, modals
│   ├── api/
│   │   ├── client.ts            # Axios instance + JWT interceptor
│   │   ├── auth.ts              # OTP send/verify, refresh, logout
│   │   ├── vendor.ts            # Profile CRUD, claim flow
│   │   ├── discounts.ts         # Discount CRUD
│   │   ├── analytics.ts         # Analytics endpoints
│   │   ├── voicebot.ts          # Voice bot config
│   │   ├── reels.ts             # Reel management
│   │   ├── subscription.ts      # Subscription + Stripe checkout
│   │   └── landing.ts           # Public landing page data
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useVendor.ts
│   │   ├── useFeatureGate.ts    # Check vendor_has_feature for UI gating
│   │   ├── useToast.ts
│   │   ├── useDebounce.ts
│   │   └── useIntersectionObserver.ts  # Landing page scroll animations
│   ├── types/
│   │   ├── vendor.ts
│   │   ├── discount.ts
│   │   ├── subscription.ts
│   │   ├── analytics.ts
│   │   └── auth.ts
│   ├── utils/
│   │   ├── formatters.ts        # Date, currency, phone masking
│   │   ├── validators.ts        # Zod schemas
│   │   └── constants.ts         # Tier names, feature lists
│   └── main.tsx                 # Imports dls-tokens.css FIRST
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── vercel.json                  # Deployment config
```

### 6.2 Routing

```
/                              → LandingPage (public, no auth required)
/login                         → LoginPage (phone input)
/verify                        → VerifyOTPPage (6-digit code)
/onboarding/search             → ClaimSearchPage (find your business)
/onboarding/verify/:vendorId   → ClaimVerifyPage (OTP or photo upload)
/onboarding/setup              → ProfileSetupPage (complete profile)
/onboarding/welcome            → WelcomePage (setup complete)
/portal/dashboard              → DashboardPage
/portal/profile                → ProfileEditPage
/portal/discounts              → DiscountsPage
/portal/analytics              → AnalyticsPage
/portal/voice-bot              → VoiceBotPage
/portal/reels                  → ReelsPage
/portal/subscription           → SubscriptionPage
```

**Route Guards:**
- `/` → always accessible (public landing page)
- `/login`, `/verify` → redirect to `/portal/dashboard` if already authenticated
- `/onboarding/*` → only for authenticated vendors without a claimed business
- `/portal/*` → only for authenticated vendors with a claimed business
- Unauthenticated access to `/portal/*` → redirect to `/login`

---

## 7. VENDOR PORTAL LANDING PAGE — WOW FACTOR

### Design Philosophy: Airbnb Design System

The landing page must make any first-time visitor's immediate reaction: **"WOW"**.

**Core Principles (from Airbnb DLS):**
- **Clean whitespace** — generous spacing, never cramped
- **Bold typography** — DM Sans at large sizes, strong hierarchy
- **Smooth interactions** — buttery scroll animations, micro-interactions
- **Card-based layouts** — information in digestible chunks
- **Minimal content** — only what's necessary, nothing extra
- **Full-bleed imagery/video** — hero section spans full viewport

### 7.1 Hero Section

```
┌─────────────────────────────────────────────────────────┐
│  [Transparent Navbar: AirAd Logo | How It Works | Pricing | Login CTA]  │
│                                                         │
│          ┌──────────────────────────────┐               │
│          │                              │               │
│          │    AUTO-PLAYING VIDEO OR      │               │
│          │    ANIMATED SLIDES            │               │
│          │                              │               │
│          │    Showing:                   │               │
│          │    1. AR view of street       │               │
│          │       with vendor bubbles     │               │
│          │    2. Vendor dashboard        │               │
│          │       with real analytics     │               │
│          │    3. Customer discovering    │               │
│          │       a nearby discount       │               │
│          │                              │               │
│          └──────────────────────────────┘               │
│                                                         │
│     "Your Business, Discovered by Everyone Nearby"       │
│                                                         │
│     Customers are walking past your door right now.      │
│     AirAd puts your business in their camera view.       │
│                                                         │
│              [ Claim Your Business — Free ]               │
│                                                         │
│         ↓ Scroll to learn more                           │
└─────────────────────────────────────────────────────────┘
```

**Hero Specifications:**
- Full viewport height (100vh)
- Background: gradient overlay on video/slides (dark → transparent bottom)
- Video: 15-30 second loop showing AirAd in action (auto-generated content, NOT placeholder)
  - Slide 1: Phone camera showing AR bubbles floating over real street (3D mockup)
  - Slide 2: Vendor dashboard with real-looking analytics data
  - Slide 3: Customer tapping discount badge, getting directions
- Headline: 56px bold, white text
- Subheadline: 20px regular, white/light grey
- CTA Button: `--color-rausch`, 56px height, 24px font, rounded 28px
- Navbar: transparent on top, becomes solid white with shadow on scroll
- Smooth parallax scroll effect on the video/slides

### 7.2 How It Works Section

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│               How AirAd Works for You                   │
│                                                         │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐        │
│    │    📍    │    │    🎯    │    │    📈    │        │
│    │          │    │          │    │          │        │
│    │  Claim   │───→│  Promote │───→│  Grow    │        │
│    │          │    │          │    │          │        │
│    │ Find your│    │ Create   │    │ Watch    │        │
│    │ business │    │ discounts│    │ customers│        │
│    │ & claim  │    │ & reels  │    │ find you │        │
│    │ it free  │    │ in mins  │    │ via AR   │        │
│    └──────────┘    └──────────┘    └──────────┘        │
│                                                         │
│    Step numbers animate in on scroll (Framer Motion)    │
│    Each card has hover lift effect                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Specifications:**
- 3 steps in horizontal cards (stack vertically on mobile)
- Large step number (1, 2, 3) with animated count-up on scroll into view
- Icon above each step (lucide-react, 48px, rausch color)
- Bold title + 2-line description per step
- Animated connector arrows between steps (SVG path animation)
- Scroll-triggered fade-in + slide-up animation (Framer Motion + Intersection Observer)

### 7.3 Subscription Tiers Preview Section

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│            Choose Your Visibility Level                  │
│                                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     │
│  │ SILVER  │ │  GOLD   │ │ DIAMOND │ │PLATINUM │     │
│  │  Free   │ │ ₨3,000  │ │ ₨7,000  │ │₨15,000  │     │
│  │         │ │  /month  │ │  /month  │ │ /month  │     │
│  │ • 1 reel│ │ • 3 reels│ │ • 6 reels│ │•Unlimited│    │
│  │ • Basic │ │ • Boost  │ │ • High   │ │•Dominant │    │
│  │   AR    │ │   AR     │ │  Priority│ │  Zone    │    │
│  │ • Basic │ │ • Voice  │ │ • Dynamic│ │•Advanced │    │
│  │  metrics│ │   intro  │ │   voice  │ │  voice   │    │
│  │         │ │ •Verified│ │ •Premium │ │•Elite+   │    │
│  │         │ │   badge  │ │  badge   │ │  Crown   │    │
│  │         │ │         │ │         │ │         │     │
│  │[Claim   ]│ │[Upgrade ]│ │[Upgrade ]│ │[Upgrade ]│    │
│  │[Free    ]│ │[Now     ]│ │[Now     ]│ │[Now     ]│    │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘     │
│                                                         │
│  DIAMOND card highlighted with "Most Popular" badge     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Specifications:**
- 4 pricing cards in horizontal layout (scroll on mobile)
- Diamond card: slightly larger, `--color-rausch` border, "Most Popular" ribbon badge
- Feature list with ✅/❌ icons per tier
- Animated price counter on scroll into view (react-countup)
- Hover effect: card lifts with shadow, CTA button becomes more prominent
- "Compare all features" expandable section below cards
- All prices in PKR with currency symbol

### 7.4 Social Proof / Stats Section

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│       Background: subtle gradient or pattern             │
│                                                         │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│    │  2,500+  │  │   15+    │  │  50,000+ │           │
│    │ Active   │  │ Cities   │  │ Monthly  │           │
│    │ Vendors  │  │ Covered  │  │ AR Views │           │
│    └──────────┘  └──────────┘  └──────────┘           │
│                                                         │
│    Numbers animate with countUp on scroll               │
│                                                         │
│    ┌─────────────────────────────────────────┐          │
│    │ "Since joining AirAd, my daily walk-ins │          │
│    │  increased by 40%. The AR discovery is  │          │
│    │  game-changing for small shops."         │          │
│    │                                          │          │
│    │  — Ahmad, Pizza Hub, F-10 Islamabad     │          │
│    └─────────────────────────────────────────┘          │
│                                                         │
│    Testimonial cards in horizontal carousel              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Specifications:**
- 3 stat counters with animated count-up (react-countup with Intersection Observer)
- Stats fetched from `/api/v1/vendor-portal/landing/stats/` (real data)
- Testimonial carousel (Swiper): 3-5 vendor stories with photo, name, business, location
- Subtle background pattern or gradient for visual separation
- Trust badges: "Trusted by 2,500+ vendors", "Available in 15+ cities"

### 7.5 Final CTA Section

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│    Full-width section with AirAd rausch gradient BG     │
│                                                         │
│         Ready to Be Discovered?                         │
│                                                         │
│    Join thousands of vendors already growing             │
│    their business with AirAd. It's free to start.       │
│                                                         │
│         [ Claim Your Business Now — Free ]               │
│                                                         │
│    White CTA button on rausch background                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 7.6 Footer

- AirAd logo + tagline
- Links: About, Privacy Policy, Terms of Service, Contact, Help Center
- Social media icons (placeholder links)
- "© 2026 AirAd. All rights reserved."

### 7.7 Landing Page Performance Requirements

| Metric | Target |
|---|---|
| First Contentful Paint (FCP) | < 1.5s |
| Largest Contentful Paint (LCP) | < 2.5s |
| Time to Interactive (TTI) | < 3.0s |
| Cumulative Layout Shift (CLS) | < 0.1 |
| Lighthouse Score | ≥ 90 |

**Optimizations:**
- Video: lazy-load, compressed MP4 + WebM fallback
- Images: WebP with JPEG fallback, responsive srcset
- Fonts: DM Sans preloaded, subset for landing page
- Above-the-fold CSS inlined
- Components lazy-loaded below fold
- SEO: proper meta tags, Open Graph, structured data

---

## 8. VENDOR PORTAL SUBSCRIPTION MODULE — STRIPE

### 8.1 Subscription Page Layout

```
┌─────────────────────────────────────────────────────────┐
│  Current Plan Card                                      │
│  ┌─────────────────────────────────────────┐            │
│  │ 💎 DIAMOND Plan                         │            │
│  │ Active until March 15, 2026             │            │
│  │                                          │            │
│  │ Features: ✅ 6 Reels  ✅ 3 Happy Hours  │            │
│  │           ✅ Dynamic Voice Bot           │            │
│  │           ✅ Advanced Analytics          │            │
│  │                                          │            │
│  │ Usage This Month:                        │            │
│  │ ████████░░  Reels: 4/6                   │            │
│  │ ██████░░░░  Happy Hours Today: 2/3       │            │
│  │                                          │            │
│  │ [ Manage Subscription ]  [ View Invoice ]│            │
│  └─────────────────────────────────────────┘            │
│                                                         │
│  Upgrade / Compare Plans                                │
│  ┌─────────────────────────────────────────┐            │
│  │ [Comparison table with all 4 tiers]      │            │
│  │ Current plan highlighted                 │            │
│  │ Upgrade buttons on higher tiers          │            │
│  │ Downgrade link on lower tiers            │            │
│  └─────────────────────────────────────────┘            │
│                                                         │
│  Billing History                                        │
│  ┌─────────────────────────────────────────┐            │
│  │ Date     │ Plan    │ Amount  │ Invoice   │           │
│  │ Feb 15   │ Diamond │ ₨7,000  │ [Download]│           │
│  │ Jan 15   │ Gold    │ ₨3,000  │ [Download]│           │
│  └─────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

### 8.2 Stripe Checkout Flow

```
1. Vendor clicks "Upgrade to Gold" (or Diamond/Platinum)
       ↓
2. Frontend calls POST /api/v1/payments/create-checkout/
   Body: { package_level: "GOLD" }
       ↓
3. Backend creates Stripe Checkout Session, returns session URL
       ↓
4. Frontend redirects to Stripe Checkout (hosted page)
       ↓
5. Vendor completes payment on Stripe
       ↓
6. Stripe redirects to /portal/subscription?success=true
       ↓
7. Backend receives webhook: checkout.session.completed
   → Creates VendorSubscription
   → Updates vendor.subscription_level
   → Sends confirmation notification
       ↓
8. Frontend shows success state with confetti animation 🎉
   → Plan card updates to new tier
   → New features immediately accessible
```

### 8.3 Stripe Integration Components

```tsx
// SubscriptionPage.tsx key components:

<CurrentPlanCard />           // Shows current tier, usage, expiry
<PlanComparisonTable />       // 4 columns, feature rows, CTA buttons
<StripeCheckoutButton />      // Creates checkout session + redirects
<BillingHistory />            // Invoice table with download links
<CancelSubscriptionModal />   // Confirm cancellation, type business name
<DowngradeConfirmModal />     // Show features that will be lost
<UpgradeSuccessAnimation />   // Confetti + new plan card
```

### 8.4 Subscription Management Features

- **Upgrade:** Immediate — Stripe prorates the amount
- **Downgrade:** At end of current billing period — show what features will be lost
- **Cancel:** At end of current billing period — survey modal asking why
- **Resume:** If cancelled but period not ended — simple re-enable
- **Past Due:** Warning banner + "Update Payment Method" via Stripe Customer Portal
- **Invoice Download:** Link to Stripe-hosted invoice PDF

---

## 9. VENDOR PORTAL CLAIM FLOW

### Design: Simple, Location-First, Maximum 3-4 Steps

### Step 1: Location Detection + Nearby Listings

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│    🔍 Find Your Business                                │
│                                                         │
│    [Search by business name or area ___________]        │
│                                                         │
│    — OR —                                               │
│                                                         │
│    📍 Businesses Near You (auto-detected GPS)           │
│                                                         │
│    ┌──── Map View ─────┐  ┌──── List View ────┐        │
│    │  [Toggle: Map/List] │  │                   │        │
│    │                     │  │ Pizza Hub - 80m   │        │
│    │   📍 User Location  │  │ Cafe Bliss - 120m │        │
│    │   🔴 Unclaimed pins │  │ Quick Mart - 200m │        │
│    │                     │  │ Fresh Bites - 350m│        │
│    └─────────────────────┘  └───────────────────┘        │
│                                                         │
│    Each listing shows: Name, Address, Distance,         │
│    "Unclaimed" badge, [Claim This Business] button      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Specifications:**
- On page load: request GPS permission → auto-detect location
- Show nearby unclaimed listings on map (red pins) AND in list view
- Toggle between map and list views
- Search bar for manual search by business name or area
- Each listing card: business name, address, distance, unclaimed badge
- "Claim This Business" button on each card
- If business not found: "Register New Business" link at bottom

### Step 2: Claim Verification (2 Options)

**Option A — OTP Verification (if phone on file):**
```
We'll send a verification code to the phone number
registered with this business: ****4567

[ Send OTP ]

Enter the 6-digit code:
[_] [_] [_] [_] [_] [_]

Didn't receive? Resend in 45s
```

**Option B — Manual Verification (if no phone):**
```
Upload verification for: Pizza Hub, F-10 Islamabad

📸 Upload Storefront Photo
   (Photo must show business name clearly)
   [Drag & drop or click to upload]

📄 Business License (Optional — speeds up approval)
   [Drag & drop or click to upload]

[ Submit for Review ]

Manual verification takes up to 24 hours.
We'll notify you when approved.
```

### Step 3: Profile Completion (Post-Verification)

```
Almost done! Complete your profile:

✅ Business Name: Pizza Hub        (pre-filled, editable)
✅ Category: Pizza, Fast Food       (pre-assigned, confirm/edit)
⬜ Business Hours: [ Set Hours ]    (visual weekly grid)
⬜ Upload Logo (optional)           [ Upload ]
⬜ Upload Cover Photo (optional)    [ Upload ]

Profile Completeness: 60% ██████░░░░

[ Complete Setup — Go Live! ]
```

### Step 4: Activation

```
🎉 You're Live on AirAd!

Your business is now visible to thousands of
nearby customers through AR discovery.

You're on the Silver (Free) plan.

📊 Views this week: 0 (just getting started!)

[ Go to Dashboard ]

💡 Tip: Upload your first reel to get 3x more views!
   [ Upload a Reel ]

Want more visibility? See upgrade options →
```

---

## 10. VENDOR PORTAL DASHBOARD & FEATURES

### 10.1 Dashboard Page

```
┌─────────────────────────────────────────────────────────┐
│  Sidebar              │  Main Content                   │
│  ┌──────────┐         │                                 │
│  │ 🏪 AirAd │         │  Good morning, Ahmad! 👋        │
│  │          │         │                                 │
│  │ Dashboard│●        │  ┌───────┐ ┌───────┐ ┌───────┐│
│  │ Profile  │         │  │  234  │ │   12  │ │    5  ││
│  │ Discounts│         │  │ Views │ │ Taps  │ │ Navs  ││
│  │ Reels    │         │  │ +15%↑ │ │ +8%↑  │ │ +20%↑ ││
│  │ Analytics│         │  └───────┘ └───────┘ └───────┘│
│  │ Voice Bot│🔒       │                                 │
│  │ Plan     │         │  Profile Completeness           │
│  │          │         │  ████████░░ 80%                  │
│  │ ─────── │         │  Missing: Cover Photo, Reel      │
│  │ 💎 Diamond│        │                                 │
│  │ Renews   │         │  Active Discounts (2)            │
│  │ Mar 15   │         │  ┌─────────────────────────┐    │
│  └──────────┘         │  │ 20% OFF — Happy Hour     │    │
│                       │  │ Active now, ends 5:00 PM  │    │
│                       │  └─────────────────────────┘    │
│                       │                                 │
│                       │  Quick Actions                   │
│                       │  [ + New Discount ] [ Upload Reel│]
│                       │                                 │
│                       │  This Week's Performance         │
│                       │  [Mini bar chart — 7 days]       │
│                       │                                 │
└─────────────────────────────────────────────────────────┘
```

**Progressive Activation Overlay (§3.2):**

The dashboard adapts based on `activation_stage` from the backend API:

```
Stage: CLAIM (Day 0-3)
  → Show only: Views count, Profile Completeness, Upload Reel CTA
  → Grey overlay on Discounts/Analytics/Voice Bot sidebar items
  → Banner: "Complete your profile and upload your first reel to unlock more features!"
  → Progress: "Step 1 of 3: Upload a reel" → "Step 2: Set business hours" → "Step 3: Explore!"

Stage: ENGAGEMENT (Day 3+)
  → Unlock: Discount creation, basic analytics, voice intro (Gold+)
  → Banner: "You're getting noticed! Create your first discount to attract more customers."
  → Guided tooltip on Discounts nav item (first time)

Stage: MONETIZATION (Day 7+)
  → Unlock: Upgrade prompts visible, analytics teaser for higher tiers
  → ROI card: "Your listing drove 340 views this week. Gold vendors get 3x more."
  → Upgrade CTA in sidebar bottom area

Stage: GROWTH / RETENTION (Day 14+)
  → Full dashboard — all features unlocked per subscription tier
  → No activation restrictions
```

**Implementation:**
- `useActivationStage()` hook reads from dashboard API response
- `<ActivationGate stage="ENGAGEMENT">` wrapper component — shows content or locked state
- Locked items: grey overlay + lock icon + "Unlock in X days" or "Upload a reel to unlock"
- Transitions trigger confetti micro-animation (Framer Motion)

### 10.2 Portal Sidebar Navigation

```
Sidebar items (with subscription-aware visibility):

📊 Dashboard           → Always visible
🏪 My Business         → Always visible (profile editing)
🎬 Reels               → Always visible (with tier limit display)
🏷️ Discounts           → Always visible (with tier limit display)
📈 Analytics           → Always visible (tier-gated content)
🎙️ Voice Bot           → Gold+ (locked icon + upgrade prompt for Silver)
💳 Subscription        → Always visible

Bottom of sidebar:
- Current plan badge (color-coded: Silver grey, Gold yellow, Diamond blue, Platinum purple)
- Renewal date
- "Upgrade" button (if not Platinum)
```

### 10.3 Discount Management Page

**Calendar View:**
- Monthly calendar with colored blocks for active/scheduled/expired discounts
- Toggle between calendar view and list view
- Color coding: Active = solid babu, Scheduled = dashed border, Expired = grey

**Create Discount (Drawer — 4 Steps):**
1. **Type Selection:** Large visual cards with emoji icons (Flat, %, BOGO, Happy Hour, Item-Specific, Flash)
2. **Details:** Conditional fields based on type, live preview of AR badge, slider for % value
3. **Scheduling:** Datetime pickers, recurring day selector chips, duration presets
4. **Confirm:** Summary card showing everything, preview of how it looks in AR

**Discount Performance Table:**
- Title, Type, Schedule, Views During Campaign, Status badge
- Click row → detailed analytics for that campaign

**Tier Enforcement UI:**
- "Happy Hours used today: 1/3" progress bar (Diamond)
- Silver trying to create Happy Hour: upgrade prompt modal
- Subscription limit always visible at top of page

### 10.4 Analytics Page (Tier-Gated)

**All Tiers:**
- Hero metric: "Viewed 234 times this week" with trend arrow
- 3 metric cards: Views, Profile Taps, Navigation Clicks (with % change)
- Bar chart: daily views over last 14 days

**Gold+:**
- Hourly breakdown table
- Day-of-week analysis
- Navigation clicks detail
- Promotion ROI (basic: views during vs outside campaign)

**Diamond+:**
- Time-of-day heatmap (7×24 grid, color intensity)
- Voice query stats (if voice bot configured)
- Conversion estimates
- Reel performance: per-reel views, completion rate

**Platinum:**
- Predictive insights: 3 recommendation cards with actionable CTAs
- Competitor benchmarking: area comparison (anonymized)
- Demand forecasting chart

**Gating UI:**
- Silver/Gold seeing Diamond features: blurred overlay with "Upgrade to Diamond to unlock hourly insights"
- Clickable blur → opens upgrade modal with comparison

### 10.5 Voice Bot Page (Gold+ Feature)

**Silver — Locked State:**
```
🔒 Voice Bot — Available from Gold Plan

Listen to how voice bot works for your business:
[▶️ Play Demo Audio]

When customers ask "Does Pizza Hub deliver?",
your voice bot answers automatically.

[ Upgrade to Gold — ₨3,000/month ]
```

**Gold — Basic Voice Bot:**
- Intro message editor (text input, max 200 chars)
- Preview: "Play intro" button

**Diamond+ — Full Configuration:**
- Split panel: Left = configuration, Right = live test
- Left panel:
  - Menu Items: dynamic list (name, price, available toggle, category)
  - Delivery Info: radius, charges, free delivery zones
  - Hours Summary: auto-generated, read-only
  - Custom Q&A Pairs: question + answer list (add/remove)
- Right panel:
  - "Ask a question" input field
  - POST to voice-query API → show response
  - Last 5 test query history
  - Completeness Score: "Your voice bot is 75% configured"
  - Missing items highlighted in yellow

### 10.6 Reel Management Page

- Vertical list: thumbnail, title, view count, upload date, status badge
- Drag-and-drop reorder
- Upload limit progress: "4 of 6 reels uploaded" (Diamond)
- Silver at limit: upload button disabled + "Upgrade to Gold for 3 reels"
- Upload flow: click "Add Reel" → file picker → title input → upload with progress bar
- Processing state: "Processing" badge until backend confirms
- Delete: confirmation modal → soft archive

### 10.7 Profile Edit Page

- Business info: name, description (character count), phone (masked), website
- Business Hours: visual weekly grid — click cells to toggle open/close per day
- Service Options: toggle cards for delivery + pickup with description fields
- Location: map embed showing current location + "Request Location Change" button
- Profile Completeness Widget: persistent progress bar in sidebar, incomplete items list
- Logo + Cover Photo upload: drag-and-drop with preview, crop/resize

---

## 11. BUILD SEQUENCE & SESSIONS

### Admin Portal Stabilization (1 Session)

| Session | Goal |
|---|---|
| FE-S1 | Fix React Router warnings, dashboard timestamps, logout handling, cache invalidation |

### Admin Portal Phase B Extensions (2 Sessions)

| Session | Goal |
|---|---|
| FE-S2 | Claim Review Queue, Content Moderation page |
| FE-S3 | Subscription Overview, Notification Management, Dashboard extensions |

### Vendor Portal Build (8 Sessions)

| Session | Goal |
|---|---|
| VP-S1 | Project setup, DLS components (copy + adapt), landing page layout + Navbar + Footer |
| VP-S2 | Landing page: Hero (video/slides), How It Works, Tiers Preview — full WOW experience |
| VP-S3 | Landing page: Social Proof, Final CTA + auth pages (Login + OTP) + Zustand auth store |
| VP-S4 | Claim flow: search page (map + list), claim verification, profile setup, welcome page |
| VP-S5 | Portal layout + sidebar + Dashboard page + Profile Edit page |
| VP-S6 | Discount Management (calendar + list + create drawer) + Reel Management |
| VP-S7 | Analytics page (all tier levels) + Voice Bot page (all tiers) |
| VP-S8 | Subscription page (Stripe checkout + plan comparison + billing history) + final polish |

### Session Dependencies

```
FE-S1 → FE-S2 → FE-S3 (Admin sequential)

VP-S1 → VP-S2 → VP-S3 (Landing + Auth)
                      ↓
                    VP-S4 (Claim flow — needs backend claim APIs)
                      ↓
                    VP-S5 (Dashboard — needs backend dashboard API)
                      ↓
              VP-S6 + VP-S7 (parallel — independent features)
                      ↓
                    VP-S8 (Subscription — needs Stripe backend)
```

### Gates

**Gate: Admin Portal Complete**
- [ ] All existing pages working with no console errors
- [ ] Phase B admin pages (claims, moderation, subscriptions, notifications) complete
- [ ] All tables have empty state + skeleton loading
- [ ] All forms validate with clear error messages
- [ ] WCAG AA contrast verified
- [ ] Keyboard navigation working on all interactive elements

**Gate: Vendor Portal Landing Page**
- [ ] WOW factor validated — first impression is compelling
- [ ] Video/slides auto-play and communicate what AirAd is
- [ ] Lighthouse score ≥ 90
- [ ] Mobile responsive (all breakpoints)
- [ ] All scroll animations smooth
- [ ] CTA leads to login/signup

**Gate: Vendor Portal Complete**
- [ ] Login → Claim → Dashboard flow working end-to-end
- [ ] All subscription tiers correctly gate all features
- [ ] Stripe checkout → success → plan update working
- [ ] Discount CRUD with tier enforcement working
- [ ] Voice bot configuration (all tiers) working
- [ ] Analytics showing real data with correct tier gating
- [ ] Reel upload + management working
- [ ] Profile edit with completeness tracking working
- [ ] Mobile responsive on all portal pages
- [ ] AirAd branding consistent on every page

---

## 12. QUALITY GATE CHECKLIST

### DLS Compliance

- [ ] No hardcoded hex colors — CSS custom properties only
- [ ] `--color-rausch` primary button: max 1 per view
- [ ] DM Sans typography everywhere
- [ ] 8px spacing grid — no arbitrary values
- [ ] lucide-react icons only, stroke-width: 1.5
- [ ] All tables: empty state + skeleton loading (never spinners)
- [ ] `prefers-reduced-motion` respected

### Accessibility (WCAG 2.1 AA)

- [ ] 4.5:1 contrast ratio for body text
- [ ] 3:1 contrast ratio for large text
- [ ] All interactive elements keyboard navigable with visible focus ring
- [ ] No icon-only buttons without `aria-label`
- [ ] Skip-to-main-content link as first focusable element
- [ ] Screen reader labels on all tables
- [ ] Focus trap in all modals and drawers

### Performance

- [ ] Landing page Lighthouse ≥ 90
- [ ] Code splitting: each route lazy-loaded
- [ ] Images: WebP with fallback, responsive srcset
- [ ] TanStack Query: staleTime configured, no unnecessary refetches
- [ ] Skeleton loading on initial load, never blocking spinners

### Security (Frontend)

- [ ] JWT stored in httpOnly cookie (never localStorage for web)
- [ ] OTP input: no autocomplete, masked display
- [ ] Phone numbers always displayed masked
- [ ] No sensitive data in URL parameters
- [ ] CSRF protection on all forms
- [ ] Stripe publishable key only (never secret key) in frontend
- [ ] API error messages: never expose internal details to user

### Vendor Portal Specific

- [ ] Landing page communicates AirAd value in < 10 seconds
- [ ] Claim flow completes in ≤ 4 steps
- [ ] Feature gating shows upgrade prompt (never empty/broken state)
- [ ] Subscription tier badge visible throughout portal
- [ ] Profile completeness always visible and actionable
- [ ] AirAd branding (colors, logo, typography) on EVERY page

### Functional Document Compliance

- [ ] All 4 vendor types supported (Food, Retail, Service, Micro-Vendor)
- [ ] All 4 vendor account states displayed correctly (Unclaimed, Claimed, Suspended, Closed)
- [ ] Full feature matrix enforced (§4.2 from vendor functional doc)
- [ ] AR visibility ranking formula reflected in analytics display
- [ ] All 6 discount types supported (§5.1)
- [ ] Happy hour management with tier limits (§5.2)
- [ ] Free delivery campaigns with tier limits (§5.3)
- [ ] Voice bot tiers correctly implemented (§6.1)
- [ ] Analytics access levels enforced per tier (§7.1)
- [ ] Churn prevention triggers handled (§8.2)
- [ ] Content moderation policies enforced (§9.1)
- [ ] Discount authenticity validation (§9.2)

---

**— End of Frontend Master Plan —**
