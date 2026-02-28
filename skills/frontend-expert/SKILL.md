---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beautifying any web UI). Generates creative, polished code and UI design that avoids generic AI aesthetics.
license: Complete terms in LICENSE.txt
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

**PROJECT CONSTRAINT — AirAd**: This project uses the **Airbnb Design Language System (DLS)** as defined in `airaad-design-system.md` (sections A1–A14). All typography, color tokens, spacing, and base components MUST conform to AirAd DLS. Do not override or bypass DLS primitives. Creative expression lives in layout, composition, motion, and how DLS components are assembled — not in replacing them.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about the purpose, audience, or technical constraints.

## Design Thinking

Before coding, understand the context and commit to a BOLD aesthetic direction:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. There are so many flavors to choose from. Use these for inspiration but design one that is true to the aesthetic direction — within DLS constraints.
- **Constraints**: Technical requirements (framework, performance, accessibility). For AirAd: React 18 + TypeScript 5 + Vite + AirAd DLS (A1–A14). DLS constraints are NON-NEGOTIABLE. Portal has 10 pages: Dashboard `/`, Vendor Management `/vendors`, Vendor Detail `/vendors/:id`, Geographic Management `/geo`, Tag Management `/tags`, Import Center `/import`, Field Operations `/field`, QA Center `/qa`, Analytics `/analytics`, Admin & Audit `/admin`.
- **Differentiation**: What makes this UNFORGETTABLE within the design system? Great layout, motion, and composition can be just as distinctive as custom visuals.

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work - the key is intentionality, not intensity.

Then implement working code (React + TypeScript) that is:
- Production-grade and functional
- Visually striking and memorable within DLS boundaries
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Design System Constraints (AirAd — MANDATORY)

These rules override any general aesthetic guidance below. All tokens are CSS custom properties defined in `airaad-design-system.md`.

- **Typography**: Use ONLY AirAd type tokens (`--text-display`, `--text-heading-xl/lg/md/sm`, `--text-body-lg/md/sm`, `--text-label`, `--text-caption`). Font family: `--font-family-base` (Circular / DM Sans). Do NOT import external fonts or override font-family. Minimum font size: `11px`. Max 3 font weights per view. Sentence case everywhere.
- **Color**: Use ONLY AirAd color tokens — brand (`--color-rausch`, `--color-babu`, `--color-arches`, `--color-hof`, `--color-foggy`), neutrals (`--color-grey-100` through `--color-grey-900`), semantic (`--color-success`, `--color-warning`, `--color-error`, `--color-info` and their `-light` variants), accent (`--color-airaad-accent` — data viz only). Do NOT hardcode hex/rgb values. `--color-rausch` is primary CTA — **maximum 1 per view**. Page backgrounds use `--color-grey-100`.
- **Components**: Build all UI using AirAd DLS component specs (A5.1–A5.8): Buttons, Form Inputs, Cards, Data Tables, Status Badges, Modals/Drawers, Sidebar Navigation, Empty States. Do NOT replace with MUI, Shadcn, Radix, or any other library.
- **Spacing & Layout**: Use ONLY AirAd spacing tokens (`--space-1` through `--space-16`, 8px base grid). Sidebar: `240px` fixed. Content max-width: `1280px`. Topbar height: `64px`. Table row height: `56px`. Never use arbitrary pixel values.
- **Icons**: Use `lucide-react` exclusively. Size: `16px` inline, `20px` nav, `24px` standalone, `32px` empty states. Stroke width: `1.5`. Stroke only — never filled icons. Always pair with visible text labels in navigation.
- **Motion**: Use AirAd motion tokens (`--duration-instant/fast/normal/slow`, `--ease-standard/enter/exit`). Always implement `prefers-reduced-motion: reduce`. No bouncing, spinning, or looping animations.
- **Accessibility**: WCAG 2.1 AA mandatory (A11). Contrast: 4.5:1 normal text, 3:1 large/UI. All interactive elements keyboard-reachable. Focus ring: `2px solid --color-rausch`. Modal focus trap. `aria-live="polite"` for dynamic content.

