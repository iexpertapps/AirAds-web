# Expert-Level Development Rules
## Stack: React 18 + TypeScript 5 | Vite | Zustand | TanStack Query | AirAd DLS (A1–A14)

> All token references below are CSS custom properties defined in `airaad-design-system.md`. Never hardcode values.

---

## 1. React 18 + TypeScript 5

- Always use functional components — no class components, ever.
- `strict: true` in `tsconfig.json` with zero exceptions carved out.
- **No `any`** — use `unknown` and narrow it down properly.
- Use discriminated unions for props that have conditional logic.
- Always type `useRef` explicitly: `useRef<HTMLDivElement>(null)`, never `useRef(null)`.
- Co-locate types with the feature they belong to — no global `types.ts` dumping ground.
- Use `useTransition` and `useDeferredValue` for non-urgent UI updates.
- Use the `use()` hook for promise unwrapping inside Suspense boundaries.
- Zero logic inside JSX — extract everything to hooks or utils before it touches the render.
- Every async operation must handle all three states: **loading**, **error**, and **success** — no exceptions.

---

## 2. Vite

- Never blindly import barrel files (`index.ts`) — they kill tree-shaking and bloat the bundle.
- Use `React.lazy` + `Suspense` for route-level code splitting.
- Use `import.meta.env` for all environment variables — validate them at app startup, never let a missing env var silently break production.
- Keep `vite.config.ts` clean — separate aliases, plugins, and build options into logical sections.
- Use `vite-plugin-checker` for TypeScript and ESLint checking during dev so errors surface early.

---

## 3. Zustand

- **One slice per domain** — no god store.
- Keep all actions inside the store definition, never in components.
- Never call `getState()` inside a component — subscribe via selectors only.
- Use `subscribeWithSelector` middleware for fine-grained reactivity.
- Use `immer` middleware for complex nested state updates — no accidental mutations.
- Always memoize selectors for components that re-render frequently.
- **Zustand is not a cache** — never use it for server data. That is TanStack Query's job, full stop.

---

## 4. TanStack Query

- **Never mix server state and client state** — Zustand owns client state, TanStack Query owns server state.
- Define all query keys as constants or factory functions in a central `queryKeys.ts` — no string literals scattered across the codebase.
- Use `staleTime` aggressively — not everything needs to refetch on every window focus.
- Set `gcTime` (formerly `cacheTime`) thoughtfully based on how long data remains valid.
- Use `queryClient.invalidateQueries` after mutations — never manually update state.
- For optimistic updates, always implement the `onError` rollback — never assume success.
- Use `suspense: true` mode with React 18 Suspense for a cleaner async data flow.
- Never put data fetching logic inside components — always wrap `useQuery` / `useMutation` in custom hooks.

---

## 5. AirAd DLS (A1–A14)

