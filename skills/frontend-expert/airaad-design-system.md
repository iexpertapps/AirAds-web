# AirAd — Airbnb Design Language System (DLS)
**Version:** 2.0 · **Date:** February 2026 · **Status:** Approved for Phase-1 Execution — Brand Elevation Update

> All UI in the AirAd Data Collection Portal **must** comply with sections A1–A14. No exceptions.

---

## A1 — Design Principles

| Principle | Definition | Portal Application |
|-----------|-----------|-------------------|
| **Unified** | Consistent experience across all surfaces | Same component library, token system, and interaction patterns across all 10 portal pages |
| **Universal** | Accessible and inclusive by default | WCAG 2.1 AA minimum, keyboard nav, screen reader labels on all tables and forms |
| **Iconic** | Bold, premium, instantly recognizable as AirAd | Logo-derived color system (orange/crimson/teal/black), purposeful gradients, ambient glow — every surface must feel intentional |
| **Conversational** | Design feels human — warm, clear, direct | Form labels as plain-language questions, error messages with helpful guidance, not codes |

---

## A2 — Color System

Apply as CSS custom properties. **Never hardcode hex values in components.**
The AirAd brand logo (three overlapping petals: orange, crimson, teal on black) is the single source of truth for all color decisions.

```css
:root {
  /* ── AirAd Brand Primitives (logo-derived) ── */
  --brand-orange:        #F97316;  /* Primary CTAs, active states, glow accents */
  --brand-crimson:       #DC2626;  /* Destructive actions, error states, gradient pair */
  --brand-teal:          #0D9488;  /* Success states, approvals, data viz */
  --brand-black:         #0A0A0A;  /* Sidebar bg, logo container, hero backgrounds */

  /* ── Brand Gradients ── */
  --gradient-brand-text:      linear-gradient(90deg, #F97316 0%, #DC2626 50%, #0D9488 100%);
  --gradient-active-indicator: linear-gradient(180deg, #F97316 0%, #DC2626 100%);
  --gradient-primary-btn:      linear-gradient(135deg, #F97316 0%, #DC2626 100%);
  --gradient-hero:             radial-gradient(ellipse 120% 80% at 50% 0%, rgba(249,115,22,0.08) 0%, transparent 60%);

  /* ── Extended Neutrals ── */
  --color-white:         #FFFFFF;
  --color-grey-100:      #F5F5F4;  /* Light page backgrounds */
  --color-grey-200:      #E7E5E4;  /* Light card borders, dividers */
  --color-grey-300:      #D6D3D1;  /* Light input borders (default) */
  --color-grey-400:      #A8A29E;  /* Placeholder text, muted icons */
  --color-grey-500:      #78716C;  /* Secondary text (light mode) */
  --color-grey-700:      #44403C;  /* Primary text (light mode) */
  --color-grey-900:      #1C1917;  /* Headings (light mode) */

  /* ── Semantic Colors ── */
  --color-success:       #0D9488;  /* = brand-teal */
  --color-success-bg:    rgba(13,148,136,0.10);
  --color-success-text:  #0D9488;
  --color-warning:       #F97316;  /* = brand-orange */
  --color-warning-bg:    rgba(249,115,22,0.10);
  --color-warning-text:  #F97316;
  --color-error:         #DC2626;  /* = brand-crimson */
  --color-error-bg:      rgba(220,38,38,0.10);
  --color-error-text:    #DC2626;
  --color-info:          #0D9488;
  --color-info-bg:       rgba(13,148,136,0.10);
  --color-info-text:     #0D9488;

  /* ── Dark Theme Surfaces (default) ── */
  --surface-page:        #111111;
  --surface-sidebar:     #0A0A0A;  /* = brand-black */
  --surface-topbar:      #141414;
  --surface-card:        #1C1C1C;
  --surface-modal:       #1C1C1C;
  --surface-input:       #1A1A1A;
  --surface-hover:       #242424;

  /* ── Dark Theme Text ── */
  --text-primary:        #F5F5F4;
  --text-secondary:      #A8A29E;

  /* ── Dark Theme Borders ── */
  --border-default:      #2A2A2A;
  --border-input:        #3A3A3A;

  /* ── Shadows ── */
  --shadow-card:         0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3);
  --shadow-modal:        0 24px 64px rgba(0,0,0,0.6), 0 8px 24px rgba(0,0,0,0.4);
  --shadow-sidebar-glow: 4px 0 24px rgba(249,115,22,0.06);
}

/* ── Light Theme Overrides ── */
[data-theme="light"] {
  --surface-page:    #F5F5F4;
  --surface-sidebar: #FFFFFF;
  --surface-topbar:  #FFFFFF;
  --surface-card:    #FFFFFF;
  --surface-modal:   #FFFFFF;
  --surface-input:   #FFFFFF;
  --surface-hover:   #F5F5F4;
  --text-primary:    #1C1917;
  --text-secondary:  #78716C;
  --border-default:  #E7E5E4;
  --border-input:    #D6D3D1;
  --shadow-card:     0 1px 2px rgba(0,0,0,0.08);
  --shadow-sidebar-glow: none;
}
```