## Frontend Aesthetics Guidelines (within DLS)

Focus creative energy on areas DLS does not lock down:

- **Motion**: Use animations for effects and micro-interactions within AirAd motion tokens (`--duration-instant` 100ms through `--duration-slow` 350ms, `--ease-standard/enter/exit`). Focus on high-impact moments: page load staggered reveals (`fadeUp`: opacity 0→1 + translateY 8px→0, 250ms), scroll-triggered transitions, and hover states that surprise. Always respect `prefers-reduced-motion`.
- **Spatial Composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density. DLS tokens define the unit — you define the arrangement.
- **Backgrounds & Visual Details**: Create atmosphere and depth using AirAd color tokens creatively — layered transparencies, dramatic shadows, gradient meshes built from the defined palette (`--color-rausch`, `--color-babu`, `--color-arches`, `--color-airaad-accent` for data viz). Do not introduce colors outside the token system.
- **Density & Hierarchy**: Use DLS type scale and spacing tokens to create strong visual hierarchy. The difference between a generic and a great DLS implementation is in how intentionally the scale is applied.

NEVER produce cookie-cutter, predictable layouts that look like default component library demos. The goal is a distinctive, memorable interface that happens to be built on DLS — not a DLS showcase.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate layout and motion. Minimalist designs need restraint, precision, and careful attention to spacing and hierarchy. Elegance comes from executing the vision well — within the system.

Remember: Extraordinary work is possible within a design system. Constraints force creativity. Show what can truly be created when committing fully to a distinctive vision inside DLS boundaries.

---

## Technical Implementation Rules

These rules are **non-negotiable** and apply to every file, every PR, every developer — no exceptions.

### React 18 + TypeScript 5

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

### Vite

- Never blindly import barrel files (`index.ts`) — they kill tree-shaking and bloat the bundle.
- Use `React.lazy` + `Suspense` for route-level code splitting.
- Use `import.meta.env` for all environment variables — validate them at app startup, never let a missing env var silently break production.
- Keep `vite.config.ts` clean — separate aliases, plugins, and build options into logical sections.
- Use `vite-plugin-checker` for TypeScript and ESLint checking during dev so errors surface early.

### Zustand

- **One slice per domain** — no god store.
- Keep all actions inside the store definition, never in components.
- Never call `getState()` inside a component — subscribe via selectors only.
- Use `subscribeWithSelector` middleware for fine-grained reactivity.
- Use `immer` middleware for complex nested state updates — no accidental mutations.
- Always memoize selectors for components that re-render frequently.
- **Zustand is not a cache** — never use it for server data. That is TanStack Query's job, full stop.

### TanStack Query

- **Never mix server state and client state** — Zustand owns client state, TanStack Query owns server state.
- Define all query keys as constants or factory functions in a central `queryKeys.ts` — no string literals scattered across the codebase.
- Use `staleTime` aggressively — not everything needs to refetch on every window focus.
- Set `gcTime` (formerly `cacheTime`) thoughtfully based on how long data remains valid.
- Use `queryClient.invalidateQueries` after mutations — never manually update state.
- For optimistic updates, always implement the `onError` rollback — never assume success.
- Use `suspense: true` mode with React 18 Suspense for a cleaner async data flow.
- Never put data fetching logic inside components — always wrap `useQuery` / `useMutation` in custom hooks.

### AirAd DLS (A1–A14)

