# Frontend Expert Guidelines — AirAd Platform

**Enforced rules for AI agents writing and reviewing frontend code** for the AirAd Data Collection Portal. These rules are mandatory and apply to every file, every PR, every developer — no exceptions.

Stack: React 18 + TypeScript 5 | Vite | Zustand | TanStack Query | AirAd DLS (A1–A14)

---

## Table of Contents

### Type Safety — **CRITICAL**
1. [No `any` Type](#no-any-type)
2. [Strict TypeScript Configuration](#strict-typescript-configuration)

### Component Architecture — **CRITICAL**
3. [No Logic Inside JSX](#no-logic-inside-jsx)
4. [Handle All Async States](#handle-all-async-states)

### Design System — **CRITICAL**
5. [AirAd DLS Only — No External Libraries](#airad-dls-only--no-external-libraries)
6. [No Inline Styles or Hardcoded Values](#no-inline-styles-or-hardcoded-values)
7. [Token System Compliance](#token-system-compliance)

### State Management — **HIGH**
8. [Zustand for Client State Only](#zustand-for-client-state-only)
9. [TanStack Query for Server State](#tanstack-query-for-server-state)

### Code Organization — **HIGH**
10. [Feature-Based Folder Structure](#feature-based-folder-structure)
11. [Icon & Accessibility Rules](#icon--accessibility-rules)

### Code Quality — **MEDIUM**
12. [Code Quality Enforcement](#code-quality-enforcement)

---

## Type Safety

### No `any` Type

**Impact: CRITICAL** | **Category: type-safety** | **Tags:** typescript, any, unknown, types

The `any` type defeats the purpose of TypeScript. Use `unknown` and narrow it properly.

#### ❌ Incorrect

```typescript
const handleData = (data: any) => {
  return data.name.toUpperCase();
};

const ref = useRef(null);  // Untyped ref

function parseResponse(res: any): any {
  return res.data;
}
```

#### ✅ Correct

```typescript
const handleData = (data: VendorResponse) => {
  return data.name.toUpperCase();
};

const ref = useRef<HTMLDivElement>(null);  // Explicitly typed ref

function parseResponse(res: AxiosResponse<VendorListResponse>): Vendor[] {
  return res.data.results;
}

// When type is truly unknown, narrow it
function handleError(error: unknown): string {
  if (error instanceof AxiosError) return error.response?.data?.detail ?? 'Request failed';
  if (error instanceof Error) return error.message;
  return 'An unknown error occurred';
}
```

**Rules:**
- `any` is a crime — every instance is grounds for PR rejection
- Use `unknown` + type narrowing when the type is genuinely uncertain
- Always type `useRef` explicitly: `useRef<HTMLDivElement>(null)`
- Use discriminated unions for conditional prop patterns
- Co-locate types with the feature — no global `types.ts` dumping ground

---

### Strict TypeScript Configuration

**Impact: CRITICAL** | **Category: type-safety** | **Tags:** tsconfig, strict, compiler

`strict: true` in `tsconfig.json` with zero exceptions. TypeScript errors are build failures.

**Rules:**
- `strict: true` — non-negotiable, no carve-outs
- CI must run `tsc --noEmit` and block merge on errors
- Never use `// @ts-ignore` or `// @ts-expect-error` without a linked issue/TODO
- Never use type assertions (`as`) to silence errors — fix the underlying type instead

---

## Component Architecture

### No Logic Inside JSX

**Impact: CRITICAL** | **Category: architecture** | **Tags:** jsx, hooks, separation

Extract all logic to hooks, variables, or utility functions before it touches the render.

#### ❌ Incorrect

```tsx
return (
  <div>
    {vendors.filter(v => v.status === 'active').map(v => (
      <div key={v.id} onClick={() => {
        setSelected(v.id);
        navigate(`/vendors/${v.id}`);
        trackEvent('vendor_click', { id: v.id });
      }}>
        {v.name} — {v.created_at ? new Date(v.created_at).toLocaleDateString() : 'N/A'}
      </div>
    ))}
  </div>
);
```

#### ✅ Correct

```tsx
const activeVendors = useMemo(
  () => vendors.filter(v => v.status === 'active'),
  [vendors]
);

const handleVendorClick = useCallback((id: string) => {
  setSelected(id);
  navigate(`/vendors/${id}`);
  trackEvent('vendor_click', { id });
}, [setSelected, navigate]);

const formatDate = (date: string | null): string =>
  date ? new Date(date).toLocaleDateString() : 'N/A';

return (
  <div>
    {activeVendors.map(v => (
      <VendorCard key={v.id} vendor={v} onClick={handleVendorClick} />
    ))}
  </div>
);
```

**Rules:**
- No `.filter()`, `.map()` chains with inline logic inside JSX
- No inline event handlers with more than one statement
- No ternary expressions with complex logic — extract to a variable
- No date formatting, string manipulation, or calculations inside JSX

---

### Handle All Async States

**Impact: CRITICAL** | **Category: architecture** | **Tags:** async, loading, error, suspense

Every async operation must handle **loading**, **error**, and **success** — no exceptions.

#### ❌ Incorrect

```tsx
const { data } = useQuery({ queryKey: queryKeys.vendors.list(), queryFn: fetchVendors });
return <VendorTable vendors={data} />;  // Crashes if data is undefined
```

#### ✅ Correct

```tsx
const { data, isLoading, error } = useQuery({
  queryKey: queryKeys.vendors.list(),
  queryFn: fetchVendors,
});

if (isLoading) return <TableSkeleton rows={5} />;
if (error) return <ErrorState title="Failed to load vendors" onRetry={refetch} />;
if (!data?.results.length) return <EmptyState title="No vendors found" action={<AddVendorButton />} />;

return <VendorTable vendors={data.results} />;
```

**Rules:**
- Loading: use skeleton components (DLS pattern), never spinners
- Error: use `ErrorState` component with retry action
- Empty: use `EmptyState` with illustration + heading + CTA (never blank)
- Data tables: skeleton rows during loading, always show row count
- Toasts: `bottom-right`, stack max 3, auto-dismiss 4s (success/info) or 6s (error/warning)

---

## Design System

### AirAd DLS Only — No External Libraries

**Impact: CRITICAL** | **Category: design-system** | **Tags:** dls, components, libraries

One component library across the entire project — AirAd DLS only.

#### ❌ Incorrect — Immediate PR Rejection

```typescript
import { Button } from '@mui/material';
import { Dialog } from '@radix-ui/react-dialog';
import { Switch } from '@headlessui/react';
import { Card } from 'shadcn/ui';
import { FaHome } from 'react-icons/fa';  // Wrong icon library
```

#### ✅ Correct

```typescript
import { Button } from '@/shared/components/dls/Button';
import { Modal } from '@/shared/components/dls/Modal';
import { Table } from '@/shared/components/dls/Table';
import { Card } from '@/shared/components/dls/Card';
import { Home } from 'lucide-react';  // Only allowed icon library
```

**Rules:**
- No MUI, no Shadcn, no Radix, no Headless UI — anywhere, ever
- If DLS doesn't have a component, build it from DLS primitives and tokens
- Extend through composition, not by patching styles
- Icons: `lucide-react` only, stroke width `1.5`, never filled
- Icon sizes: `16px` inline, `20px` nav, `24px` standalone, `32px` empty states
- Always pair icons with visible text labels in navigation

---

### No Inline Styles or Hardcoded Values

**Impact: CRITICAL** | **Category: design-system** | **Tags:** styles, tokens, hardcoded

A single inline style or hardcoded value found in a PR is grounds for immediate rejection.

#### ❌ Incorrect — These Are Crimes

```tsx
// Inline style prop
<Card style={{ padding: '16px', marginTop: '12px' }}>

// Hardcoded color
<span style={{ color: '#F97316' }}>Active</span>
<div className="bg-[#DC2626]">

// Hardcoded spacing
<div className="mt-[13px] p-[7px]">

// Hardcoded border-radius
<div className="rounded-[6px]">

// Hardcoded font size
<p style={{ fontSize: '14px' }}>
```

#### ✅ Correct

```tsx
// DLS spacing tokens
<Card className="p-space-4 mt-space-3">

// DLS color tokens via CSS variables
<span className="text-color-success">Active</span>

// DLS spacing tokens
<div className="mt-space-3 p-space-2">

// DLS border-radius from component specs
<div className="rounded-card">  {/* 12px from DLS card spec */}

// DLS typography tokens
<p className="text-body-md">
```

**Rules:**
- No `style={}` props — period
- No hardcoded hex, rgb(), or named colors — always a token
- No raw px, rem, or % when a spacing/size token exists — always a token
- No hardcoded border-radius — always from DLS component spec
- No hardcoded font-size — always from typography token scale

---

### Token System Compliance

**Impact: CRITICAL** | **Category: design-system** | **Tags:** tokens, css-variables, theme

The token system is the only source of truth for all visual properties.

**Token Categories (all CSS custom properties from `airaad-design-system.md`):**

| Category | Tokens | Rule |
|----------|--------|------|
| **Brand** | `--brand-orange`, `--brand-crimson`, `--brand-teal`, `--brand-black` | `--brand-orange` is primary CTA — max 1 dominant use per view |
| **Surfaces** | `--surface-page/sidebar/topbar/card/modal/input/hover` | Theme-aware via `[data-theme]` — never hardcode bg colors |
| **Text** | `--text-primary`, `--text-secondary` | Never hardcode text colors |
| **Borders** | `--border-default`, `--border-input` | Never hardcode border colors |
| **Semantic** | `--color-success/warning/error/info` + `-bg`/`-text` | Mapped to brand colors |
| **Typography** | `--text-display` through `--text-caption` | Min size 11px, max 3 weights per view, sentence case |
| **Spacing** | `--space-1` (4px) through `--space-16` (64px) | 8px base grid, never arbitrary values |
| **Layout** | Sidebar `240px` / `64px`, content max `1280px`, topbar `64px`, row `56px` | Fixed constants from DLS |
| **Motion** | `--duration-instant/fast/normal/slow`, `--ease-standard/enter/exit` | Always respect `prefers-reduced-motion` |

**Charts (A10 — Recharts):** CSS variable strings do NOT resolve in JS inline style objects. Always use `useChartColors()` hook for live computed values.

---

## State Management

### Zustand for Client State Only

**Impact: HIGH** | **Category: state** | **Tags:** zustand, client-state, store

Zustand owns client/UI state. Never use it as a cache for server data.

#### ❌ Incorrect

```typescript
// Server data in Zustand — this is TanStack Query's job
const useVendorStore = create((set) => ({
  vendors: [],
  fetchVendors: async () => {
    const { data } = await api.get('/vendors/');
    set({ vendors: data });
  },
}));

// getState() inside a component
const theme = useUIStore.getState().theme;
```

#### ✅ Correct

```typescript
// Client/UI state only
const useUIStore = create(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: 'dark' as 'dark' | 'light',
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      toggleTheme: () => set((s) => ({ theme: s.theme === 'dark' ? 'light' : 'dark' })),
    }),
    { name: 'airad-ui' }
  )
);

// Subscribe via selector, never getState()
const theme = useUIStore((s) => s.theme);
```

**Rules:**
- One slice per domain — no god store
- All actions inside the store definition, never in components
- Never `getState()` inside a component — subscribe via selectors only
- Use `immer` middleware for complex nested updates
- Memoize selectors for frequently re-rendering components
- Persist UI preferences to `localStorage`, never server data

---

### TanStack Query for Server State

**Impact: HIGH** | **Category: state** | **Tags:** tanstack-query, server-state, cache

TanStack Query owns all server data. Never mix with Zustand.

#### ❌ Incorrect

```typescript
// String literal query keys scattered in components
useQuery({ queryKey: ['vendors', id], queryFn: () => fetchVendor(id) });

// Data fetching inside a component
const VendorPage = () => {
  const { data } = useQuery({
    queryKey: ['vendor', id],
    queryFn: async () => {
      const res = await apiClient.get(`/vendors/${id}/`);
      return res.data;
    },
  });
};

// Manual state update instead of invalidation
onSuccess: (data) => { setVendors(prev => [...prev, data]); }
```

#### ✅ Correct

```typescript
// Centralized query keys in queryKeys.ts
export const queryKeys = {
  vendors: {
    all: () => ['vendors'] as const,
    list: (params?: VendorListParams) => [...queryKeys.vendors.all(), 'list', params] as const,
    detail: (id: string) => [...queryKeys.vendors.all(), 'detail', id] as const,
  },
};

// Data fetching in custom hook
const useVendor = (id: string) => useQuery({
  queryKey: queryKeys.vendors.detail(id),
  queryFn: () => vendorService.getById(id),
  staleTime: 5 * 60 * 1000,
});

// Invalidation after mutation
const useUpdateVendor = () => useMutation({
  mutationFn: vendorService.update,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.vendors.all() });
  },
  onError: (err, variables, context) => {
    // Rollback optimistic update
  },
});
```

**Rules:**
- All query keys in `queryKeys.ts` — no string literals anywhere
- Use `staleTime` aggressively — not everything refetches on window focus
- `queryClient.invalidateQueries` after mutations — never manual state updates
- For optimistic updates, always implement `onError` rollback
- Wrap `useQuery`/`useMutation` in custom hooks — never inside components directly

---

## Code Organization

### Feature-Based Folder Structure

**Impact: HIGH** | **Category: organization** | **Tags:** folders, structure, colocation

```
src/
├── features/              # Feature-based folders
│   └── [feature]/
│       ├── components/    # UI components for this feature
│       ├── hooks/         # Custom hooks for this feature
│       ├── store/         # Zustand slice for this feature
│       ├── queries/       # TanStack Query hooks for this feature
│       ├── types/         # Types scoped to this feature
│       └── utils/         # Utilities scoped to this feature
├── shared/                # Components, hooks, utils used by 2+ features
├── lib/                   # Third-party lib configurations
├── theme/                 # ThemeProvider, tokens, theme config
├── queryKeys.ts           # All query key factories
└── main.tsx               # App entry point
```

**Rules:**
- Feature-based, not type-based — never a root-level `components/` or `hooks/` folder
- Single-feature items stay in that feature's folder
- Used in 2+ features → moves to `shared/`
- Never blindly import barrel files (`index.ts`) — kills tree-shaking

---

### Icon & Accessibility Rules

**Impact: HIGH** | **Category: accessibility** | **Tags:** icons, wcag, a11y, lucide

#### Icons

- `lucide-react` exclusively — no other icon library
- Stroke width: `1.5` — never filled
- Sizes: `16px` inline, `20px` nav, `24px` standalone, `32px` empty states
- Always pair with visible text labels in navigation

#### Accessibility (WCAG 2.1 AA — Mandatory)

- Contrast: 4.5:1 normal text, 3:1 large text and UI components
- Focus ring: `2px solid var(--brand-orange)`
- `aria-live="polite"` for toasts and dynamic content
- `aria-describedby` for form error messages
- `aria-hidden="true"` on decorative icons
- Modal focus trap — Tab cycles within modal, ESC closes
- All interactive elements keyboard-reachable (Tab/Enter/Escape)
- Always respect `prefers-reduced-motion: reduce`

---

## Code Quality

### Code Quality Enforcement

**Impact: MEDIUM** | **Category: quality** | **Tags:** eslint, prettier, husky, ci

**Rules:**
- ESLint + Prettier + Husky pre-commit hooks — non-negotiable
- Enforce at commit time, not review time
- No `console.log` in committed code — use logger utility
- No commented-out code in the repo
- TypeScript errors are build failures — CI blocks merge on type errors
- Every PR: all three async states handled before merge

---

## Theme System Rules

- **Default theme: dark** — `index.html` sets `data-theme="dark"` before React hydrates (no flash)
- Theme stored in Zustand (`useUIStore`), persisted to `localStorage` key `'airad-theme'`
- `ThemeProvider` at root: reads Zustand, sets `document.documentElement.setAttribute('data-theme', theme)`
- Both dark and light themes fully implemented — no half-baked light mode
- All theme values from DLS surface/text/border tokens — never custom primitives
- CSS variables for instant theme switch with zero re-renders
- TopBar exposes Sun/Moon toggle → calls `toggleTheme()` from `useUIStore`

---

## Non-Negotiables Summary

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
| `dangerouslySetInnerHTML` with user content | ❌ Crime |
| PII in localStorage/sessionStorage | ❌ Crime |

---

## Security Governance — @security-architect

This skill operates under the **@security-architect** governance layer. All frontend code must comply with `/skills/security-architect/SKILL.md` (§1–§10).

### Mandatory Client-Side Security Rules

1. **Token Storage (§1, §3)** — Never store access tokens in `localStorage`. Use `sessionStorage` with XSS mitigations, or in-memory only. Clear all tokens on logout.
2. **No PII in Browser Storage (§2, §9)** — Never store RESTRICTED data (phone numbers, PII) in `localStorage` or `sessionStorage`. Fetch on demand, display masked, discard after use.
3. **XSS Prevention (§4)** — Never use `dangerouslySetInnerHTML` without explicit sanitization. React's JSX escaping handles most cases.
4. **CSRF Protection (§4)** — Include CSRF tokens in all state-changing requests.
5. **PII Display (§9)** — Display personal data masked by default (`*********4567`). Decrypt/unmask only on explicit user action with audit trail.
6. **Content Security Policy (§4)** — No inline scripts, no `eval()`.
7. **Error Handling (§4)** — Never display raw API error details to users. Show user-friendly messages.

### Enforcement

- **CRITICAL violations** (§1, §2, §3): Block — must fix before merge.
- **HIGH violations** (§4, §9): Warn — should fix before merge.

---

## References

- [SKILL.md](SKILL.md) — Design thinking, DLS constraints, technical rules
- [expert-rules.md](expert-rules.md) — Detailed token reference and component specs
- [airaad-design-system.md](airaad-design-system.md) — Full AirAd DLS specification (A1–A14)
- [@security-architect Governance](/skills/security-architect/SKILL.md) — Security policies (§1–§10)
- [@security-architect Enforcement](/skills/security-architect/AGENTS.md) — Enforced security rules