**Color usage rules:**
- `--brand-orange` → Primary action buttons, active nav indicators, focus rings. Maximum **1 dominant use per view**.
- `--brand-teal` → Success/completion states (GPS Validated badges, Approved status).
- `--brand-crimson` → Destructive actions, error states, gradient pair with orange.
- `--brand-black` → Sidebar background, logo container — **always preserve this background behind the logo**.
- `--gradient-brand-text` → Product name "AirAd" only — never on body copy or generic headings.
- **Dark theme is the primary/default theme.** Light theme is fully supported but secondary.
- **Never use color alone** to convey status — always pair with icon + label text.
- Page backgrounds: `--surface-page` token (never hardcode).

---

## A3 — Typography

**Font:** Circular (approximated with DM Sans for web).

```css
--font-family-base: 'Circular', 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-family-mono: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
```

| Token | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `--text-display` | 32px | 700 | 1.25 | Page hero titles (Dashboard H1) |
| `--text-heading-xl` | 26px | 600 | 1.3 | Section headings |
| `--text-heading-lg` | 22px | 600 | 1.35 | Card titles, modal headers |
| `--text-heading-md` | 18px | 600 | 1.4 | Subsection titles |
| `--text-heading-sm` | 16px | 600 | 1.4 | Table column headers |
| `--text-body-lg` | 16px | 400 | 1.6 | Primary body text |
| `--text-body-md` | 14px | 400 | 1.6 | Default UI text, table rows |
| `--text-body-sm` | 12px | 400 | 1.5 | Meta text, timestamps, captions |
| `--text-label` | 13px | 500 | 1.4 | Form labels, badge text |
| `--text-caption` | 11px | 400 | 1.4 | Footnotes, tooltips (min size) |

**Rules:**
- Minimum font size: **11px**
- Body text minimum contrast: **4.5:1** against background (WCAG AA)
- Never use more than **3 font weights** in a single view
- Use **sentence case** everywhere — not Title Case

---

## A4 — Spacing System (8px Base Grid)

All spacing must follow multiples of 8px. **Never use arbitrary pixel values.**

```css
:root {
  --space-1:  4px;   /* Tight: icon-to-label gaps */
  --space-2:  8px;   /* XS: inline element spacing */
  --space-3:  12px;  /* SM: tight component padding */
  --space-4:  16px;  /* MD: default component padding */
  --space-5:  20px;
  --space-6:  24px;  /* LG: card padding, section gaps */
  --space-8:  32px;  /* XL: between major sections */
  --space-10: 40px;  /* 2XL: page-level breathing room */
  --space-12: 48px;  /* 3XL: hero sections */
  --space-16: 64px;  /* 4XL: full-bleed separations */
}
```

**Grid system:**
- Sidebar width: `240px` (fixed)
- Content area max-width: `1280px` (centered)
- Page padding: `32px` horizontal, `40px` vertical top
- Card grid gap: `24px` minimum
- Table row height: `56px`
- Topbar height: `64px`

---

## A5 — Component Library

### A5.1 Buttons

```tsx
<Button variant="primary">     // bg: --gradient-primary-btn (orange→crimson) + glow shadow
<Button variant="secondary">   // bg: --surface-card, border: 1px --border-default
<Button variant="ghost">       // bg: transparent, hover: --surface-hover
<Button variant="destructive"> // bg: --color-error-bg, border: --brand-crimson — destructive only
```