- **One component library across the entire project — AirAd DLS only.**
- No MUI, no Shadcn, no Radix, no Headless UI, no any other library — anywhere, ever.
- If DLS doesn't have a component you need, build it yourself using AirAd DLS primitives and tokens.
- Treat DLS as a constraint, not a suggestion — never override component internals with hacky CSS.
- Extend through composition, not by patching styles.
- Follow the same API patterns as DLS components (`controlled` vs `uncontrolled`, `size`, `variant` props) when building custom components.
- Keep DLS components at the leaf level — only wrap them in domain components when business logic needs to be injected.
- Token system is the only source of truth: color (`--color-*`), typography (`--text-*`, `--font-family-*`), spacing (`--space-*`), motion (`--duration-*`, `--ease-*`).
- Icons: `lucide-react` only, stroke width `1.5`, never filled.
- Data tables: always show row count, 25 rows default pagination, skeleton rows for loading (not spinners).
- Empty states: illustration + plain-language heading + action CTA — never blank.
- Toasts: `toast.success/error/warning/info` — bottom-right, stack max 3, auto-dismiss 4s (success/info) or 6s (error/warning).

### Theme System

- **Default theme is light** (AirAd portal uses `--color-grey-100` page backgrounds per A2) — the app must never flash an unstyled state on first load.
- Store theme preference in Zustand and persist it to `localStorage`.
- One single `ThemeProvider` at the root level wraps the entire app — theme logic never lives inside individual components.
- Both light and dark themes must be fully implemented and tested — no half-baked light mode.
- All theme values must come from DLS design tokens — never define your own color primitives.
- Use CSS variables under the hood so theme switching is instant with zero re-renders.
- `ThemeProvider` is the only place the theme is set — components only consume tokens, they never decide the theme.

### Inline Styles & Hardcoded Values — These Are Crimes

- **No `style={}` props** anywhere in the codebase — period.
- **No hardcoded colors** — no hex, no `rgb()`, no named colors like `red` or `white` in JSX or CSS.
- **No hardcoded sizes** — no raw `px`, `rem`, or `%` values when a spacing or size token exists.
- **No hardcoded border colors** — always a token.
- **No hardcoded border-radius** — always a token, never `4px` or `8px` written raw.
- Write a custom ESLint rule that flags any `style={}` prop and any raw color or spacing value in JSX if the default rules don't catch it.
- These rules apply to every single file — components, layouts, pages, utilities, everything.
- **A single inline style found in a PR is grounds for immediate rejection.**

### Folder Structure

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

### Code Quality & Enforcement

- ESLint + Prettier + Husky pre-commit hooks are **non-negotiable**.
- Enforce quality at commit time — not at review time.
- No `console.log` in committed code — use a proper logger utility.
- No commented-out code committed to the repo.
- Every PR must have all three async states handled before it merges.
- TypeScript errors are treated as build failures — CI must block merges on type errors.

### Non-Negotiables Summary

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

## Security Governance — @security-architect

This skill operates under the **@security-architect** governance layer. All frontend code must comply with the security policies defined in `/skills/security-architect/SKILL.md` (§1–§10).

### Mandatory Client-Side Security Rules

These rules are inherited from @security-architect and are **non-negotiable**:

1. **Token Storage (§1, §3)** — Never store access tokens in `localStorage`. Use `sessionStorage` (current AirAd pattern) with XSS mitigations, or in-memory only. Clear all tokens on logout.
2. **No PII in Browser Storage (§2, §9)** — Never store RESTRICTED data (phone numbers, PII) in `localStorage` or `sessionStorage`. Fetch on demand, display masked, discard after use.
3. **XSS Prevention (§4)** — Never use `dangerouslySetInnerHTML` without explicit sanitization. React's JSX escaping handles most cases — do not bypass it.
4. **CSRF Protection (§4)** — Ensure CSRF tokens are included in all state-changing requests to the backend.
5. **PII Display (§9)** — Display personal data masked by default (`*********4567`). Decrypt/unmask only on explicit user action with audit trail.
6. **Content Security Policy (§4)** — Enforce CSP headers. No inline scripts. No `eval()`.
7. **Error Handling (§4)** — Never display raw API error details, stack traces, or internal paths to users. Show user-friendly messages.

### Enforcement

If generated frontend code violates any @security-architect policy:
- **CRITICAL violations** (§1, §2, §3): Block — must fix before merge.
- **HIGH violations** (§4, §9): Warn — should fix before merge.

Refer to `/skills/security-architect/AGENTS.md` for detailed rules and examples.
