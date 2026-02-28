# USER PORTAL FRONTEND PLAN — PART 1
## AirAds User Portal — React 18 + TypeScript + Vite — Design System, Landing Page, Auth, Discovery Shell, AR View

This plan defines the complete frontend architecture for the AirAds User Portal — a standalone React 18 + TypeScript + Vite application located at `airaad/user-portal/`, serving end customers who discover nearby vendors via AR, voice, map, and tag browsing.

---

## TABLE OF CONTENTS (Part 1)

1. [Application Identity & Separation Strategy](#1-application-identity)
2. [Tech Stack & Project Structure](#2-tech-stack)
3. [Design System — AirAds DLS for User Portal](#3-design-system)
4. [Component Library](#4-component-library)
5. [State Management & Data Fetching Strategy](#5-state-management)
6. [Routing Architecture](#6-routing-architecture)
7. [Landing Page — WOW Factor](#7-landing-page)
8. [Authentication Pages](#8-authentication-pages)
9. [Discovery Home Shell](#9-discovery-home-shell)
10. [AR Discovery View](#10-ar-discovery-view)

> **Part 2 covers:** Map View, List View, Voice Search UI, Tag Browsing, Vendor Profile, Deals Tab, Reels Feed, Navigation, Preferences, Responsive Strategy, Performance Targets, Accessibility, Guest vs Logged-In Mode, Build Sequence, QA Checklist.

---

## 1. APPLICATION IDENTITY & SEPARATION STRATEGY

### This is a Third, Completely Separate Application

AirAds now has three frontend applications:
- `airaad/frontend/` — Admin Portal (`admin.airad.pk`)
- `airaad/vendor-portal/` — Vendor Portal (`vendor.airad.pk`)
- `airaad/user-portal/` — **User Portal** (`app.airad.pk`) ← THIS PLAN

### Non-Negotiable Separations

| Rule | Reason |
|---|---|
| Login URL is `/user/login` — never `/login` | `/login` belongs to Vendor Portal |
| Separate auth store (customer JWT only) | Cannot share tokens with Vendor or Admin |
| Separate DLS token file (same values, new file) | User portal may diverge in future |
| No import of Vendor Portal components | Different design language for AR/discovery UI |
| Separate `.env` file with `VITE_API_BASE_URL` | Different env vars namespace |

### URL Strategy

```
Public (no auth):      /                → Landing Page
                       /user/login      → Login
                       /user/register   → Register
Discovery (guest OK):  /discover        → Discovery Home (AR default)
                       /deals           → Active Deals Tab
                       /reels           → Reels Feed
                       /browse          → Tag Browser
                       /vendor/:id      → Vendor Profile
                       /navigate/:id    → In-app navigation
Settings:              /preferences     → User Preferences
```

---

## 2. TECH STACK & PROJECT STRUCTURE

### Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Framework | React 18 + TypeScript 5 | Same as existing portals — consistency |
| Build Tool | Vite 5 | Fast HMR, same as existing |
| Routing | React Router v6 (future flags enabled) | Same as existing |
| State | Zustand | Same as existing — lightweight |
| Data Fetching | TanStack Query v5 | Same as existing — caching + background refetch |
| HTTP Client | Axios with interceptors | Same as existing — JWT refresh handling |
| Animations | Framer Motion | Required for AR markers, landing page, voice waves |
| Maps | Mapbox GL JS | Required for map view with custom pins |
| AR | Custom (WebXR + DeviceOrientationEvent) | No 3rd party — custom implementation |
| Icons | Lucide React | Same as existing |
| Typography | DM Sans (Google Fonts) | Specified in master prompt |
| Styling | CSS Modules + CSS Custom Properties | Same pattern as existing portals |
| Voice | Web Speech API (SpeechRecognition + SpeechSynthesis) | Browser-native, no cost |

### Project Structure

```
airaad/user-portal/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
├── .env.example
├── public/
│   └── airad_icon.png
└── src/
    ├── main.tsx                    ← App entry, env validation, font load, theme init, SW registration, Sentry init
    ├── router.tsx                  ← All routes, lazy loading, guards
    ├── vite-env.d.ts
    │
    ├── styles/
    │   ├── dls-tokens.css          ← Brand tokens (dark + light theme variables)
    │   ├── global.css              ← Reset, base styles, DM Sans Google Fonts import
    │   ├── shared.css              ← Utility classes (no inline styles rule)
    │   └── animations.css         ← Keyframe animations (float, pulse, shimmer, glow)
    │
    ├── api/                        ← All API calls — one file per domain
    │   ├── client.ts               ← Axios instance with interceptors
    │   ├── auth.ts                 ← Guest token, register, login, refresh, delete
    │   ├── discovery.ts            ← Nearby, AR markers, map pins, search
    │   ├── voiceSearch.ts          ← Voice query API
    │   ├── tags.ts                 ← Tag browser API
    │   ├── vendors.ts              ← Vendor profile, reels, voice bot, nearby
    │   ├── deals.ts                ← Active deals nearby, deal detail
    │   ├── reels.ts                ← Reels feed
    │   ├── preferences.ts          ← User preferences CRUD, search history
    │   └── tracking.ts             ← Interaction + reel view tracking (fire-and-forget)
    │
    ├── stores/
    │   ├── authStore.ts            ← CustomerUser state, JWT, guest token
    │   ├── discoveryStore.ts       ← Current location, active filters, view mode
    │   ├── uiStore.ts              ← Theme, loading states, toast queue
    │   └── navigationStore.ts     ← Active navigation session state
    │
    ├── hooks/
    │   ├── useLocation.ts          ← GPS access, permission handling, area name
    │   ├── useAR.ts                ← AR detection, device orientation subscription
    │   ├── useVoice.ts             ← SpeechRecognition abstraction
    │   ├── useGeofence.ts          ← Arrival detection (within 30m of destination)
    │   └── useOffline.ts           ← Online/offline detection + cache fallback
    │
    ├── utils/
    │   ├── formatters.ts           ← Distance, time, countdown, date formatting
    │   ├── geo.ts                  ← Bearing calculation, geohash, Haversine distance
    │   ├── nlp.ts                  ← Client-side query suggestion + intent preview logic
    │   └── constants.ts            ← Query keys, route names, config constants
    │
    ├── components/
    │   ├── dls/                    ← Design Language System (reusable primitives)
    │   │   ├── Button/
    │   │   ├── SearchBar/
    │   │   ├── TagChip/
    │   │   ├── SkeletonLoader/
    │   │   ├── Toast/
    │   │   ├── VoiceWave/
    │   │   ├── DistanceBadge/
    │   │   ├── PromotionBadge/
    │   │   ├── TierBadge/
    │   │   ├── Logo/
    │   │   ├── CountdownTimer/
    │   │   └── OfflineBanner/
    │   │
    │   ├── landing/                ← Landing page sections
    │   │   ├── Navbar/
    │   │   ├── HeroSection/
    │   │   ├── HowItWorksSlider/
    │   │   ├── ThreeModesSection/
    │   │   ├── SocialProofSection/
    │   │   ├── CtaSection/
    │   │   └── Footer/
    │   │
    │   ├── discovery/              ← Discovery-specific components
    │   │   ├── ViewSwitcher/
    │   │   ├── DiscoverySearchBar/
    │   │   ├── LocationContext/
    │   │   ├── PromotionsStrip/
    │   │   └── FilterBar/
    │   │
    │   ├── ar/                     ← AR-specific components
    │   │   ├── ARCanvas/
    │   │   ├── ARMarker/
    │   │   ├── ARCluster/
    │   │   ├── ARCompass/
    │   │   ├── ARRadiusSlider/
    │   │   └── WalkingSafetyOverlay/
    │   │
    │   ├── vendor/                 ← Vendor-related components
    │   │   ├── VendorCard/
    │   │   ├── VendorCardSkeleton/
    │   │   └── VoiceBotSheet/
    │   │
    │   └── navigation/             ← Navigation components
    │       ├── NavigationMap/
    │       ├── NavigationHeader/
    │       └── ArrivalOverlay/
    │
    └── pages/
        ├── landing/LandingPage.tsx
        ├── auth/LoginPage.tsx
        ├── auth/RegisterPage.tsx
        ├── discovery/DiscoveryPage.tsx   ← Shell with view switcher
        ├── discovery/ARView.tsx
        ├── discovery/MapView.tsx
        ├── discovery/ListView.tsx
        ├── browse/TagBrowserPage.tsx
        ├── deals/DealsPage.tsx
        ├── reels/ReelsPage.tsx
        ├── vendor/VendorProfilePage.tsx
        ├── navigate/NavigationPage.tsx
        └── preferences/PreferencesPage.tsx
```

---

## 3. DESIGN SYSTEM — AIROADS DLS FOR USER PORTAL

### 3.1 Brand Identity Source

Colors derived from the AirAds logo — 3 overlapping petals on black (energy=orange, passion=crimson, trust=teal).

### 3.2 CSS Custom Properties — `dls-tokens.css`

```css
:root {
  /* === BRAND COLORS === */
  --brand-orange: #FF8C00;
  --brand-orange-light: #FFB347;
  --brand-orange-dark: #E07800;
  --brand-orange-glow: rgba(255, 140, 0, 0.25);

  --brand-crimson: #C41E3A;
  --brand-crimson-light: #E8425A;
  --brand-crimson-glow: rgba(196, 30, 58, 0.25);

  --brand-teal: #00BCD4;
  --brand-teal-light: #4DD0E1;
  --brand-teal-glow: rgba(0, 188, 212, 0.25);

  --brand-black: #000000;
  --brand-gradient: linear-gradient(135deg, #FF8C00, #C41E3A, #00BCD4);

  /* === SPACING (8px base) === */
  --space-1: 4px;   --space-2: 8px;   --space-3: 12px;
  --space-4: 16px;  --space-5: 20px;  --space-6: 24px;
  --space-8: 32px;  --space-10: 40px; --space-12: 48px;
  --space-16: 64px; --space-20: 80px;

  /* === BORDER RADIUS === */
  --radius-sm: 4px;   --radius-md: 8px;   --radius-lg: 12px;
  --radius-xl: 16px;  --radius-2xl: 24px; --radius-full: 9999px;

  /* === TYPOGRAPHY === */
  --font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-size-xs: 11px; --font-size-sm: 13px; --font-size-md: 15px;
  --font-size-lg: 17px; --font-size-xl: 20px; --font-size-2xl: 24px;
  --font-size-3xl: 32px; --font-size-4xl: 40px; --font-size-5xl: 56px;
  --font-weight-regular: 400; --font-weight-medium: 500;
  --font-weight-semibold: 600; --font-weight-bold: 700;
  --line-height-tight: 1.2; --line-height-base: 1.5;

  /* === TRANSITIONS === */
  --transition-fast: 150ms ease;
  --transition-base: 200ms ease;
  --transition-spring: 400ms cubic-bezier(0.34, 1.56, 0.64, 1);
  --transition-smooth: 300ms cubic-bezier(0.4, 0, 0.2, 1);

  /* === SHADOWS === */
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.4);
  --shadow-lg: 0 8px 32px rgba(0,0,0,0.5);
  --shadow-orange: 0 0 20px var(--brand-orange-glow);
  --shadow-glow-orange: 0 0 40px rgba(255,140,0,0.3);
}
```

### 3.3 Dark Theme (Default — applied via `[data-theme="dark"]` on `<html>`)

```css
[data-theme="dark"], :root {
  --color-bg-page: #0A0A0A;
  --color-bg-surface: #141414;
  --color-bg-elevated: #1E1E1E;
  --color-bg-overlay: rgba(0,0,0,0.85);
  --color-bg-nav: #000000;
  --color-text-primary: #FFFFFF;
  --color-text-secondary: rgba(255,255,255,0.65);
  --color-text-tertiary: rgba(255,255,255,0.40);
  --color-text-disabled: rgba(255,255,255,0.25);
  --color-border: rgba(255,255,255,0.10);
  --color-border-focus: var(--brand-orange);
  --color-focus-ring: 0 0 0 3px rgba(255,140,0,0.35);
  --color-interactive-hover: rgba(255,255,255,0.06);
  --color-success: #00BCD4;
  --color-success-bg: rgba(0,188,212,0.12);
  --color-warning: #FFC107;
  --color-warning-bg: rgba(255,193,7,0.12);
  --color-error: #C41E3A;
  --color-error-bg: rgba(196,30,58,0.12);
  --glass-bg: rgba(20,20,20,0.80);
  --glass-border: rgba(255,255,255,0.12);
  --glass-blur: blur(12px);
}
```

### 3.4 Light Theme

```css
[data-theme="light"] {
  --color-bg-page: #F5F5F5;
  --color-bg-surface: #FFFFFF;
  --color-bg-elevated: #FAFAFA;
  --color-bg-nav: #000000;
  --color-text-primary: #0A0A0A;
  --color-text-secondary: rgba(10,10,10,0.65);
  --color-text-tertiary: rgba(10,10,10,0.40);
  --color-border: rgba(0,0,0,0.10);
  --color-interactive-hover: rgba(0,0,0,0.04);
  --glass-bg: rgba(255,255,255,0.85);
  --glass-border: rgba(0,0,0,0.10);
}
```

### 3.5 Theme Initialization (in `main.tsx`)

1. Read `localStorage.getItem('theme')`
2. If not set: detect `window.matchMedia('(prefers-color-scheme: dark)')`
3. **Default: `'dark'`** (outdoor readability + premium feel per spec)
4. Set `document.documentElement.setAttribute('data-theme', theme)` before React mounts
5. `uiStore` watches changes and reapplies reactively

---

## 4. COMPONENT LIBRARY

### 4.1 Button

Variants: `primary` (gradient orange→crimson), `secondary` (outlined), `ghost` (transparent), `danger` (crimson)
Sizes: `sm` (32px), `md` (40px), `lg` (48px), `xl` (56px — hero CTAs)
States: default, hover, active, disabled, loading (spinner replaces content)
Full-width: `fullWidth` prop — takes 100% of container

### 4.2 SearchBar

Variants: `hero` (64px height, large glow, for landing page), `compact` (44px, sticky in discovery)
Left slot: location pin icon (brand orange), tappable — opens city context
Center: controlled text input, placeholder rotates between suggestions
Right slot: mic button — 40×40px gradient circle, `listening` state triggers pulse animation
Hover: `box-shadow: 0 0 20px var(--brand-orange-glow)`
Focus: `transform: scale(1.01)` + intensified glow
Below bar slot: quick tag chips row (horizontal scroll)

### 4.3 VendorCard

Layout: 88px height, horizontal — thumbnail left (64×64), content center, tier badge right
Content: name (bold), category chip, distance badge, promotion badge OR "No deals" (tertiary)
Active promotion: left border `3px solid var(--brand-orange)` + left-side inner shadow
Hover: `translateY(-2px)` + shadow increase (transition: var(--transition-smooth))
Loading state: `VendorCardSkeleton` — same dimensions, shimmer animation

### 4.4 ARMarker

Shape: glassmorphism rounded pill
Default state: distance (large white), vendor name (bold), category emoji, promotion badge
Promotion badge: pulsing orange glow (`box-shadow: 0 0 12px var(--brand-orange-glow)`, 2s loop)
Scale: proportional to distance — `transform: scale(${1 - distanceFraction * 0.5})`
On tap: Framer Motion `layoutId` spring expand to full card (220ms spring)
Expanded: + category, hours, active promotion full detail, 3 action buttons (Directions / Call / View)
On backdrop tap: collapse back

### 4.5 VoiceWave

5 vertical bars, `framer-motion` animate heights independently (varying timing to avoid sync)
Colors: brand crimson gradient per bar
States: `idle` (static, short bars), `listening` (animated tall), `processing` (slow wave)

### 4.6 SkeletonLoader

Shimmer animation: `background-position` CSS keyframe — moving gradient `rgba(255,255,255,0.05)` → `rgba(255,255,255,0.12)` → `rgba(255,255,255,0.05)`
Variants: `card` (vendor card shape), `text` (line blocks), `circle`, `ar-marker`
Rule: never shows blank white — always shimmer placeholder

### 4.7 CountdownTimer

Props: `endsAt: Date`
Format: `Xh Ym` if > 1h, `Xm Ys` if < 1h
Color states: normal (secondary) → `#FFC107` amber (< 2h) → `var(--brand-crimson)` pulsing (< 1h)
Uses `setInterval` (1s) — auto-stops and calls optional `onExpired` callback

### 4.8 PromotionBadge

Variants: `normal` (brand orange bg), `urgent` (crimson pulsing glow), `flash` (animated flash)
Sizes: `sm` (for vendor cards), `lg` (for vendor profile hero and deal cards)

### 4.9 TierBadge

Silver: `●` grey dot | Gold: `⭐` | Diamond: `💎` teal | Platinum: gradient crown
Sizes: `xs` (dot only, for AR markers), `sm` (icon, vendor cards), `md` (icon + label text)

### 4.10 OfflineBanner

Fixed top bar when `navigator.onLine === false` (detected via `useOffline` hook)
Brand crimson background, message + retry button
Slides down via Framer Motion on disconnect, slides up on reconnect

---

## 5. STATE MANAGEMENT & DATA FETCHING STRATEGY

### 5.1 Zustand Stores

**`authStore.ts`:**
```typescript
{
  mode: 'GUEST' | 'AUTHENTICATED';
  guestToken: string | null;        // localStorage
  accessToken: string | null;       // sessionStorage
  refreshToken: string | null;      // sessionStorage
  user: CustomerUser | null;
  // Actions: setGuest, login, logout, refreshTokens
}
```

**`discoveryStore.ts`** (most frequently written):
```typescript
{
  userLat: number | null;
  userLng: number | null;
  locationPermission: 'unknown' | 'granted' | 'denied';
  areaName: string;                  // "Gulberg III"
  activeView: 'AR' | 'MAP' | 'LIST'; // persisted in localStorage
  activeTagSlugs: string[];
  searchRadius: number;              // meters
  showOpenNowOnly: boolean;
  sortMode: 'relevance' | 'distance' | 'deals';
  searchQuery: string;
  isVoiceActive: boolean;
  // Client-side behavioral learning for ranking personalization
  userBehaviorProfile: {
    preferredCategories: string[];     // Top 3 categories user interacts with
    preferredPriceRange: 'budget' | 'mid' | 'premium' | null;
    interactionHistory: {               // Last 20 interactions for learning
      vendorId: string;
      interactionType: 'VIEW' | 'CALL' | 'NAVIGATE' | 'PROMOTION_TAP';
      timestamp: number;
      outcome: 'positive' | 'negative' | null; // User feedback
    }[];
    timeOfDayPatterns: {                // When user is most active
      morning: number;    // 6-12
      afternoon: number;  // 12-18
      evening: number;    // 18-22
      night: number;      // 22-6
    };
    distancePreference: number;         // Preferred search radius (learned)
  };
}
```

**`uiStore.ts`:**
```typescript
{
  theme: 'DARK' | 'LIGHT' | 'SYSTEM';
  toasts: Toast[];
  isFullscreenReelOpen: boolean;
  // Actions: setTheme, addToast, dismissToast
}
```

**`navigationStore.ts`:**
```typescript
{
  isNavigating: boolean;
  destinationVendorId: string | null;
  destinationName: string | null;
  destinationLat: number | null;
  destinationLng: number | null;
  hasArrived: boolean;
}
```

### 5.2 TanStack Query Keys (`utils/constants.ts`)

```typescript
export const QUERY_KEYS = {
  nearby: (lat, lng, radius, tags) => ['nearby', lat, lng, radius, tags],
  arMarkers: (lat, lng, radius) => ['ar-markers', lat, lng, radius],
  mapPins: (lat, lng, radius, tags) => ['map-pins', lat, lng, radius, tags],
  vendorDetail: (id) => ['vendor', id],
  vendorReels: (id) => ['vendor-reels', id],
  deals: (lat, lng, radius) => ['deals', lat, lng, radius],
  reelsFeed: (lat, lng, page) => ['reels-feed', lat, lng, page],
  tags: (lat, lng) => ['tags', lat, lng],
  flashAlert: (lat, lng) => ['flash-alert', lat, lng],
  promotionsStrip: (lat, lng) => ['promotions-strip', lat, lng], // [AUDIT FIX 1.7] separate from flash-alert
  cities: () => ['cities'],                                       // [AUDIT FIX 1.8] city picker data
  preferences: () => ['preferences'],
  searchHistory: () => ['search-history'],
} as const;
```

**Refetch intervals:**
- AR markers: `refetchInterval: 5000` (5 seconds — live)
- Flash alert: `refetchInterval: 60000` (60 seconds)
- Nearby vendors: `refetchInterval: 30000`
- Deals: `refetchInterval: 60000`
- Vendor detail: `staleTime: 300000` (5 min)

### 5.3 Client-Side Behavioral Ranking Enhancement

> **[AUDIT FIX — CRITICAL]** Behavioral learning must integrate with backend's 5-factor ranking algorithm, not replace it. This enhancement adds personalization on top of the base ranking score.

### Integration with Backend Ranking

The backend provides a `baseRankingScore` from the 5-factor algorithm:
```
Final Score = (Relevance × 0.30) + (Distance × 0.25) + (Active Offer × 0.15) + (Popularity × 0.15) + (Subscription Tier × 0.15)
```

Frontend behavioral enhancement adds a personalization boost:
```typescript
// In src/services/behavioralRanking.ts
interface VendorWithRanking {
  id: string;
  baseRankingScore: number;  // From backend 5-factor algorithm
  // ... other vendor fields
}

interface BehavioralBoost {
  vendorId: string;
  boost: number;  // -0.1 to +0.2 (max ±20% adjustment)
  confidence: number;  // 0.0 to 1.0 based on data volume
  lastUpdated: number;
}

class BehavioralRankingService {
  private boosts: Map<string, BehavioralBoost> = new Map();
  private userInteractions: UserInteraction[] = [];
  
  // Calculate personalization boost based on user behavior
  calculatePersonalizationBoost(vendor: VendorWithRanking): number {
    const boost = this.boosts.get(vendor.id);
    if (!boost) return 0;
    
    // Apply confidence weighting - less confident boosts have smaller impact
    return boost.boost * boost.confidence;
  }
  
  // Final ranking combines backend score + behavioral boost
  getFinalRankingScore(vendor: VendorWithRanking): number {
    const behavioralBoost = this.calculatePersonalizationBoost(vendor);
    
    // IMPORTANT: behavioral boost is ADDED to backend score, not multiplied
    // This preserves the backend's 5-factor weight distribution
    return vendor.baseRankingScore + behavioralBoost;
  }
  
  // Record user interaction for learning
  recordInteraction(vendorId: string, interactionType: string, feedback?: 'positive' | 'negative') {
    const interaction: UserInteraction = {
      vendorId,
      type: interactionType,
      timestamp: Date.now(),
      feedback
    };
    
    this.userInteractions.push(interaction);
    this.updateBehavioralBoost(vendorId, interaction);
    
    // Persist to localStorage for guest users
    this.saveToStorage();
  }
  
  private updateBehavioralBoost(vendorId: string, interaction: UserInteraction) {
    const existing = this.boosts.get(vendorId) || { 
      vendorId, 
      boost: 0, 
      confidence: 0, 
      lastUpdated: Date.now() 
    };
    
    // Update boost based on interaction type and feedback
    const boostChange = this.getBoostChange(interaction);
    existing.boost = Math.max(-0.1, Math.min(0.2, existing.boost + boostChange));
    
    // Increase confidence with more interactions
    existing.confidence = Math.min(1.0, existing.confidence + 0.05);
    existing.lastUpdated = Date.now();
    
    this.boosts.set(vendorId, existing);
  }
  
  private getBoostChange(interaction: UserInteraction): number {
    const { type, feedback } = interaction;
    
    // Positive feedback increases boost, negative decreases
    const feedbackMultiplier = feedback === 'positive' ? 1 : feedback === 'negative' ? -1 : 0;
    
    // Different interaction types have different weights
    const interactionWeights = {
      'VIEW': 0.01,
      'AR_TAP': 0.03,
      'NAVIGATION': 0.05,
      'PROMOTION_TAP': 0.04,
      'VOICE_SEARCH': 0.02,
      'FAVORITE': 0.06,
      'SHARE': 0.04
    };
    
    return (interactionWeights[type] || 0.01) * feedbackMultiplier;
  }
  
  // Apply behavioral sorting to vendor list
  applyBehavioralSorting(vendors: VendorWithRanking[]): VendorWithRanking[] {
    return vendors
      .map(vendor => ({
        ...vendor,
        finalRankingScore: this.getFinalRankingScore(vendor)
      }))
      .sort((a, b) => b.finalRankingScore - a.finalRankingScore);
  }
}

// Global instance
export const behavioralRanking = new BehavioralRankingService();
```

### Usage in Discovery Components

```typescript
// In src/components/VendorCard.tsx
import { behavioralRanking } from '../services/behavioralRanking';

const VendorCard: React.FC<{ vendor: VendorWithRanking }> = ({ vendor }) => {
  const handleUserFeedback = (vendorId: string, feedback: 'positive' | 'negative') => {
    behavioralRanking.recordInteraction(vendorId, 'VIEW', feedback);
    
    // Show subtle feedback confirmation
    uiStore.getState().addToast({
      type: 'success',
      message: feedback === 'positive' ? 'Thanks for your feedback!' : 'We\'ll show you better results',
      duration: 2000
    });
  };
  
  // Get final ranking score for display (debug mode only)
  const finalScore = behavioralRanking.getFinalRankingScore(vendor);
  const behavioralBoost = behavioralRanking.calculatePersonalizationBoost(vendor);
  
  return (
    <div className="vendor-card">
      {/* Vendor content */}
      
      {/* Debug info - only in development */}
      {process.env.NODE_ENV === 'development' && (
        <div className="debug-ranking">
          <span>Base: {vendor.baseRankingScore.toFixed(3)}</span>
          <span>Boost: {behavioralBoost > 0 ? '+' : ''}{behavioralBoost.toFixed(3)}</span>
          <span>Final: {finalScore.toFixed(3)}</span>
        </div>
      )}
      
      {/* Feedback buttons */}
      <div className="feedback-buttons">
        <button onClick={() => handleUserFeedback(vendor.id, 'positive')}>
          👍 Helpful
        </button>
        <button onClick={() => handleUserFeedback(vendor.id, 'negative')}>
          👎 Not helpful
        </button>
      </div>
    </div>
  );
};
```

### Integration with TanStack Query

```typescript
// In src/hooks/useDiscoveryVendors.ts
import { behavioralRanking } from '../services/behavioralRanking';

export const useDiscoveryVendors = (params: DiscoveryParams) => {
  return useQuery({
    queryKey: ['discovery-vendors', params],
    queryFn: async () => {
      const response = await api.get('/api/v1/user-portal/discovery/nearby/', { params });
      const vendors: VendorWithRanking[] = response.data;
      
      // Apply behavioral ranking to backend results
      return behavioralRanking.applyBehavioralSorting(vendors);
    },
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // Refresh every minute
  });
};
```

### Migration to Logged-in Users

```typescript
// In src/services/behavioralRanking.ts
class BehavioralRankingService {
  // ... existing methods
  
  // Export guest behavioral data for migration
  exportGuestData(): BehavioralDataExport {
    return {
      boosts: Array.from(this.boosts.values()),
      interactions: this.userInteractions,
      exportDate: Date.now()
    };
  }
  
  // Import behavioral data for logged-in users
  importUserData(data: BehavioralDataExport) {
    // Merge with existing data, preferring server data
    data.boosts.forEach(boost => {
      const existing = this.boosts.get(boost.vendorId);
      if (!existing || boost.lastUpdated > existing.lastUpdated) {
        this.boosts.set(boost.vendorId, boost);
      }
    });
    
    // Merge interactions
    this.userInteractions = [...this.userInteractions, ...data.interactions];
  }
  
  // Sync with server for logged-in users
  async syncWithServer() {
    if (!authStore.getState().isAuthenticated) return;
    
    try {
      // Export local data
      const localData = this.exportGuestData();
      
      // Send to server
      await api.post('/api/v1/user-portal/preferences/behavioral-data', localData);
      
      // Get server data and merge
      const serverData = await api.get('/api/v1/user-portal/preferences/behavioral-data');
      this.importUserData(serverData.data);
      
    } catch (error) {
      console.error('Failed to sync behavioral data:', error);
    }
  }
}

interface BehavioralDataExport {
  boosts: BehavioralBoost[];
  interactions: UserInteraction[];
  exportDate: number;
}
```

### Backend API Support

```python
# In user_portal/views/preferences.py
class BehavioralDataView(APIView):
    """Handle behavioral data synchronization for logged-in users"""
    
    def get(self, request):
        """Export user's behavioral data"""
        user = request.user
        data = {
            'boosts': BehavioralBoost.objects.filter(user=user).values(),
            'interactions': UserInteraction.objects.filter(user=user).values(),
        }
        return Response(data)
    
    def post(self, request):
        """Import and merge behavioral data"""
        user = request.user
        data = request.data
        
        # Merge boosts
        for boost_data in data.get('boosts', []):
            boost, created = BehavioralBoost.objects.get_or_create(
                user=user,
                vendor_id=boost_data['vendorId'],
                defaults={
                    'boost': boost_data['boost'],
                    'confidence': boost_data['confidence'],
                    'last_updated': boost_data['lastUpdated']
                }
            )
            if not created and boost_data['lastUpdated'] > boost.last_updated:
                boost.boost = boost_data['boost']
                boost.confidence = boost_data['confidence']
                boost.last_updated = boost_data['lastUpdated']
                boost.save()
        
        return Response({'status': 'merged'})
```

### Key Implementation Notes

1. **Preserves Backend Ranking:** Behavioral boost is additive, not multiplicative
2. **Bounded Impact:** Boost limited to ±20% to prevent overriding backend logic
3. **Confidence Weighting:** New users have minimal impact until data accumulates
4. **Guest Migration:** Seamless transition from guest to logged-in mode
5. **Server Sync:** Persistent storage for logged-in users across devices
6. **Debug Visibility:** Development mode shows ranking breakdown for testing

```typescript
// In hooks/useNearbyVendors.ts
export const useNearbyVendors = (lat: number, lng: number, radius: number, tags: string[]) => {
  const userProfile = discoveryStore(state => state.userBehaviorProfile);

  return useQuery({
    queryKey: QUERY_KEYS.nearby(lat, lng, radius, tags),
    queryFn: () => api.getNearbyVendors(lat, lng, radius, tags),
    select: (data) => {
      // Apply behavioral ranking to backend results
      return behavioralRanking.applyBehavioralRanking(data.vendors, userProfile);
    },
    refetchInterval: 30000,
  });
};
```

**User Feedback Collection:**

```typescript
// In components/VendorCard.tsx
const handleUserFeedback = (vendorId: string, feedback: 'positive' | 'negative') => {
  behavioralRanking.recordInteraction(vendorId, 'VIEW', feedback);
  
  // Show subtle feedback confirmation
  uiStore.getState().addToast({
    type: 'success',
    message: feedback === 'positive' ? 'Thanks for your feedback!' : 'We\'ll show you better results',
    duration: 2000
  });
};
```

### 5.4 Axios Interceptors (`api/client.ts`)

- **Request:** attach `Authorization: Bearer <accessToken>` OR `X-Guest-Token: <guestToken>`
- **Response 401:** proactive token refresh with shared promise deduplication (no double-refresh):
  ```typescript
  // In client.ts — deduplicated refresh:
  let refreshPromise: Promise<void> | null = null;
  // On 401: if (!refreshPromise) { refreshPromise = doRefresh().finally(() => refreshPromise = null); }
  // All concurrent 401s await the same promise, then retry with new token
  ```
- **Response 429:** parse `Retry-After` header → `uiStore.addToast({type:'warning', message:'Try again in Xs'})` → reject with `RateLimitError` (never retry automatically)
- **After refresh failure:** `authStore.logout()` → redirect `/user/login` with `?returnTo=` param

---

## 6. ROUTING ARCHITECTURE

### Route Guards

**`GuestOrAuthRoute`:** All discovery/vendor pages AND `/preferences` — passes through for both guest and logged-in. Injects location context. Ensures guest token exists (creates one if not).

> **[AUDIT FIX — CRITICAL]** `/preferences` must use `GuestOrAuthRoute`, NOT `AuthOnlyRoute`. Guests can access theme, default view, and search radius settings. Only the notification preferences section and GDPR sections (account deletion, data export) render inline sign-in prompts — they do NOT redirect the guest to login. This is mandated by UP-12 which explicitly states guests can access limited preferences.

**`AuthOnlyRoute`:** Reserved for any future auth-only routes that have no guest-accessible equivalent. Currently only wraps account deletion confirmation flow if accessed directly. Redirects to `/user/login?returnTo=<path>`.

**`PublicOnlyRoute`:** Login, Register — redirects to `/discover` if already authenticated.

### Lazy Loading Strategy

All page components: `React.lazy()` with `<Suspense>` fallback (skeleton matching page shape — never a generic spinner).

Code split boundaries:
- Landing page: separate chunk (heaviest — Framer Motion animations)
- AR view: separate chunk (AR logic, device API wrappers)
- Mapbox GL JS: separate chunk (loaded only when Map view activated, ~600KB gzipped)
- All other pages: grouped into discovery bundle

---

## 7. LANDING PAGE — WOW FACTOR

### 7.1 Design Mandate

Every design decision answers: "Does this create a WOW within 3 seconds of loading?"
Aesthetic: Claude.ai / Vercel style — powerful, centered, minimal. Zero clutter.

### 7.2 Sticky Navbar

```
Background: #000000 (pure black)
Left: AirAds logo (sm) + "AirAds" wordmark in brand orange
Center: "How It Works" | "For Vendors" | "Sign In" links
Right: "Start Exploring →" — gradient pill button (orange → crimson), 40px height

Scroll behavior:
  Top: transparent, no border
  Scrolled > 50px: black bg + 1px rgba(255,255,255,0.10) bottom border + backdrop-filter: blur(8px)

Mobile (< 768px):
  Center links hidden → hamburger icon (right)
  Hamburger: full-screen slide-in dark menu, all items 48px touch targets
```

### 7.3 Hero Section (100vh)

```
Container: 100vh, #0A0A0A background, flexbox column center

Background ambient glows (CSS only — no image files):
  Left: radial-gradient(ellipse 600px 400px at 20% 50%, rgba(255,140,0,0.08), transparent)
  Right: radial-gradient(ellipse 600px 400px at 80% 50%, rgba(0,188,212,0.08), transparent)

AirAds Logo:
  Size: 80px, margin-bottom: 32px
  CSS float animation: translateY 0 → -8px → 0, 3s ease-in-out infinite

H1: "Discover What's Near You, Right Now."
  Font: DM Sans Bold, 56px desktop / 36px mobile, line-height: 1.15
  "Right Now." text: background: var(--brand-gradient); -webkit-background-clip: text; color: transparent

Subheadline: "Point your camera. Speak your craving. Walk to the deal."
  Font: 18px desktop / 15px mobile, color: var(--color-text-secondary)

HERO SEARCH BAR:
  Width: min(680px, 90vw), Height: 64px
  Background: var(--color-bg-elevated)
  Border: 1px solid var(--color-border)
  Border-radius: var(--radius-full) — pill shape
  margin-top: 40px

  Left: MapPin icon (Lucide, 20px, brand orange)
  Center: placeholder "Search for food, shops, deals nearby..."
         Font: DM Sans Medium, 16px
  Right: mic button — 40×40px circle, var(--brand-gradient) bg, white Mic icon, 18px
         On hover: scale(1.05); On listening: pulsing ring CSS animation

  Hover state: box-shadow: 0 0 0 2px rgba(255,140,0,0.3), 0 8px 32px rgba(255,140,0,0.15)
  Focus state: box-shadow: 0 0 0 3px rgba(255,140,0,0.4); transform: scale(1.01)

Quick Tags Row (margin-top: 16px, centered):
  "🍕 Food" "☕ Coffee" "✂️ Salon" "🛍️ Shopping" "🔥 Deals"
  Each: TagChip sm, outlined, orange on hover
  On tap: navigate to /discover with tag pre-selected in discoveryStore

Trust line (margin-top: 12px):
  "No signup needed · Works in your browser · Finds what's open now"
  Font: 13px, var(--color-text-tertiary)
```

### 7.4 How It Works Slider (Phone Mockup with 4 Auto-Playing Slides)

```
Section title: "Three Ways to Discover" (2xl bold centered) + subtitle
Phone mockup: 280×560px, border-radius: 40px, black bg, CSS notch + home bar

4 slides inside mockup (Framer Motion AnimatePresence, 4000ms each, crossfade):

SLIDE 1 — AR Discovery:
  Background: dark blue gradient (camera simulation)
  Framer Motion: 3 ARMarker components floating in stagger, slow bob animation
  "🍔 Raja Burgers — 120m" | "☕ Coffee Lab — 80m" | "✂️ Style Studio — 200m"
  Caption: "Point your camera. See what's around you."

SLIDE 2 — Voice Search:
  Background: #0A0A0A
  Center: large mic icon (crimson) + VoiceWave bars animated
  Text: "cheap biryani near me" appearing word by word (stagger reveal)
  After 1.5s: 3 vendor cards slide up (stagger)
  Caption: "Just say what you're craving."

SLIDE 3 — Map + Deals:
  Background: dark map grid (CSS pattern — no external image)
  Orange/teal pin dots (5-6, some pulsing)
  One pin expands into: "🔥 30% OFF · Al Baik · 150m · Ends in 2h"
  CountdownTimer ticking
  Caption: "Real-time deals from nearby shops."

SLIDE 4 — Navigate:
  Route line: SVG path, brand gradient stroke, animated dasharray draw
  Destination pin: pulsing teal dot
  "Walk 2 minutes north ↑" instruction + "~ 2 min" teal chip
  Caption: "One tap to get there."

Auto-play: 4000ms, pause on hover/touch
Swipe: Framer Motion drag gesture to change slides
Dots: 4 circles, active = brand orange, inactive = rgba(255,255,255,0.3)
```

### 7.5 Three Modes Explained (Cards)

```
3 cards horizontal (desktop) / stacked (mobile)
Scroll-in animation: whileInView {y: 20→0, opacity: 0→1}, once: true

Card 1 — AR Camera Discovery (accent: brand orange, border-left: 3px solid)
  Icon: animated camera SVG (dots float out on scroll-in)
  "Open your camera and see nearby businesses floating in your real world view."

Card 2 — Just Speak (accent: brand crimson)
  Icon: microphone + 3 sound arcs (animate on scroll)
  "Say what you want in plain language. We understand Urdu, English, and Roman."

Card 3 — See The Map (accent: brand teal)
  Icon: map + pins dropping animation on scroll
  "Classic map view with all nearby vendors. Filter by category, distance, or deals."
```

### 7.6 Social Proof (Animated Count-Up on Scroll)

```
3 stats (count-up via Framer Motion animate or intersection observer trigger):
  "500+" Vendors | "3" Cities | "Live" Real-time deals

Stat values: 56px bold, brand gradient text, -webkit-background-clip: text
Labels: 16px secondary
Separator: 1px vertical border (desktop only)
Below: "No account needed to start exploring." (15px secondary, centered)
```

### 7.7 Final CTA Section

```
Background: var(--color-bg-surface)
Radial glow: rgba(255,140,0,0.05) + rgba(0,188,212,0.05)

H2: "What's Near You Right Now?" — 40px bold, centered
"Right Now?" in gradient text

Hero search bar (exact same component reused)
"Or just open the live map →" — text link to /discover, 14px secondary
```

### 7.8 Footer

```
Background: #000000
Top border: 2px linear-gradient(90deg, #FF8C00, #C41E3A, #00BCD4) — brand gradient divider

Left: AirAds logo (sm) + "Nearby + Now" tagline
Right: "For Vendors →" (vendor portal link) | "Privacy Policy" | "Terms"
Bottom: "© 2026 AirAds. All rights reserved." (12px tertiary, centered)
```

### 7.9 Landing Page Performance Rules

- `prefers-reduced-motion`: all animations wrapped — disable keyframes, show static state
- All scroll animations: `whileInView` with `once: true` — trigger only once, never repeat
- Zero external images on landing — all CSS/SVG or the single `airad_icon.png` from public/
- Framer Motion: import only specific motion exports (tree-shaking)
- Above-fold content target: interactive in < 1.5s on 4G

---

## 8. AUTHENTICATION PAGES

### 8.1 Login Page (`/user/login`)

```
Layout: Two-panel (desktop) / Full-screen (mobile)

LEFT PANEL (desktop, ~40% width, black bg):
  AirAds logo (lg, float animation) + "AirAds" gradient heading
  Tagline: "Discover what's near you, right now."
  3 trust points with teal checkmarks:
    "✓ Free to explore, always"
    "✓ No credit card, ever"
    "✓ Your location stays private"

RIGHT PANEL (100% on mobile):
  Background: var(--color-bg-surface)
  Padding: 48px (desktop) / 32px 24px (mobile)

  H1: "Welcome back, Explorer." (bold 28px)
  Subtitle: "Sign in to your account." (secondary 15px)

  Form:
    Email input (label + type=email + autocomplete=email)
    Password input (label + obscure toggle with Eye icon)
    "Forgot password?" link (right-aligned)
    "Sign In" button (primary gradient, fullWidth, lg, loading state)
    Divider: "or"
    "Continue as Guest →" (ghost, fullWidth, lg)
      → issues guest token → navigates to /discover
    "New to AirAds? It's free →" (text link, bottom)

  On success:
    If ?returnTo= → navigate to returnTo
    Else → navigate to /discover
```

### 8.2 Register Page (`/user/register`)

```
Same two-panel layout.

Form fields (minimal — lowest friction):
  First name only (not "full name")
  Email
  Password + strength indicator (4-segment bar: red/orange/amber/green)
  "I agree to Terms and Privacy Policy" checkbox (required)

Submit: "Create Account — It's Free" (primary gradient, fullWidth)

Success state (replaces form — no page redirect):
  Animated checkmark (Framer Motion SVG path draw, 400ms, brand teal)
  "Check Your Email!" heading
  "We sent a verification link to [email]."
  Resend link with 60s countdown (disabled until countdown ends)
  "Back to Sign In" link
```

---

## 9. DISCOVERY HOME SHELL

### 9.1 Shell Architecture

`DiscoveryPage.tsx` is the outer shell that:
1. Requests GPS permission on mount via `useLocation` hook
2. Shows location-resolving state while GPS fixes
3. Renders sticky header (search bar + view switcher + promotions strip)
4. Renders active view (AR / Map / List) via `IndexedStack` pattern (all three mounted, only active visible)
5. Renders bottom navigation bar (mobile only, `position: fixed bottom`)

Using `IndexedStack` pattern (all three views rendered, CSS `display: none` on inactive) ensures AR camera session is not destroyed when switching views.

### 9.2 Sticky Header

```
Position: sticky top: 0, z-index: 100
Background: var(--color-bg-nav) + backdrop-filter: blur(8px)

Row 1 (44px): Discovery context + view switcher
  Left: LocationContext ("📍 Gulberg III") — tappable
  Right: ViewSwitcher pill — "📷 AR | 🗺️ Map | 📋 List"
    Active: brand orange bg, white text
    Inactive: transparent, secondary text
    Switching: AnimatePresence crossfade (150ms)

Row 2 (44px): DiscoverySearchBar (compact variant, full width)

Row 3 (conditional, ~36px): PromotionsStrip
  Only visible when active promotions exist nearby (API flash-alert data)
  Horizontal scroll, hidden scrollbar
  Chip: "🔥 20% OFF · Raja Burgers · 2 min walk" — brand orange, tappable → /vendor/:id
  Auto-hides with Framer Motion when no promotions (height animation)
```

### 9.3 Location Permission Handling

```
States:
  'unknown':  Requesting — "Finding your location..." subtle text, skeleton cards below
  'granted':  Normal — LocationContext shows area name
  'denied':   Map view fallback + "Enable location for better results" info chip
              NO crash, NO blocking modal
              Guest city picker available as alternative

First load loading (GPS fix):
  SkeletonLoader cards (shimmer, same dimensions as VendorCard)
  Never shows blank — always skeleton
  If > 3 seconds: AirAds logo watermark (low opacity) in center
```

### 9.4 Bottom Navigation Bar (Mobile Only, < 768px)

```
Position: fixed bottom: 0, z-index: 100, full width
Background: var(--color-bg-surface) + top border
Height: 60px

5 tabs:
  🏠 Discover  →  /discover
  🔥 Deals     →  /deals
  🏷️ Browse   →  /browse
  🎬 Reels     →  /reels
  👤 Me        →  /preferences

Active: brand orange icon + label
Inactive: var(--color-text-tertiary)
Minimum touch target per tab: 44×44px (ensured by flex layout)
```

### 9.5 Empty & Offline States

```
Empty state:
  AirAds logo (60px, opacity 0.12) + "No vendors found nearby."
  Context message + 2 CTAs: "Expand Radius" | "Browse Categories"

Offline state:
  OfflineBanner slides in from top
  Cached TanStack Query data still visible (stale — explicitly labeled)
  "Last updated [X] min ago" text in secondary color
  Retry button → triggers refetch when online
```

---

## 10. AR DISCOVERY VIEW

### 10.1 AR Detection Strategy (on `ARView.tsx` mount)

```typescript
const detectARMode = async (): Promise<'REAL' | 'SIMULATED'> => {
  // Check 1: Camera permission via navigator.permissions API
  const cameraStatus = await navigator.permissions.query({name: 'camera'});
  if (cameraStatus.state === 'denied') return 'SIMULATED';

  // Check 2: DeviceOrientationEvent support
  if (!('DeviceOrientationEvent' in window)) return 'SIMULATED';

  // Check 3: iOS 13+ requires explicit permission request
  if (typeof (DeviceOrientationEvent as any).requestPermission === 'function') {
    const permission = await (DeviceOrientationEvent as any).requestPermission();
    if (permission !== 'granted') return 'SIMULATED';
  }

  return 'REAL';
};
```

Transition between modes: seamless — user never sees "detection in progress".

### 10.2 Mode A — Real AR (Mobile browser, camera granted)

```
<video> element: position: fixed, width: 100vw, height: 100vh
  autoPlay, playsInline, muted — camera feed as background

Overlay (absolute positioned div on top):
  AR markers positioned using bearing + device heading:
    bearing_to_vendor = Haversine bearing from user GPS to vendor GPS
    relative_bearing = (bearing_to_vendor - device_heading + 360) % 360
    visible_range = relative_bearing <= 60 || relative_bearing >= 300
    screen_x = screenWidth * 0.5 + (normalizedRelativeBearing * screenWidth * 0.6)
    scale = 1.0 - (distance_m / max_radius_m) * 0.5 — clamped 0.5-1.0

  DeviceOrientationEvent.alpha → device_heading (smooth via requestAnimationFrame)

Compass rose: SVG, top-right, rotates with device_heading (CSS transform, 100ms linear)
```

### 10.3 Mode B — Simulated AR (Desktop or permission denied)

```
Background: linear-gradient(180deg, #0a0a1a 0%, #0a1628 50%, #0a2818 100%)
Not a blank screen. Not an error. Premium simulated AR experience.

Markers positioned mathematically as if user faces north (no compass rotation).

Desktop: Parallax on mousemove
  document.addEventListener('mousemove', (e)) → offset markers by max ±20px
  Creates depth illusion

Mobile (camera denied but gyroscope available):
  DeviceOrientationEvent for tilt → markers shift ±15px max (prevents dizziness)

Floating animation:
  Framer Motion animate y: [0, -6, 0], duration randomized 2-4s per marker
  Staggered start times — no synchronized bobbing effect
```

### 10.4 AR Marker — Expanded Behavior

```
Collapsed (default):
  Width: 160-240px (distance-proportional), Height: 56px
  Glass: var(--glass-bg), border: 1px var(--glass-border), backdrop-filter: var(--glass-blur)
  Border-radius: var(--radius-2xl) — pill
  Content: [emoji][name][distance][promotion badge][tier dot]

On tap (Framer Motion layoutId spring):
  Expanded: 280px wide, ~140px tall
  Added content: category, hours, active promotion detail
  3 action buttons:
    "🧭 Directions" → starts navigation (fires NAVIGATION interaction)
    "📞 Call" → tel: link (fires CALL interaction)
    "View Profile →" → navigate to /vendor/:id

On backdrop tap: AnimatePresence exit → collapse back to pill
```

### 10.5 AR Clustering

```
Client-side grouping (after API response, before render):
  Group markers where angular separation < 8 degrees (bearing difference)
  If group.length >= 3 → show ARCluster instead of individual markers

ARCluster:
  Orange border (2px), count badge, top 2 category emojis
  "5 vendors" center text

On cluster tap:
  Spring expand → individual markers appear in arc (stagger 50ms each)
  Background tap → re-group (AnimatePresence + spring)
```

### 10.6 Walking Safety Overlay

```
Trigger: DeviceMotionEvent accelerometer magnitude > 0.5 m/s² sustained 2s

Overlay:
  Position: fixed top, full width, height: 44px
  Background: rgba(196,30,58,0.85) — brand crimson
  Content: "👀 Watch where you're walking!" (14px white bold)
  NOT full-screen — unobtrusive top strip

Auto-dismiss: 3 seconds
Re-trigger: minimum 30 seconds after last dismiss
prefers-reduced-motion: no slide animation, appears instantly

```

### 10.7 AR Radius Slider

```
Position: fixed bottom, above bottom navigation
Width: 80% screen width, centered

5 values: 100m | 500m | 1km | 2km
Default: 500m (matches backend default)

On change:
  Debounce: 300ms before updating discoveryStore.searchRadius
  TanStack Query refetch triggered (radius param changes)
  Markers fade in/out (Framer Motion opacity 0→1, 300ms) as results update

Label: "Showing vendors within: [radius]" (13px secondary, centered above slider)
```

---

*Continues in USER_PORTAL_FRONTEND_PLAN_PART2.md*