**Rules:**
- Border radius: `8px`
- Min height: `48px` (primary), `40px` (secondary/ghost)
- Padding: `12px 24px` (primary), `10px 20px` (secondary)
- Primary button: `box-shadow: 0 2px 8px rgba(249,115,22,0.30)` at rest; glow intensifies on hover; `translateY(1px)` on active
- Loading state: spinner replaces label (never disable without feedback)
- Focus state: `2px solid --brand-orange` outline, `2px offset`
- Button labels: verb + noun — `"Import CSV"`, `"Approve vendor"`, `"View details"` — never `"OK"` or `"Submit"`

### A5.2 Form Inputs

```css
.dls-input {
  height: 40px;                          /* DLS standard height */
  border: 1px solid var(--border-input);
  border-radius: 8px;
  padding: 0 16px;
  font-size: 14px;
  color: var(--text-primary);
  background: var(--surface-input);
  transition: border-color 150ms ease, background 150ms ease;
}

.dls-input:hover  { border-color: var(--color-grey-500); }
.dls-input:focus  { border-color: var(--brand-orange);
                    outline: 2px solid var(--brand-orange);
                    outline-offset: 2px; }
.dls-input.error  { border-color: var(--brand-crimson); }
.dls-input.valid  { border-color: var(--brand-teal); }
```

**Rules:**
- Validate on **blur**, not on every keystroke
- Error messages appear **below** the input in `--color-error`
- Required fields: asterisk (*) in label + `aria-describedby` for screen readers
- Never use placeholder-only labels (accessibility failure)

### A5.3 Cards

```css
.dls-card {
  background: var(--surface-card);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow-card);
}
```

**Rules:**
- Card background always `--surface-card` (dark: `#1C1C1C`, light: `#FFFFFF`)
- Status/KPI cards: left border `4px solid` in semantic color (`--brand-teal` success, `--brand-orange` warning, `--brand-crimson` error)
- Avoid nesting cards inside cards (max 1 level)

### A5.4 Data Tables

```
Header row:   background --surface-hover, font --text-heading-sm, color --text-primary, border-bottom 1px --border-default
Data rows:    height 56px, padding 12px 16px, border-bottom 1px --border-default, color --text-primary
Hover:        background --surface-hover
Selected:     background rgba(249,115,22,0.06), left border 3px --brand-orange
```

**Rules:**
- Always show row count: `"Showing 1–25 of 4,218 vendors"`
- Pagination: 25 rows default (options: 10 / 25 / 50 / 100)
- Sticky header on all tables with more than 10 rows
- Loading state: **skeleton rows** (not spinner) — same height as real rows
- Empty state: illustration + explanation + action CTA (never blank)

### A5.5 Status Badges / Chips

```tsx
<Badge variant="success">Approved</Badge>   // bg: rgba(13,148,136,0.10), text: --brand-teal, border: rgba(13,148,136,0.20)
<Badge variant="warning">Pending</Badge>    // bg: rgba(249,115,22,0.10),  text: --brand-orange, border: rgba(249,115,22,0.20)
<Badge variant="error">Rejected</Badge>     // bg: rgba(220,38,38,0.10),   text: --brand-crimson, border: rgba(220,38,38,0.20)
<Badge variant="info">Processing</Badge>    // bg: rgba(13,148,136,0.10),  text: --brand-teal, border: rgba(13,148,136,0.20)
<Badge variant="neutral">Unclaimed</Badge>  // bg: --surface-hover, text: --text-primary, border: --border-default
```

**Rules:**
- Border radius: `100px` (pill shape)
- Padding: `4px 10px`
- Font: `--text-label` (13px, weight 500)
- Always include icon/dot prefix — **never text alone**

### A5.6 Modals / Drawers

- Overlay: `rgba(0,0,0,0.65)` + `backdrop-filter: blur(4px)`
- Modal container: `--surface-modal`, `border: 1px solid --border-default`, `border-radius: 16px`, `padding: 32px`, `box-shadow: --shadow-modal`
- Max-width: `480px` (confirmations), `640px` (forms)
- Slide-in Drawer: `width: 480px`, from right, `background: --surface-modal`, `border-left: 1px solid --border-default`
- Close: X button + ESC key + backdrop click
- Always **trap focus** inside modal
- Action buttons: right-aligned, primary button is **rightmost**

