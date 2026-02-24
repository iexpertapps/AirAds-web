# ╔══════════════════════════════════════════════════════════════════╗
# ║         AirAd — WOW DESIGN SYSTEM UPGRADE                       ║
# ║         Logo Integration · Dual Theme · Brand Elevation         ║
# ║         Windsurf Prompt — Copy & Paste as ONE block             ║
# ╚══════════════════════════════════════════════════════════════════╝

> **PASTE THIS ENTIRE BLOCK into Windsurf in one shot.**
> This is a DESIGN-ONLY pass. No backend logic, no API changes, no model changes.
> Scope: Every visual surface — React Admin Portal + Flutter App (if exists).

---

## 🎯 OBJECTIVE

Perform a complete visual design elevation across the entire AirAd codebase.
The logo file `airad_icon3x.png` exists at the **project root**.
Use it as the single source of truth for the entire brand color system.
The result must make anyone who sees it immediately say **"WOW — this is a premium product."**
Reference quality bar: **Linear.app, Vercel Dashboard, Stripe, Raycast**.

---

## 📌 STEP 0 — READ THE LOGO FIRST

Before writing a single line of code, look at `airad_icon3x.png` in the project root.

The logo is 3 overlapping organic teardrop/petal shapes on a **pure black (#000000)** background:
- **Top petal**: Warm Orange → `#FF8C00` (energy, primary actions, discovery)
- **Left petal**: Deep Crimson → `#C41E3A` (passion, alerts, brand identity)
- **Right petal**: Vibrant Teal → `#00BCD4` (trust, success, innovation)
- **Overlap zones**: Rich purple-maroon blends where petals intersect

These 3 colors + black ARE the AirAd brand. Everything flows from them.

---

## 📁 STEP 1 — LOGO ASSET DISTRIBUTION

```
TASK: Distribute and resize airad_icon3x.png to all required locations.

SOURCE FILE: ./airad_icon3x.png (project root)

FOR REACT PORTAL:
  Copy to: frontend/src/assets/logo/airad_icon.png
  Also create a favicon: frontend/public/favicon.png
  Use the sharp npm package or a canvas script to generate:
    - 16x16  → frontend/public/favicon-16.png
    - 32x32  → frontend/public/favicon-32.png
    - 64x64  → frontend/public/favicon-64.png
    - 180x180 → frontend/public/apple-touch-icon.png
  Update frontend/index.html to reference these favicons.

FOR FLUTTER APP (if present):
  Copy to: mobile/assets/images/airad_icon.png
  Also create:
    - mobile/assets/images/airad_icon_64.png  (64x64)
    - mobile/assets/images/airad_icon_128.png (128x128)
    - mobile/assets/images/airad_splash.png   (512x512, centered on brand-dark bg)
  Register ALL in pubspec.yaml under flutter > assets.

LOGO USAGE RULES (enforce everywhere):
  - The logo icon ALWAYS keeps its black background — it is part of the brand identity
  - On dark surfaces: logo renders naturally
  - On light surfaces: wrap in a container with border-radius: 12px, background: #000, padding: 6px
  - NEVER stretch, recolor, or apply opacity to the logo icon
  - Minimum display size: 24px (icon-only), 28px with wordmark
```

---

## 🏗️ STEP 2 — CREATE SHARED LOGO COMPONENT

```
TASK: Build a reusable Logo component for React.

FILE: frontend/src/components/shared/Logo.tsx

Props interface:
  size: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  variant: 'icon-only' | 'icon-text' | 'full-lockup'
  theme: 'auto' | 'light' | 'dark'  (auto = reads from ThemeContext)

Size map:
  xs  → icon: 24px  | text: 16px weight-700
  sm  → icon: 32px  | text: 20px weight-700
  md  → icon: 40px  | text: 24px weight-700  (default — use in navbar)
  lg  → icon: 56px  | text: 32px weight-700  (use in auth pages)
  xl  → icon: 80px  | text: 44px weight-800  (use in splash/onboarding)

Wordmark "AirAd":
  Apply CSS gradient text:
    background: linear-gradient(135deg, #FF8C00 0%, #C41E3A 50%, #00BCD4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  Font: var(--font-display) — weight 700 or 800
  Letter-spacing: -0.02em

Full lockup variant:
  Icon + "AirAd" wordmark + tagline "Discover What's Near"
  Tagline: 13px, var(--text-secondary), weight 400, letter-spacing 0.04em UPPERCASE

The icon container:
  background: #000000
  border-radius: 10px (sm/md), 14px (lg/xl)
  padding: 4px (sm/md), 6px (lg/xl)
  box-shadow in light theme: 0 2px 8px rgba(0,0,0,0.15)
  box-shadow in dark theme: 0 2px 12px rgba(255,140,0,0.20)
```

---

## 🎨 STEP 3 — COMPLETE DUAL THEME COLOR SYSTEM

```
TASK: Replace ALL color tokens in the project with this complete dual-theme system.
File: frontend/src/styles/tokens.css (create or overwrite entirely)

/* ================================================================
   AIRAAD DESIGN SYSTEM — DUAL THEME TOKENS
   Derived from airad_icon3x.png brand colors
   ================================================================ */

/* ── BRAND PRIMITIVES (theme-independent) ── */
:root {
  --brand-orange:          #FF8C00;
  --brand-orange-light:    #FFB347;
  --brand-orange-dark:     #E67E00;
  --brand-orange-glow:     rgba(255, 140, 0, 0.25);

  --brand-crimson:         #C41E3A;
  --brand-crimson-light:   #E8405A;
  --brand-crimson-dark:    #9E1830;
  --brand-crimson-glow:    rgba(196, 30, 58, 0.25);

  --brand-teal:            #00BCD4;
  --brand-teal-light:      #4DD0E1;
  --brand-teal-dark:       #0097A7;
  --brand-teal-glow:       rgba(0, 188, 212, 0.25);

  --brand-black:           #000000;
  --brand-dark:            #0D0D0D;

  /* Gradient shorthands */
  --gradient-brand:        linear-gradient(135deg, #FF8C00 0%, #C41E3A 50%, #00BCD4 100%);
  --gradient-brand-soft:   linear-gradient(135deg, rgba(255,140,0,0.15) 0%, rgba(196,30,58,0.10) 50%, rgba(0,188,212,0.15) 100%);
  --gradient-orange-crimson: linear-gradient(135deg, #FF8C00 0%, #C41E3A 100%);
  --gradient-crimson-teal: linear-gradient(135deg, #C41E3A 0%, #00BCD4 100%);
  --gradient-teal-orange:  linear-gradient(135deg, #00BCD4 0%, #FF8C00 100%);
}

/* ================================================================
   LIGHT THEME
   ================================================================ */
[data-theme="light"], .theme-light {

  /* Backgrounds */
  --bg-base:               #F5F5F5;   /* page canvas */
  --bg-surface:            #FFFFFF;   /* cards, modals */
  --bg-surface-raised:     #FFFFFF;   /* dropdowns, popovers */
  --bg-surface-sunken:     #EFEFEF;   /* input fields, table rows alt */
  --bg-sidebar:            #FFFFFF;   /* sidebar background */
  --bg-sidebar-active:     rgba(255, 140, 0, 0.08);  /* active nav item */
  --bg-hover:              rgba(0, 0, 0, 0.04);
  --bg-overlay:            rgba(0, 0, 0, 0.45);

  /* Text */
  --text-primary:          #111111;
  --text-secondary:        #555555;
  --text-tertiary:         #888888;
  --text-disabled:         #BBBBBB;
  --text-inverse:          #FFFFFF;
  --text-on-brand:         #FFFFFF;

  /* Borders */
  --border-default:        #E0E0E0;
  --border-strong:         #BDBDBD;
  --border-focus:          #FF8C00;
  --border-error:          #C41E3A;
  --border-success:        #00897B;

  /* Brand semantic on light */
  --color-primary:         #FF8C00;
  --color-primary-hover:   #E67E00;
  --color-primary-active:  #CC7000;
  --color-primary-subtle:  rgba(255, 140, 0, 0.10);
  --color-primary-text:    #CC6600;

  --color-accent:          #C41E3A;
  --color-accent-hover:    #9E1830;
  --color-accent-subtle:   rgba(196, 30, 58, 0.08);

  --color-info:            #0097A7;
  --color-info-hover:      #00838F;
  --color-info-subtle:     rgba(0, 188, 212, 0.10);
  --color-info-text:       #006978;

  /* Status colors */
  --color-success:         #00897B;
  --color-success-bg:      #E0F2F1;
  --color-success-text:    #004D40;
  --color-success-border:  #80CBC4;

  --color-warning:         #FF8C00;
  --color-warning-bg:      #FFF3E0;
  --color-warning-text:    #E65100;
  --color-warning-border:  #FFCC02;

  --color-error:           #C41E3A;
  --color-error-bg:        #FFEBEE;
  --color-error-text:      #B71C1C;
  --color-error-border:    #EF9A9A;

  --color-neutral:         #757575;
  --color-neutral-bg:      #F5F5F5;
  --color-neutral-text:    #424242;

  /* Sidebar specific (light) */
  --sidebar-bg:            #FFFFFF;
  --sidebar-border:        #EEEEEE;
  --sidebar-text:          #444444;
  --sidebar-text-active:   #FF8C00;
  --sidebar-icon:          #777777;
  --sidebar-icon-active:   #FF8C00;
  --sidebar-item-active-bg: rgba(255, 140, 0, 0.08);
  --sidebar-item-active-border: #FF8C00;

  /* Shadows (light theme — crisp, premium) */
  --shadow-xs:  0 1px 2px rgba(0,0,0,0.06);
  --shadow-sm:  0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
  --shadow-md:  0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06);
  --shadow-lg:  0 10px 15px rgba(0,0,0,0.08), 0 4px 6px rgba(0,0,0,0.05);
  --shadow-xl:  0 20px 25px rgba(0,0,0,0.09), 0 10px 10px rgba(0,0,0,0.04);
  --shadow-brand: 0 4px 14px rgba(255, 140, 0, 0.30);
  --shadow-brand-crimson: 0 4px 14px rgba(196, 30, 58, 0.30);
  --shadow-brand-teal: 0 4px 14px rgba(0, 188, 212, 0.30);
}

/* ================================================================
   DARK THEME
   ================================================================ */
[data-theme="dark"], .theme-dark {

  /* Backgrounds */
  --bg-base:               #0A0A0A;   /* deepest — page canvas */
  --bg-surface:            #141414;   /* cards */
  --bg-surface-raised:     #1C1C1C;   /* dropdowns, modals */
  --bg-surface-sunken:     #0D0D0D;   /* input backgrounds */
  --bg-sidebar:            #000000;   /* pure black like the logo bg */
  --bg-sidebar-active:     rgba(255, 140, 0, 0.12);
  --bg-hover:              rgba(255, 255, 255, 0.05);
  --bg-overlay:            rgba(0, 0, 0, 0.75);

  /* Text */
  --text-primary:          #F0F0F0;
  --text-secondary:        #A0A0A0;
  --text-tertiary:         #606060;
  --text-disabled:         #404040;
  --text-inverse:          #111111;
  --text-on-brand:         #FFFFFF;

  /* Borders */
  --border-default:        rgba(255,255,255,0.08);
  --border-strong:         rgba(255,255,255,0.15);
  --border-focus:          #FF8C00;
  --border-error:          #E8405A;
  --border-success:        #4DD0E1;

  /* Brand semantic on dark */
  --color-primary:         #FF8C00;
  --color-primary-hover:   #FFB347;
  --color-primary-active:  #FF9E26;
  --color-primary-subtle:  rgba(255, 140, 0, 0.15);
  --color-primary-text:    #FFB347;

  --color-accent:          #E8405A;
  --color-accent-hover:    #FF6B85;
  --color-accent-subtle:   rgba(232, 64, 90, 0.12);

  --color-info:            #4DD0E1;
  --color-info-hover:      #80DEEA;
  --color-info-subtle:     rgba(77, 208, 225, 0.12);
  --color-info-text:       #80DEEA;

  /* Status colors */
  --color-success:         #4DD0E1;
  --color-success-bg:      rgba(0, 188, 212, 0.12);
  --color-success-text:    #80DEEA;
  --color-success-border:  rgba(0, 188, 212, 0.30);

  --color-warning:         #FFB347;
  --color-warning-bg:      rgba(255, 140, 0, 0.12);
  --color-warning-text:    #FFCC80;
  --color-warning-border:  rgba(255, 140, 0, 0.35);

  --color-error:           #E8405A;
  --color-error-bg:        rgba(196, 30, 58, 0.15);
  --color-error-text:      #FF8A9A;
  --color-error-border:    rgba(196, 30, 58, 0.40);

  --color-neutral:         #888888;
  --color-neutral-bg:      rgba(255,255,255,0.06);
  --color-neutral-text:    #BBBBBB;

  /* Sidebar specific (dark — pure black, logo-matched) */
  --sidebar-bg:            #000000;
  --sidebar-border:        rgba(255,255,255,0.06);
  --sidebar-text:          #888888;
  --sidebar-text-active:   #FF8C00;
  --sidebar-icon:          #555555;
  --sidebar-icon-active:   #FF8C00;
  --sidebar-item-active-bg: rgba(255, 140, 0, 0.12);
  --sidebar-item-active-border: #FF8C00;

  /* Shadows (dark theme — glow-based, brand-aware) */
  --shadow-xs:  0 1px 2px rgba(0,0,0,0.40);
  --shadow-sm:  0 1px 3px rgba(0,0,0,0.50), 0 1px 2px rgba(0,0,0,0.40);
  --shadow-md:  0 4px 6px rgba(0,0,0,0.50), 0 2px 4px rgba(0,0,0,0.40);
  --shadow-lg:  0 10px 15px rgba(0,0,0,0.55), 0 4px 6px rgba(0,0,0,0.40);
  --shadow-xl:  0 20px 25px rgba(0,0,0,0.60), 0 10px 10px rgba(0,0,0,0.40);
  --shadow-brand: 0 0 20px rgba(255, 140, 0, 0.40), 0 4px 14px rgba(255, 140, 0, 0.25);
  --shadow-brand-crimson: 0 0 20px rgba(196, 30, 58, 0.40), 0 4px 14px rgba(196, 30, 58, 0.25);
  --shadow-brand-teal: 0 0 20px rgba(0, 188, 212, 0.40), 0 4px 14px rgba(0, 188, 212, 0.25);
}
```

---

## ✍️ STEP 4 — TYPOGRAPHY SYSTEM

```
TASK: Create the typography token system.
File: frontend/src/styles/typography.css

Import from Google Fonts: Inter (fallback for Circular) + DM Sans

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=DM+Sans:wght@400;500;600;700;800&display=swap');

:root {
  /* Font families */
  --font-display:  'Circular', 'DM Sans', 'Inter', system-ui, sans-serif;
  --font-body:     'Inter', 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono:     'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;

  /* Font sizes */
  --text-2xs:   10px;
  --text-xs:    11px;
  --text-sm:    13px;
  --text-base:  14px;
  --text-md:    16px;
  --text-lg:    18px;
  --text-xl:    22px;
  --text-2xl:   26px;
  --text-3xl:   32px;
  --text-4xl:   40px;
  --text-5xl:   56px;

  /* Font weights */
  --weight-regular:   400;
  --weight-medium:    500;
  --weight-semibold:  600;
  --weight-bold:      700;
  --weight-extrabold: 800;
  --weight-black:     900;

  /* Line heights */
  --leading-tight:    1.20;
  --leading-snug:     1.35;
  --leading-normal:   1.50;
  --leading-relaxed:  1.65;
  --leading-loose:    1.80;

  /* Letter spacing */
  --tracking-tight:   -0.03em;
  --tracking-snug:    -0.01em;
  --tracking-normal:   0em;
  --tracking-wide:     0.03em;
  --tracking-wider:    0.06em;
  --tracking-widest:   0.12em;

  /* Spacing scale (8px grid) */
  --space-1:   4px;
  --space-2:   8px;
  --space-3:   12px;
  --space-4:   16px;
  --space-5:   20px;
  --space-6:   24px;
  --space-8:   32px;
  --space-10:  40px;
  --space-12:  48px;
  --space-16:  64px;
  --space-20:  80px;
  --space-24:  96px;

  /* Border radius */
  --radius-xs:   4px;
  --radius-sm:   6px;
  --radius-md:   8px;
  --radius-lg:   12px;
  --radius-xl:   16px;
  --radius-2xl:  24px;
  --radius-full: 9999px;

  /* Transitions */
  --transition-fast:    100ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-base:    180ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow:    280ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-spring:  400ms cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

---

## 🧩 STEP 5 — COMPONENT SYSTEM UPGRADES

```
TASK: Upgrade or create these shared components. Apply dual-theme tokens throughout.
Every component MUST work perfectly in both light and dark themes.

════════════════════════════════════
COMPONENT 1: Button
════════════════════════════════════
Variants: primary | secondary | ghost | destructive | outline | link
Sizes: sm | md | lg

Primary button — THE WOW BUTTON:
  background: var(--brand-orange)       → OR use gradient for hero CTAs
  Hero CTA gradient: linear-gradient(135deg, #FF8C00, #C41E3A)
  color: white
  border-radius: var(--radius-lg)
  padding: 10px 20px (md), 8px 16px (sm), 14px 28px (lg)
  font-weight: var(--weight-semibold)
  font-size: var(--text-base)
  letter-spacing: var(--tracking-snug)
  box-shadow: var(--shadow-brand) on hover
  transform: translateY(-1px) on hover
  transform: translateY(0) on active
  transition: var(--transition-base)

Secondary button:
  background: var(--bg-surface)
  border: 1.5px solid var(--border-default)
  color: var(--text-primary)
  hover: border-color: var(--brand-orange), color: var(--brand-orange)

Ghost button:
  background: transparent
  color: var(--text-secondary)
  hover: background: var(--bg-hover), color: var(--text-primary)

Destructive button:
  background: var(--color-error)
  hover: box-shadow: var(--shadow-brand-crimson)

Loading state: Show animated spinner (3 rotating dots in brand colors)
Disabled state: opacity: 0.45, cursor: not-allowed, no hover effects

════════════════════════════════════
COMPONENT 2: StatusBadge / Chip
════════════════════════════════════
Variants: success | warning | error | info | neutral | orange | crimson | teal

success  → text: var(--color-success-text), bg: var(--color-success-bg), border: var(--color-success-border)
warning  → text: var(--color-warning-text), bg: var(--color-warning-bg), border: var(--color-warning-border)
error    → text: var(--color-error-text), bg: var(--color-error-bg), border: var(--color-error-border)
info     → text: var(--color-info-text), bg: var(--color-info-subtle), border: var(--color-info)
teal     → text: var(--brand-teal), bg: var(--brand-teal-glow), border: var(--brand-teal)

Each badge has: dot indicator (4px circle, same color as text) + label text
border: 1px solid (matching color, 30% opacity)
border-radius: var(--radius-full)
font-size: var(--text-xs), font-weight: var(--weight-medium)
padding: 3px 10px
letter-spacing: var(--tracking-wide)

════════════════════════════════════
COMPONENT 3: Input / Form Fields
════════════════════════════════════
Default state:
  background: var(--bg-surface-sunken)
  border: 1.5px solid var(--border-default)
  border-radius: var(--radius-md)
  padding: 10px 14px
  font-size: var(--text-base)
  color: var(--text-primary)
  transition: var(--transition-fast)

Focus state:
  border-color: var(--brand-orange)
  box-shadow: 0 0 0 3px var(--brand-orange-glow)
  background: var(--bg-surface)
  outline: none

Error state:
  border-color: var(--color-error)
  box-shadow: 0 0 0 3px var(--brand-crimson-glow)

Success/validated state:
  border-color: var(--brand-teal)
  box-shadow: 0 0 0 3px var(--brand-teal-glow)

Label: font-size var(--text-sm), weight var(--weight-medium), color var(--text-secondary)
Helper text: font-size var(--text-xs), color var(--text-tertiary)
Error message: font-size var(--text-xs), color var(--color-error-text)

════════════════════════════════════
COMPONENT 4: Card
════════════════════════════════════
Default card:
  background: var(--bg-surface)
  border: 1px solid var(--border-default)
  border-radius: var(--radius-xl)
  box-shadow: var(--shadow-sm)
  padding: var(--space-6)
  transition: var(--transition-base)

Hoverable card (add .card-hoverable):
  hover: transform: translateY(-2px)
  hover: box-shadow: var(--shadow-lg)
  hover: border-color: var(--brand-orange) at 30% opacity

Stat card (KPI / analytics):
  Has a subtle left border: 3px solid var(--brand-orange) OR var(--brand-teal) OR var(--brand-crimson)
  The left border color rotates across cards to create visual rhythm
  Dark theme: card background has very subtle gradient:
    background: linear-gradient(135deg, var(--bg-surface) 0%, rgba(255,140,0,0.03) 100%)

════════════════════════════════════
COMPONENT 5: Table
════════════════════════════════════
Table wrapper:
  border: 1px solid var(--border-default)
  border-radius: var(--radius-xl)
  overflow: hidden
  background: var(--bg-surface)

Header row:
  background: var(--bg-surface-sunken)
  border-bottom: 2px solid var(--border-default)
  font-size: var(--text-sm)
  font-weight: var(--weight-semibold)
  color: var(--text-secondary)
  letter-spacing: var(--tracking-wider)
  text-transform: uppercase
  padding: 14px 16px

Data row:
  height: 56px
  border-bottom: 1px solid var(--border-default)
  font-size: var(--text-base)
  color: var(--text-primary)
  padding: 0 16px
  transition: background var(--transition-fast)
  hover: background: var(--bg-hover)

Last row: border-bottom: none

════════════════════════════════════
COMPONENT 6: Sidebar Navigation
════════════════════════════════════
Sidebar:
  width: 240px
  background: var(--sidebar-bg)       ← pure black in dark theme = logo bg match 🔥
  border-right: 1px solid var(--sidebar-border)
  display: flex, flex-direction: column
  height: 100vh, position: fixed

Logo section (top):
  padding: 20px 16px 16px
  border-bottom: 1px solid var(--sidebar-border)
  Use Logo component, size="md", variant="icon-text"

Nav section:
  padding: var(--space-4) var(--space-3)
  flex: 1, overflow-y: auto

Nav group label:
  font-size: var(--text-2xs)
  font-weight: var(--weight-semibold)
  color: var(--sidebar-icon)
  letter-spacing: var(--tracking-widest)
  text-transform: uppercase
  padding: 16px 12px 6px

Nav item (inactive):
  display: flex, align-items: center, gap: 10px
  padding: 9px 12px
  border-radius: var(--radius-md)
  font-size: var(--text-base)
  color: var(--sidebar-text)
  font-weight: var(--weight-medium)
  transition: var(--transition-fast)
  cursor: pointer
  margin-bottom: 2px
  hover: background: var(--bg-hover), color: var(--text-primary)
  Icon: 18px, color: var(--sidebar-icon)

Nav item (ACTIVE):
  background: var(--sidebar-item-active-bg)
  color: var(--sidebar-text-active) = var(--brand-orange) 🔥
  font-weight: var(--weight-semibold)
  border-left: 3px solid var(--sidebar-item-active-border) = var(--brand-orange) 🔥
  padding-left: 9px (adjust for border)
  Icon: var(--sidebar-icon-active) = var(--brand-orange) 🔥

  Dark theme EXTRA: Active item gets subtle orange glow:
    box-shadow: inset 0 0 20px rgba(255, 140, 0, 0.05)

Bottom section (user profile):
  margin-top: auto
  padding: var(--space-4) var(--space-3)
  border-top: 1px solid var(--sidebar-border)
  User avatar + name + role label
  Theme toggle button (sun/moon icon)

════════════════════════════════════
COMPONENT 7: Theme Toggle
════════════════════════════════════
A pill-shaped toggle in the sidebar bottom section.
Uses system preference as default (prefers-color-scheme).
Saves preference to localStorage key: 'airad-theme'

Toggle appearance:
  Light mode icon: ☀️ (Sun)
  Dark mode icon: 🌙 (Moon)
  Container: pill shape, background: var(--bg-surface-raised)
  Active indicator: slides with CSS transition var(--transition-spring)
  Active icon bg: linear-gradient(135deg, #FF8C00, #C41E3A)

ThemeProvider wraps the app root, applies data-theme attribute to <html> element.

════════════════════════════════════
COMPONENT 8: Page Header
════════════════════════════════════
Every page has a consistent page header:
  Page title: font-size var(--text-3xl), weight var(--weight-bold), color var(--text-primary)
  Subtitle / breadcrumb: font-size var(--text-base), color var(--text-secondary)
  Right side: action buttons (primary CTA, secondary actions)
  Border-bottom: 1px solid var(--border-default) OR just generous margin-bottom
  Padding-bottom: var(--space-6)
  Margin-bottom: var(--space-8)

════════════════════════════════════
COMPONENT 9: Toast / Notification
════════════════════════════════════
Position: top-right, stacked
border-radius: var(--radius-lg)
padding: var(--space-4) var(--space-5)
min-width: 300px, max-width: 420px
box-shadow: var(--shadow-xl)
border-left: 4px solid (color based on type)
animation: slide in from right + fade

success toast: border-left: var(--brand-teal), icon: checkmark in teal
error toast:   border-left: var(--brand-crimson), icon: X in crimson
warning toast: border-left: var(--brand-orange), icon: ⚠️ in orange
info toast:    border-left: var(--brand-teal), icon: ℹ️ in teal

Dark theme: background var(--bg-surface-raised) with higher contrast

════════════════════════════════════
COMPONENT 10: Empty State
════════════════════════════════════
Centered layout, generous vertical padding (var(--space-20))
Large icon: 64px, color: var(--text-tertiary)
Title: var(--text-xl), weight var(--weight-semibold), color var(--text-primary)
Description: var(--text-md), color var(--text-secondary), max-width 360px, centered
CTA: Primary button with brand gradient
Optional: subtle brand gradient bg strip behind icon area
```

---

## 🏠 STEP 6 — PAGE-LEVEL DESIGN UPGRADES

```
TASK: Apply design upgrades to every existing page/screen.

════════════
LOGIN PAGE
════════════
Layout: Split screen — left side 45% brand panel, right side 55% form
Left panel:
  background: #000000 (matches logo background exactly)
  Centered logo: Logo component size="xl" variant="full-lockup"
  Below logo: tagline "Discover What's Near" in var(--brand-teal)
  Abstract background: 3 glowing orbs matching brand colors
    Orb 1: radial-gradient from var(--brand-orange-glow) at 30% 30%
    Orb 2: radial-gradient from var(--brand-crimson-glow) at 70% 60%
    Orb 3: radial-gradient from var(--brand-teal-glow) at 20% 80%
    filter: blur(60px), opacity 0.6, pointer-events: none
Right panel:
  background: var(--bg-base)
  padding: 48px
  Form card: var(--bg-surface), border-radius: var(--radius-2xl), padding: var(--space-10)
  box-shadow: var(--shadow-xl)

════════════════
DASHBOARD / HOME
════════════════
KPI stat cards at top: 4 cards, each with left accent border in brand colors (orange, teal, crimson, orange)
Charts: use brand colors — orange for primary series, teal for secondary, crimson for tertiary
Page background: var(--bg-base) NOT white
Section headers: styled with PageHeader component

════════════════════
TABLES / LIST PAGES
════════════════════
Wrap all tables in the Table component (rounded, shadowed)
Add a "sticky" table header that stays fixed on scroll
Search/filter bar above table: pill-shaped search input + filter chips
Filter chips use brand badge colors
Pagination at bottom: styled with brand primary color for active page
Row actions (edit/delete): appear on hover, ghost buttons that reveal

════════════════════
MODALS / DIALOGS
════════════════════
backdrop-filter: blur(8px) on overlay (glassmorphism backdrop)
Modal container: var(--bg-surface), border-radius: var(--radius-2xl)
box-shadow: var(--shadow-xl) PLUS:
  Dark theme: 0 0 0 1px rgba(255,140,0,0.15) — subtle brand glow border
Header: border-bottom 1px solid var(--border-default), padding var(--space-6)
Footer: border-top 1px solid var(--border-default), padding var(--space-5) var(--space-6)
Close button: top-right, ghost, hover: brand color
```

---

## 🌟 STEP 7 — WOW MICRO-DETAILS (This is what separates good from WOW)

```
TASK: Add these micro-details throughout the app. Every single one matters.

1. BRAND GLOW ON DARK SIDEBAR LOGO:
   When in dark theme, the logo in the sidebar has a very subtle ambient glow:
   filter: drop-shadow(0 0 12px rgba(255, 140, 0, 0.25))
   Only applies in dark theme. Subtle. Premium.

2. GRADIENT FAVICON PULSE (login page only):
   The favicon in browser tab pulses between brand colors via CSS animation.
   This is a delightful surprise for the person who notices.

3. ACTIVE SIDEBAR INDICATOR:
   The 3px left border on the active nav item is NOT a flat color.
   It's a mini gradient: linear-gradient(180deg, #FF8C00, #C41E3A)
   This echoes the logo's petal colors.

4. BUTTON GRADIENT SHINE:
   Primary buttons in dark theme get a subtle shine overlay on hover:
   ::before pseudo-element with linear-gradient(transparent → white 5% → transparent)
   Animates left-to-right on hover (shimmer effect).

5. CARD HOVER GLOW (dark theme only):
   Hoverable cards get a very subtle brand-colored border on hover:
   border-color: rgba(255, 140, 0, 0.25)
   No glow on light theme — clean and minimal there.

6. FOCUS RING CONSISTENCY:
   ALL focusable elements must have:
   outline: none;
   box-shadow: 0 0 0 3px var(--brand-orange-glow);
   This is the brand focus ring. Consistent everywhere.

7. SCROLLBAR STYLING:
   ::-webkit-scrollbar { width: 6px; height: 6px; }
   ::-webkit-scrollbar-track { background: var(--bg-base); }
   ::-webkit-scrollbar-thumb {
     background: var(--border-strong);
     border-radius: var(--radius-full);
   }
   ::-webkit-scrollbar-thumb:hover { background: var(--brand-orange); }

8. LOADING STATES:
   Skeleton loaders use animated shimmer gradient:
   background: linear-gradient(90deg, var(--bg-surface-sunken) 25%, var(--bg-hover) 50%, var(--bg-surface-sunken) 75%)
   background-size: 200% 100%
   animation: shimmer 1.5s infinite

9. TABLE ROW SELECTION:
   Selected rows get: background: var(--color-primary-subtle)
   Left border: 2px solid var(--brand-orange)

10. PAGE TRANSITION:
    Route changes animate with: opacity 0→1 + translateY(8px→0)
    Duration: 200ms, easing: ease-out
    This makes the app feel alive and responsive.

11. STAT NUMBER ANIMATION:
    KPI numbers on dashboard animate from 0 to their value on page load
    Use a count-up effect. Duration: 800ms, easing: ease-out
    The numbers feel like they're "revealing" the data.

12. BRAND GRADIENT DIVIDERS:
    In key locations (auth page, section breaks), use:
    height: 2px
    background: var(--gradient-brand)
    border: none
    These add a premium brand flourish.

13. EMPTY STATE ILLUSTRATION:
    Use the logo icon itself (large, 80px, low opacity 0.12) as the
    background watermark for empty state pages. Subtle brand presence.
```

---

## ⚙️ STEP 8 — THEME PROVIDER SETUP

```
TASK: Set up ThemeProvider at app root level.

FILE: frontend/src/context/ThemeContext.tsx

- Reads saved preference from localStorage('airad-theme')
- Falls back to system preference: window.matchMedia('(prefers-color-scheme: dark)')
- Default fallback: 'dark' (the app looks more premium in dark mode)
- Applies data-theme="light" or data-theme="dark" to document.documentElement
- Exports useTheme() hook: { theme, toggleTheme, setTheme }

FILE: frontend/src/main.tsx or App.tsx
- Wrap entire app in <ThemeProvider>
- Apply CSS: transition: background-color 200ms ease, color 200ms ease to :root
  so theme switch feels smooth, not jarring

IMPORTANT: NEVER use hardcoded color values (#hex or rgb()) anywhere in components.
Only use CSS custom properties (var(--token-name)).
This is what makes the theme switch work instantly and perfectly.
```

---

## 📱 STEP 9 — FLUTTER APP DESIGN TOKENS (if Flutter app exists)

```
TASK: Mirror the design system in Flutter.
FILE: mobile/lib/core/theme/app_theme.dart

Create AppTheme class with:
  - static ThemeData lightTheme
  - static ThemeData darkTheme
  - static AppColors lightColors
  - static AppColors darkColors

AppColors class (use extension on ThemeData):
  brandOrange:    Color(0xFFFF8C00)
  brandCrimson:   Color(0xFFC41E3A)
  brandTeal:      Color(0xFF00BCD4)
  brandBlack:     Color(0xFF000000)
  gradientBrand:  LinearGradient([brandOrange, brandCrimson, brandTeal])

Light ThemeData:
  colorScheme: ColorScheme.light with primary: brandOrange, secondary: brandTeal, error: brandCrimson
  scaffoldBackgroundColor: Color(0xFFF5F5F5)
  cardColor: Color(0xFFFFFFFF)
  dividerColor: Color(0xFFE0E0E0)

Dark ThemeData:
  colorScheme: ColorScheme.dark with primary: brandOrange, secondary: brandTeal, error: brandCrimson
  scaffoldBackgroundColor: Color(0xFF0A0A0A)
  cardColor: Color(0xFF141414)
  dividerColor: Color(0xFF1F1F1F)

AppBar (both themes):
  backgroundColor: Colors.black (matches logo bg)
  elevation: 0
  titleTextStyle: brandOrange for app name

Bottom nav active color: brandOrange
FAB color: gradient from brandOrange to brandCrimson
```

---

## ✅ STEP 10 — QUALITY CHECKLIST (Verify before finishing)

```
Before marking this task complete, verify ALL of the following:

LOGO:
[ ] airad_icon3x.png copied to all required asset locations
[ ] Favicons generated (16, 32, 64, 180px)
[ ] Logo component renders in all sizes and variants
[ ] Logo looks correct in both light and dark themes
[ ] Wordmark gradient applied correctly (orange → crimson → teal)
[ ] Logo black background preserved on light surfaces (not stripped)

THEMING:
[ ] All 3 brand colors (orange, crimson, teal) used in the UI — none absent
[ ] Dark theme sidebar is pure black (#000000) matching logo background
[ ] Light theme feels clean and premium — no harsh contrasts
[ ] Dark theme feels rich and immersive — not just "grey everything"
[ ] Theme toggle works smoothly with CSS transition
[ ] System preference detected on first visit
[ ] Theme preference persisted across browser sessions
[ ] ZERO hardcoded hex values in component files — all use var()

COMPONENTS:
[ ] Buttons have brand glow shadow on hover
[ ] Active nav item has orange left border + orange text + orange icon
[ ] Cards have subtle hover elevation in light, glow in dark
[ ] Tables have rounded corners and no harsh borders
[ ] Inputs have orange focus ring (not default browser outline)
[ ] Badges use semantic brand colors
[ ] Toasts appear top-right with brand-color left border
[ ] All modals have blur backdrop

MICRO-DETAILS:
[ ] Dark theme logo has subtle orange drop-shadow glow
[ ] Scrollbar styled with brand hover color
[ ] Skeleton loaders use shimmer animation
[ ] Page transitions animate smoothly
[ ] Focus rings are brand-colored on all interactive elements

ACCESSIBILITY:
[ ] All text meets WCAG AA contrast in BOTH themes
[ ] No color used as the sole indicator of status (always paired with icon/text)
[ ] All interactive elements keyboard navigable
[ ] Focus visible at all times (never outline: none without replacement)

CONSISTENCY:
[ ] All spacing uses var(--space-N) tokens — no arbitrary px values
[ ] All border-radius uses var(--radius-N) tokens
[ ] All shadows use var(--shadow-N) tokens
[ ] All transitions use var(--transition-N) tokens
[ ] Font sizes use var(--text-N) tokens
```

---

## 🚀 EXECUTION ORDER

```
Execute in this exact sequence to avoid rework:

1. STEP 1  — Copy and resize logo to all locations
2. STEP 4  — Create typography.css with all tokens
3. STEP 3  — Create tokens.css with full dual-theme color system
4. STEP 8  — Set up ThemeProvider at app root
5. STEP 2  — Build Logo component
6. STEP 5  — Build/upgrade all shared components
7. STEP 6  — Upgrade page layouts one by one
8. STEP 7  — Add micro-details pass
9. STEP 9  — Flutter theme (if app exists)
10. STEP 10 — Run full quality checklist

Do NOT skip steps. Do NOT start page work before component system is done.
The component system is the foundation — everything else is built on top of it.
```

---

> **REMINDER TO WINDSURF:**
> This is an aesthetic and branding upgrade pass only.
> Do NOT change any API calls, business logic, routing, or data models.
> If in doubt about a color choice, always go back to the logo: Orange → Crimson → Teal → Black.
> Those four colors tell you everything you need to know about what AirAd looks like.
> The goal: **someone opens this app and says "WOW" in the first 3 seconds.**