- **One component library across the entire project — AirAd DLS only.**
- No MUI, no Shadcn, no Radix, no Headless UI, no any other library — anywhere, ever.
- If DLS doesn't have a component you need, build it yourself using AirAd DLS primitives and tokens.
- Treat DLS as a constraint, not a suggestion — never override component internals with hacky CSS.
- Extend through composition, not by patching styles.
- Follow the same API patterns as DLS components (`controlled` vs `uncontrolled`, `size`, `variant` props) when building custom components.
- Keep DLS components at the leaf level — only wrap them in domain components when business logic needs to be injected.
- Token system is the only source of truth — never hardcode values:
  - **Brand primitives**: `--brand-orange` (#F97316, primary CTA/active, max 1 dominant use/view), `--brand-crimson` (#DC2626, destructive/error), `--brand-teal` (#0D9488, success/approved), `--brand-black` (#0A0A0A, sidebar/logo bg — never change)
  - **Brand gradients**: `--gradient-brand-text` ("AirAd" wordmark only), `--gradient-primary-btn` (primary button bg), `--gradient-active-indicator` (sidebar active strip), `--gradient-hero` (page hero bg)
  - **Surfaces**: `--surface-page`, `--surface-sidebar`, `--surface-topbar`, `--surface-card`, `--surface-modal`, `--surface-input`, `--surface-hover` — all theme-aware via `[data-theme]`
  - **Text**: `--text-primary`, `--text-secondary` — never hardcode text colors
  - **Borders**: `--border-default`, `--border-input` — never hardcode border colors
  - **Semantic**: `--color-success/warning/error/info` + `-bg` / `-text` variants (all mapped to brand colors)
  - **Neutrals**: `--color-grey-100` through `--color-grey-900` (warm stone scale)
  - **Typography**: `--text-display` (32px/700) through `--text-caption` (11px/400); `--font-family-base` (Circular/DM Sans); min size 11px; sentence case; max 3 weights/view
  - **Spacing**: `--space-1` (4px) through `--space-16` (64px); 8px base grid; never arbitrary px values
  - **Layout**: sidebar `240px` fixed (collapsed `64px`), content max-width `1280px`, topbar `64px`, table row `56px`, card padding `24px`
  - **Motion**: `--duration-instant` (100ms) / `--duration-fast` (150ms) / `--duration-normal` (250ms) / `--duration-slow` (350ms); `--ease-standard/enter/exit`; always respect `prefers-reduced-motion`
- **Icons**: `lucide-react` exclusively — stroke width `1.5`, never filled, sizes: `16px` inline / `20px` nav / `24px` standalone / `32px` empty states
- **Components (A5.1–A5.8)**:
  - Buttons: border-radius `8px`, min-height `48px` primary / `40px` secondary, verb+noun labels, max 1 primary/view; primary uses `--gradient-primary-btn` + orange glow shadow
  - Inputs: height `40px`, `background: --surface-input`, `border: 1px --border-input`, focus ring `--brand-orange`, validate on blur only, error below input
  - Cards: `background: --surface-card`, `border-radius: 12px`, `border: 1px --border-default`, `box-shadow: --shadow-card`
  - Tables: skeleton rows for loading (not spinners), always show row count, 25 rows default, sticky header >10 rows; selected row uses `--brand-orange` left border
  - Badges: pill shape (`border-radius: 100px`), always icon/dot prefix + text, never color alone; use brand color `rgba()` backgrounds
  - Modals: overlay `rgba(0,0,0,0.65)` + `backdrop-filter: blur(4px)`, `background: --surface-modal`, focus trap, ESC closes
  - Sidebar: `240px`, `background: --surface-sidebar` (dark = `--brand-black`), nav item height `44px`, active state uses `--brand-orange` text + `--gradient-active-indicator` left strip
  - Empty states: illustration + plain-language heading + action CTA — never blank
- **Charts (A10 — Recharts)**: CSS variable strings do **not** resolve in JS inline style objects — always use the `useChartColors()` hook (`/src/shared/hooks/useChartColors.ts`) to get live computed values for `stroke`, `fill`, and `contentStyle` props
- **Accessibility (A11 — WCAG 2.1 AA mandatory)**: contrast 4.5:1 normal text / 3:1 large, focus ring `2px solid --brand-orange`, `aria-live="polite"` for toasts, `aria-describedby` for form errors, `aria-hidden="true"` on decorative icons
- **Portal pages**: Dashboard `/`, Vendor Management `/vendors`, Vendor Detail `/vendors/:id`, Geographic Management `/geo`, Tag Management `/tags`, Import Center `/import`, Field Operations `/field`, QA Center `/qa`, Analytics `/analytics`, Admin & Audit `/admin`

---

## 6. Theme System

- **Default theme is dark** — the AirAd portal is dark-first. The `index.html` must set `data-theme="dark"` immediately (before React hydrates) via an inline script to prevent flash.
- Store theme preference in Zustand (`useUIStore`) and persist it to `localStorage` under the key `'airad-theme'`.
- `ThemeProvider` reads from Zustand and sets `document.documentElement.setAttribute('data-theme', theme)` — this is the only place the theme attribute is written.
- One single `ThemeProvider` at the root level wraps the entire app — theme logic never lives inside individual components.
- Both dark and light themes must be fully implemented — no half-baked light mode.
- All theme values must come from DLS surface/text/border tokens — never define your own color primitives.
- Use CSS variables under the hood so theme switching is instant with zero re-renders.
- `ThemeProvider` is the only place the theme is set — components only consume tokens, they never decide the theme.
- The TopBar exposes a Sun/Moon toggle button that calls `toggleTheme()` from `useUIStore`.

---

## 7. Inline Styles & Hardcoded Values — These Are Crimes

- **No `style={}` props** anywhere in the codebase — period.
- **No hardcoded colors** — no hex, no `rgb()`, no named colors like `red` or `white` in JSX or CSS.
- **No hardcoded sizes** — no raw `px`, `rem`, or `%` values when a spacing or size token exists.
- **No hardcoded border colors** — always a token.
- **No hardcoded border-radius** — always a token, never `4px` or `8px` written raw.
- Write a custom ESLint rule that flags any `style={}` prop and any raw color or spacing value in JSX if the default rules don't catch it.
- These rules apply to every single file — components, layouts, pages, utilities, everything.
- **A single inline style found in a PR is grounds for immediate rejection.**

---

## 8. Folder Structure

```
src/
├── features/              # Feature-based folders (auth, dashboard, etc.)
│   └── [feature]/
│       ├── components/    # UI components for this feature
│       ├── hooks/         # Custom hooks for this feature
│       ├── store/         # Zustand slice for this feature
│       ├── queries/       # TanStack Query hooks for this feature
│       ├── types/         # Types scoped to this feature
│       └── utils/         # Utilities scoped to this feature
├── shared/                # Truly shared components, hooks, utils
├── lib/                   # Third-party lib configurations
├── theme/                 # ThemeProvider, tokens, theme config
├── queryKeys.ts           # All query key factories in one place
└── main.tsx               # App entry point
```

- **Feature-based, not type-based** — never have a root-level `components/` or `hooks/` folder.
- If something is used in only one feature, it lives inside that feature.
- If something is used in two or more features, it moves to `shared/`.

---

## 9. Code Quality & Enforcement

- ESLint + Prettier + Husky pre-commit hooks are **non-negotiable**.
- Enforce quality at commit time — not at review time.
- No `console.log` in committed code — use a proper logger utility.
- No commented-out code committed to the repo.
- Every PR must have all three async states handled before it merges.
- TypeScript errors are treated as build failures — CI must block merges on type errors.

---

## 10. General Non-Negotiables

| Rule | Status |
|------|--------|
| No `any` type | ❌ Crime |
| Inline `style={}` | ❌ Crime |
| Hardcoded colors / sizes / radius / border | ❌ Crime |
| Multiple component libraries | ❌ Crime |
| Server state in Zustand | ❌ Crime |
| Logic inside JSX | ❌ Crime |
| Missing error/loading state | ❌ Crime |
| String literal query keys | ❌ Crime |
| Theme logic inside components | ❌ Crime |
| Barrel file abuse | ❌ Crime |

---

*These rules apply to every file, every PR, every developer — no exceptions.*