### A5.7 Sidebar Navigation

```
Width: 240px fixed (collapsed: 64px)
Background: --surface-sidebar (dark: --brand-black #0A0A0A)
Nav item height: 44px
Nav item border-radius: 0 100px 100px 0  (pill-right)
Nav item margin-right: 8px

Logo area:
  - Icon: 36×36px rounded container, background: --brand-black
  - Dark mode: box-shadow: 0 0 20px rgba(249,115,22,0.25), 0 0 40px rgba(249,115,22,0.10)
  - Wordmark "AirAd": --gradient-brand-text applied as background-clip: text

States:
  default → text: --text-secondary
  hover   → background: --surface-hover, text: --text-primary
  active  → background: rgba(249,115,22,0.10), text: --brand-orange, weight: 600
             + left edge indicator: 3px wide, top/bottom 6px inset, background: --gradient-active-indicator

Section labels: 11px, 700, uppercase, letter-spacing: 1px, color: --text-secondary
```

### A5.8 Empty States

Every list/table must have an empty state:

```
[Simple line-art illustration]
     Heading: Clear, plain language
  Subheading: Why it's empty + what to do
      Button: Primary action to fill the empty state
```

Examples:
- Vendors table empty → `"No vendors yet — start by importing data"` + `[Import CSV]`
- QA queue empty → `"You're all caught up! No vendors pending GPS validation"`

---

## A6 — Iconography

**Library:** `lucide-react` exclusively.

**Rules:**
- Size: `16px` (inline), `20px` (nav), `24px` (standalone), `32px` (empty states)
- Stroke width: `1.5` (Airbnb signature — not bold 2.0)
- Stroke only — **never filled icons**
- Always pair icons with visible text labels in navigation

---

## A7 — Motion & Animation

```css
--duration-instant:  100ms;  /* Hover state changes */
--duration-fast:     150ms;  /* Button presses, badge changes */
--duration-normal:   250ms;  /* Modal open, drawer slide */
--duration-slow:     350ms;  /* Page transitions */
--ease-standard:     cubic-bezier(0.4, 0, 0.2, 1);
--ease-enter:        cubic-bezier(0.0, 0.0, 0.2, 1);
--ease-exit:         cubic-bezier(0.4, 0.0, 1, 1);
```

**Rules:**
- `prefers-reduced-motion: reduce` → disable ALL animations
- Skeleton loaders: `1.5s` shimmer, `linear`, infinite
- Page entry: `fadeUp` — `opacity 0→1` + `translateY(8px→0)`, `250ms`
- Drawer slide: `350ms ease-standard` from right
- Toast: slide from bottom-right, auto-dismiss `4s`
- **No bouncing, spinning, or looping animations** in production UI

---

## A8 — Layout System

```
┌────────────────────────────────────────────────────────┐
│  TOPBAR  [Breadcrumb]     [Search]   [Notif] [Avatar]  │ height: 64px
├──────────┬─────────────────────────────────────────────┤
│          │                                              │
│ SIDEBAR  │  PAGE CONTENT AREA                          │
│ 240px    │  max-width: 1280px, padding: 40px 32px      │
│ fixed    │                                              │
│          │  ┌──────────────────────────────────────┐   │
│          │  │ PAGE HEADER (title + actions)         │   │ height: 80px
│          │  ├──────────────────────────────────────┤   │
│          │  │ FILTERS BAR                           │   │ height: 56px
│          │  ├──────────────────────────────────────┤   │
│          │  │ MAIN CONTENT (table / cards / map)    │   │
│          │  └──────────────────────────────────────┘   │
└──────────┴─────────────────────────────────────────────┘
```

**Page Header pattern:**
```tsx
<PageHeader
  title="Vendor management"       // --text-display, sentence case
  subtitle="4,218 vendors total"  // --text-body-lg, --color-foggy
  actions={<Button variant="primary">Import CSV</Button>}
/>
```

**Filters Bar pattern:**
```tsx
<FiltersBar>
  <SearchInput placeholder="Search vendors..." />
  <Select label="City" />
  <Select label="QC Status" />
  <Select label="Data source" />
  <Button variant="ghost">Clear filters</Button>
  <span>Showing 4,218 results</span>
</FiltersBar>
```

---

## A9 — Form Design

- Single-column for fewer than 8 fields; two-column grid for longer forms
- Most important / required fields first
- Submit button: right-aligned on desktop, full-width on mobile
- Validation on **blur** only

---

## A10 — Data Visualization (Recharts)

**Chart color sequence:**
1. `--brand-orange`  (#F97316) — primary series
2. `--brand-teal`    (#0D9488) — secondary series
3. `--brand-crimson` (#DC2626) — tertiary / error series
4. `--color-grey-400` (#A8A29E) — neutral / inactive series

**Theme-aware chart rendering:**
- All Recharts `stroke`, `fill`, and `contentStyle` props must use **resolved CSS variable values** — never CSS variable strings (they don't resolve in JS inline styles)
- Use the `useChartColors()` hook (`/src/shared/hooks/useChartColors.ts`) to get live-resolved values that update on theme toggle
- Grid lines: resolved `--border-default`, `1px`, dashed
- Tick labels: resolved `--text-secondary`
- Tooltip: `background: resolved --surface-card`, `border: 1px solid resolved --border-default`
- No 3D charts ever
- No pie charts for more than 5 segments (use bar chart instead)
- Area charts: fill opacity `0.08`

**Required charts for portal:**

| Page | Chart Type | Data |
|------|-----------|------|
| Dashboard | KPI Stat Cards (4-up) | Vendors, GPS %, Tag %, Coverage |
| Dashboard | Choropleth Map | Vendor density per area |
| Analytics | Line Chart | Vendor acquisition over time |
| Analytics | Horizontal Bar | Coverage per area vs. 500 target |
| Import Center | Progress Bar | Real-time batch import |
| QA Center | Progress Bar | Tag accuracy vs. 95% target |

---

## A11 — Accessibility (WCAG 2.1 AA — Mandatory)

**Contrast ratios:**
- Normal text (≤18px): **4.5:1 minimum**
- Large text / UI components: **3:1 minimum**
- `--text-secondary` (#A8A29E) on `--surface-card` (#1C1C1C) = 4.6:1 ✓ passes AA
- `--brand-orange` (#F97316) on `--brand-black` (#0A0A0A) = 4.5:1 ✓ passes AA
- `--brand-teal` (#0D9488) on `--surface-card` (#1C1C1C) = 3.2:1 — **large text and icons only**

**Keyboard navigation:**
- All interactive elements reachable via Tab
- Logical focus order (top-left to bottom-right)
- Visible focus ring: `2px solid --brand-orange` on ALL elements
- First focusable element: skip-to-content link
- Modal focus trap (Tab cycles within open modal)
- ESC closes modals and drawers

**Screen readers:**
- Data tables: `<th scope="col/row">`, `<caption>`, `aria-sort`
- Status badges: `aria-label="Status: Approved"` (not just color)
- Form errors: `aria-describedby` linking input to error message
- Dynamic content: `aria-live="polite"` for toasts and status updates
- Icons paired with text: `aria-hidden="true"` on the icon

**Touch targets:**
- Minimum **44×44px** for all interactive elements
- 8px minimum spacing between adjacent touch targets

---

## A12 — Responsive Behavior

| Breakpoint | Behavior |
|-----------|---------|
| `1280px+` | Full sidebar + 3-column KPI grid |
| `1024px` | Full sidebar + 2-column KPI grid |
| `768px` | Sidebar collapses to icon rail |
| `375px` | Hamburger menu, single column |

Tables at <1024px: horizontal scroll, sticky first column, reduce row padding to `--space-3`.

---

## A13 — Loading & Empty States

**Skeleton screens (preferred over spinners):**
```tsx
<TableSkeleton rows={10} columns={7} />   // Shimmer bars matching real layout
<StatCardSkeleton />                       // 4 cards, shimmer
<MapSkeleton />                            // Grey rectangle, same aspect ratio
```

**Loading priority (perceived performance):**
1. Page chrome renders immediately (sidebar, header)
2. Skeleton appears for content areas
3. Critical data loads first (KPI numbers)
4. Secondary data loads progressively

**Toast notifications:**
```tsx
toast.success("Vendor approved")           // green, auto-dismiss 4s
toast.error("GPS validation failed")       // red, 6s, manual dismiss
toast.warning("Duplicate detected")        // orange, 6s, with action
toast.info("Import batch queued")          // blue, auto-dismiss 4s
```

Position: **top-right**. Stack up to 3 visible (FIFO). Slide in from right, fade on dismiss. Each variant has a `4px solid` left border in the brand color (`--brand-teal` success/info, `--brand-orange` warning, `--brand-crimson` error). Background: `--surface-card`.

---

## A14 — Writing Style

**Rules:**
- **Sentence case** for everything (not Title Case)
- Address the user directly: `"Your import completed"` not `"Import completed"`
- Be specific in errors — no error codes
- Confirmation messages: past tense `"Vendor approved"` not `"Vendor has been approved"`
- Button labels: verb + noun — never `"OK"` or `"Submit"`

| ✕ Don't | ✓ Do |
|---------|------|
| `"Error 422: Unprocessable Entity"` | `"GPS accuracy must be 10m or less"` |
| `"Operation completed successfully"` | `"Vendor approved"` |
| `"No records found"` | `"No vendors match your filters"` |
| `"Are you sure? This cannot be undone"` | `"Remove this vendor? This will archive their data."` |
| `"Submit"` / `"OK"` | `"Save vendor"` / `"Approve"` / `"Import CSV"` |

---

## AirAd — AR Visibility Scoring Formula

```
Final AR Score =
  (Intent Match      × 0.30) +
  (Distance Weight   × 0.25) +
  (Active Promotion  × 0.15) +
  (Engagement Score  × 0.15) +
  (Subscription Mult × 0.15)
```

**Subscription multipliers:**

| Tier | Price | Multiplier |
|------|-------|-----------|
| Silver | Free | 1.0× |
| Gold | PKR 3,000/mo | 1.2× |
| Diamond | PKR 7,000/mo | 1.5× |
| Platinum | PKR 15,000/mo | 2.0× |

> Paid tier cannot override distance relevance by more than 30%.

---

## AirAd — 5-Layer Tag System

| Layer | Type | Set By | Examples |
|-------|------|--------|---------|
| **Layer 1** | Category — *What the vendor IS* | Vendor (max 3) | Food, Pizza, Cafe, BBQ, Salon |
| **Layer 2** | Intent — *Why users search* | Vendor | Cheap, BudgetUnder300, Halal, Quick |
| **Layer 3** | Promotion — *Time-bound campaigns* | Auto-generated | DiscountLive, HappyHour, FlashDeal |
| **Layer 4** | Time Context — *Clock-based* | Auto-generated | OpenNow, Lunch, Dinner, LateNightOpen |
| **Layer 5** | System — *Invisible to users* | Platform only | ClaimedVendor, ARPriority, HighEngagement |

---

## Portal Pages

| Page | Route | Primary Role |
|------|-------|-------------|
| Dashboard | `/` | Platform health, KPIs, alerts, coverage map |
| Vendor Management | `/vendors` | Full data table, bulk actions, filters |
| Vendor Detail | `/vendors/:id` | GPS map, tags, photos, QC decision |
| Geographic Management | `/geo` | Country / City / Area / Landmark CRUD |
| Tag Management | `/tags` | All 5 layers, usage counts, add/deprecate |
| Import Center | `/import` | CSV drag-drop, Google Places, batch history |
| Field Operations | `/field` | Assignment map, visit log, photo review |
| QA Center | `/qa` | GPS queue, duplicates, tag audit, drift |
| Analytics | `/analytics` | KPI charts, trends, source breakdown |
| Admin & Audit | `/admin` | User management, audit log (SUPER_ADMIN) |

---

## Phase-1 KPI Targets

| Metric | Target |
|--------|--------|
| Vendors per launch area | 500+ minimum |
| GPS accuracy ≤10m | 95% of listings |
| Tag accuracy | 95% minimum |
| Voice bot intent accuracy | 85% minimum |
| AR marker render time | <2 seconds |
| Vendor claim rate (Month 1) | 15% minimum |
| Platform uptime | 99.5% |
| API response time (p95) | <200ms |

---

*AirAd Phase-1 — DLS Reference v2.0 · Brand Elevation Update · Authority: AirAd Brand Identity + Airbnb Design Language System A1–A14*
