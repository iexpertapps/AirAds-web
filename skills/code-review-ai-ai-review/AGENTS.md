# AI Code Review Guidelines — AirAd Platform

**Enforced rules for AI agents performing code reviews** on the AirAd platform. These rules govern how reviews are conducted, what must be checked, and how findings are reported.

Stack: Django 5.x + DRF (backend) | React 18 + TypeScript 5 + Vite (frontend) | GitHub Actions CI/CD

---

## Table of Contents

### Review Process — **CRITICAL**
1. [Security-First Review](#security-first-review)
2. [Severity Classification](#severity-classification)
3. [Quality Gate Enforcement](#quality-gate-enforcement)

### Backend Checks — **HIGH**
4. [Django & DRF Patterns](#django--drf-patterns)
5. [Database & ORM Safety](#database--orm-safety)

### Frontend Checks — **HIGH**
6. [React & TypeScript Patterns](#react--typescript-patterns)
7. [State Management Rules](#state-management-rules)

### Cross-Cutting — **HIGH**
8. [AirAd DLS Compliance](#airad-dls-compliance)
9. [Testing & Coverage](#testing--coverage)

### Reporting — **MEDIUM**
10. [Review Output Format](#review-output-format)

---

## Review Process

### Security-First Review

**Impact: CRITICAL** | **Category: process** | **Tags:** security, governance, compliance

Every code review must validate security compliance against @security-architect policies (§1–§10) before any other checks. Security violations take priority over style, performance, or architecture issues.

#### Mandatory Security Checklist (every PR)

- [ ] No hardcoded secrets or credentials (§6)
- [ ] No weak password hashing or custom crypto (§1, §3)
- [ ] RESTRICTED data encrypted at rest, masked in display/logs (§2, §3)
- [ ] No raw string-formatted SQL (§4)
- [ ] No PII in logs or error responses (§5, §9)
- [ ] Input validation on all user-facing inputs (§4)
- [ ] Explicit permission checks on new/modified endpoints (§1, §7)
- [ ] Audit logging for data mutations (§5)
- [ ] Error responses do not leak internals (§4)
- [ ] Dependencies free of critical CVEs (§8)

#### Security-Sensitive Change Triggers

These changes require **elevated scrutiny** — review every line:
- Authentication or authorization logic
- Encryption, hashing, or key management
- New API endpoints accepting user input
- CORS, CSP, or security header changes
- New data models storing PII or RESTRICTED data
- Deployment config or secret management changes
- New third-party service integrations
- User role or permission matrix changes

Refer to `/skills/security-architect/AGENTS.md` for detailed security enforcement rules and examples.

---

### Severity Classification

**Impact: CRITICAL** | **Category: process** | **Tags:** severity, triage, classification

Every finding must be classified with a severity level. Never leave findings unclassified.

#### Severity Definitions

| Severity | Description | Examples | Action |
|----------|-------------|----------|--------|
| **CRITICAL** | Security vulnerability, data loss, or crash | SQL injection, hardcoded secrets, unhandled null dereference, missing auth check | **Block merge** — must fix |
| **HIGH** | Correctness risk, significant maintainability issue | Missing error handling, N+1 query, race condition, missing input validation | **Block merge** — should fix |
| **MEDIUM** | Code quality, readability, minor performance | Missing type hints, poor naming, unnecessary re-renders, missing docs | **Warn** — fix or justify |
| **LOW** | Stylistic preference, minor improvement | Formatting, import order, variable naming preference | **Suggest** — optional |
| **INFO** | Observation, educational note | Alternative approach, upcoming deprecation, best practice tip | **Comment** — no action required |

#### ❌ Incorrect

```markdown
<!-- Unclassified finding with no severity -->
This function could be improved.
```

#### ✅ Correct

```markdown
**🔴 CRITICAL — SQL Injection (§4)**
**File:** `apps/vendors/views.py:42`
**Issue:** Raw string formatting in SQL query allows injection.
**Fix:** Use Django ORM or parameterized query.
```

---

### Quality Gate Enforcement

**Impact: CRITICAL** | **Category: process** | **Tags:** gates, blocking, merge

Reviews must enforce quality gates that align with CI pipeline gates.

**Rules:**
- **1+ CRITICAL findings** → Review status: `REQUEST_CHANGES`. PR cannot merge.
- **3+ HIGH findings** → Review status: `REQUEST_CHANGES`. Escalate to architectural review.
- **HIGH findings only** → Review status: `REQUEST_CHANGES`. Recommend fixes before merge.
- **MEDIUM/LOW only** → Review status: `COMMENT`. May merge with acknowledged items.
- **No findings** → Review status: `APPROVE`.

#### ❌ Incorrect

```
# Approving a PR with a CRITICAL finding
LGTM! Just a minor SQL issue on line 42, but otherwise looks good. ✅
```

#### ✅ Correct

```
# Blocking a PR with a CRITICAL finding
❌ REQUEST_CHANGES — 1 CRITICAL issue found.

🔴 CRITICAL: SQL injection vulnerability in apps/vendors/views.py:42 (§4)
Must fix before merge. See suggested fix below.
```

---

## Backend Checks

### Django & DRF Patterns

**Impact: HIGH** | **Category: backend** | **Tags:** django, drf, python, api

Check all backend code for Django/DRF-specific anti-patterns.

#### ❌ Incorrect Patterns to Flag

```python
# 1. Missing permission_classes — defaults to AllowAny if not set globally
class VendorView(APIView):
    def get(self, request):
        return Response(Vendor.objects.all().values())

# 2. Using __all__ in serializer fields — exposes unintended fields
class Meta:
    model = Vendor
    fields = "__all__"

# 3. Bare except swallowing errors
try:
    vendor.save()
except:
    pass

# 4. Returning raw exception details
except Exception as e:
    return Response({"error": str(e)}, status=500)

# 5. Missing pagination on list endpoint
class VendorListView(ListAPIView):
    queryset = Vendor.objects.all()
    # No pagination_class — returns unbounded results
```

#### ✅ Correct Patterns

```python
# 1. Explicit permissions
class VendorView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrManager]

# 2. Explicit field list
class Meta:
    model = Vendor
    fields = ["id", "name", "category", "status"]

# 3. Specific exception handling
try:
    vendor.save()
except IntegrityError as e:
    logger.error(f"Vendor save failed: vendor_id={vendor.id}, error={e}")
    return Response({"error": "Failed to save vendor."}, status=400)

# 4. Generic error with correlation ID
except Exception as e:
    correlation_id = str(uuid.uuid4())
    logger.error(f"Internal error [{correlation_id}]: {e}", exc_info=True)
    return Response({"error": "An internal error occurred.", "correlation_id": correlation_id}, status=500)

# 5. Paginated list endpoint
class VendorListView(ListAPIView):
    queryset = Vendor.objects.all()
    pagination_class = StandardPagination  # max 100 per page
```

---

### Database & ORM Safety

**Impact: HIGH** | **Category: backend** | **Tags:** orm, database, queries, n+1

Flag database anti-patterns that cause performance or security issues.

#### ❌ Incorrect

```python
# N+1 query — one query per vendor in the loop
for vendor in Vendor.objects.all():
    print(vendor.area.name)  # Hits DB for each vendor

# Unbounded queryset — no limit
all_vendors = Vendor.objects.all()
return Response(VendorSerializer(all_vendors, many=True).data)

# Raw SQL with string formatting
Vendor.objects.raw(f"SELECT * FROM vendors WHERE name = '{name}'")
```

#### ✅ Correct

```python
# Eager loading with select_related / prefetch_related
for vendor in Vendor.objects.select_related("area").all():
    print(vendor.area.name)  # No additional queries

# Paginated queryset
paginator = StandardPagination()
page = paginator.paginate_queryset(Vendor.objects.all(), request)
return paginator.get_paginated_response(VendorSerializer(page, many=True).data)

# Parameterized raw SQL (if ORM is insufficient)
Vendor.objects.raw("SELECT * FROM vendors WHERE name = %s", [name])
```

**Rules:**
- Flag any queryset access inside a loop (N+1 candidate)
- Flag any list endpoint without pagination
- Flag any `.raw()` or `.extra()` call — verify parameterization
- Flag `select_related` / `prefetch_related` missing on foreign key traversals
- Flag `.all()` without `.filter()` or pagination on large tables

---

## Frontend Checks

### React & TypeScript Patterns

**Impact: HIGH** | **Category: frontend** | **Tags:** react, typescript, hooks

Flag React and TypeScript anti-patterns specific to the AirAd stack.

#### ❌ Incorrect

```typescript
// 1. Using `any` type
const handleData = (data: any) => { ... }

// 2. Logic inside JSX
return <div>{users.filter(u => u.active).map(u => <span>{u.name}</span>)}</div>

// 3. Missing error/loading states
const { data } = useQuery({ queryKey: ['vendors'], queryFn: fetchVendors });
return <VendorList vendors={data} />;  // Crashes if data is undefined

// 4. String literal query keys
useQuery({ queryKey: ['vendors', id], queryFn: () => fetchVendor(id) });

// 5. dangerouslySetInnerHTML without sanitization
<div dangerouslySetInnerHTML={{ __html: userContent }} />
```

#### ✅ Correct

```typescript
// 1. Proper typing
const handleData = (data: VendorResponse) => { ... }

// 2. Logic extracted from JSX
const activeUsers = useMemo(() => users.filter(u => u.active), [users]);
return <div>{activeUsers.map(u => <span key={u.id}>{u.name}</span>)}</div>

// 3. All three async states handled
const { data, isLoading, error } = useQuery({
  queryKey: queryKeys.vendors.list(),
  queryFn: fetchVendors,
});
if (isLoading) return <TableSkeleton />;
if (error) return <ErrorState message="Failed to load vendors" />;
return <VendorList vendors={data} />;

// 4. Centralized query keys
useQuery({ queryKey: queryKeys.vendors.detail(id), queryFn: () => fetchVendor(id) });

// 5. Never use dangerouslySetInnerHTML with user content
<div>{sanitizedContent}</div>
```

**Rules:**
- Flag every `any` type — must use `unknown` and narrow
- Flag logic inside JSX — must extract to hooks or variables
- Flag missing loading/error states on async operations
- Flag string literal query keys — must use `queryKeys` factory
- Flag `dangerouslySetInnerHTML` — CRITICAL if user-supplied content
- Flag `console.log` in committed code — must use logger utility
- Flag class components — must use functional components

---

### State Management Rules

**Impact: HIGH** | **Category: frontend** | **Tags:** zustand, tanstack-query, state

Enforce correct separation of client state (Zustand) and server state (TanStack Query).

#### ❌ Incorrect

```typescript
// Server data stored in Zustand — TanStack Query's job
const useVendorStore = create((set) => ({
  vendors: [],
  fetchVendors: async () => {
    const data = await api.get('/vendors/');
    set({ vendors: data });
  },
}));

// Calling getState() inside a component
const vendors = useVendorStore.getState().vendors;

// Manual state update after mutation instead of invalidation
const updateVendor = async (data) => {
  await api.patch(`/vendors/${data.id}/`, data);
  useVendorStore.setState({ vendors: updatedList }); // Manual update
};
```

#### ✅ Correct

```typescript
// Server state in TanStack Query
const useVendors = () => useQuery({
  queryKey: queryKeys.vendors.list(),
  queryFn: fetchVendors,
  staleTime: 5 * 60 * 1000,
});

// Client state in Zustand (UI state only)
const useUIStore = create((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
}));

// Invalidation after mutation
const useUpdateVendor = () => useMutation({
  mutationFn: (data) => api.patch(`/vendors/${data.id}/`, data),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.vendors.list() }),
});
```

---

## Cross-Cutting

### AirAd DLS Compliance

**Impact: HIGH** | **Category: design-system** | **Tags:** dls, tokens, components, accessibility

All frontend code must comply with the AirAd Design Language System (A1–A14).

#### ❌ Incorrect — Flag Immediately

```typescript
// Hardcoded color — must use token
<div style={{ color: '#F97316' }}>

// Inline style prop — crime
<Card style={{ padding: '16px' }}>

// External component library
import { Button } from '@mui/material';
import { Dialog } from '@radix-ui/react-dialog';

// Hardcoded spacing
<div className="mt-[13px] p-[7px]">

// Filled icon or wrong library
import { FaHome } from 'react-icons/fa';
```

#### ✅ Correct

```typescript
// DLS token via CSS variable
<div className="text-brand-orange">  // maps to var(--brand-orange)

// DLS component with token-based styling
<Card className="p-space-6">  // maps to var(--space-6)

// AirAd DLS components only
import { Button } from '@/shared/components/dls/Button';
import { Modal } from '@/shared/components/dls/Modal';

// DLS spacing tokens
<div className="mt-space-4 p-space-3">

// lucide-react only, stroke width 1.5
import { Home } from 'lucide-react';
<Home size={20} strokeWidth={1.5} />
```

**Rules:**
- Flag any `style={}` prop — **immediate PR rejection**
- Flag any hardcoded hex, rgb, named color, or raw px/rem value
- Flag any import from MUI, Shadcn, Radix, Headless UI, or other component libraries
- Flag any icon library other than `lucide-react`
- Flag filled icons or wrong stroke width (must be `1.5`)
- Flag missing WCAG AA compliance: contrast ratios, keyboard navigation, aria attributes

---

### Testing & Coverage

**Impact: HIGH** | **Category: testing** | **Tags:** pytest, vitest, coverage

Verify that PRs include appropriate test coverage.

**Rules:**
- New API endpoints must have test cases for: success, validation error, permission denied (403), not found (404)
- New utility functions must have unit tests
- Bug fixes must include a regression test
- Coverage must not decrease — CI gate enforces `--cov-fail-under=79`
- Frontend: all three async states tested (loading, error, success)
- Never delete or weaken existing tests without explicit justification

#### ❌ Incorrect

```python
# Test only happy path
def test_create_vendor(self):
    response = self.client.post('/api/v1/vendors/', data)
    assert response.status_code == 201
# Missing: 400, 401, 403 cases
```

#### ✅ Correct

```python
def test_create_vendor_success(self):
    response = self.client.post('/api/v1/vendors/', valid_data)
    assert response.status_code == 201

def test_create_vendor_invalid_data(self):
    response = self.client.post('/api/v1/vendors/', invalid_data)
    assert response.status_code == 400

def test_create_vendor_unauthenticated(self):
    self.client.logout()
    response = self.client.post('/api/v1/vendors/', valid_data)
    assert response.status_code == 401

def test_create_vendor_forbidden(self):
    self.client.force_authenticate(field_agent)
    response = self.client.post('/api/v1/vendors/', valid_data)
    assert response.status_code == 403
```

---

## Reporting

### Review Output Format

**Impact: MEDIUM** | **Category: reporting** | **Tags:** output, format, comments

Structure all review output consistently for readability and actionability.

#### Standard Review Format

```markdown
## 🤖 AI Code Review

**Files reviewed:** 5 | **Findings:** 3

---

## Critical Issues 🔴

### 1. SQL Injection in Vendor Search
**File:** `apps/vendors/views.py:42`
**Policy:** @security-architect §4 (Secure API Design)
**Issue:** Raw string formatting in database query allows SQL injection.
**Impact:** Complete data exfiltration or modification.
**Fix:**
```python
# Use ORM instead of raw SQL
vendors = Vendor.objects.filter(name__icontains=search_term)
```

---

## High Priority 🟠

### 1. N+1 Query in Vendor List
**File:** `apps/vendors/views.py:28`
**Issue:** Foreign key `area` accessed in loop without `select_related`.
**Fix:** Add `.select_related("area")` to queryset.

---

## Medium Priority 🟡

### 1. Missing Type Hint
**File:** `apps/vendors/services.py:15`
**Issue:** Function `get_vendors` missing return type annotation.
**Fix:** Add `-> QuerySet[Vendor]` return type.

---

## Summary
- 🔴 CRITICAL: 1
- 🟠 HIGH: 1
- 🟡 MEDIUM: 1

**Recommendation:** REQUEST_CHANGES — 1 CRITICAL issue must be fixed before merge.
```

**Rules:**
- Always include file path and line number
- Always include severity emoji prefix: 🔴 CRITICAL, 🟠 HIGH, 🟡 MEDIUM, 🔵 LOW, ℹ️ INFO
- Always include a concrete fix with code example for CRITICAL and HIGH findings
- Always reference @security-architect policy number (§1–§10) for security findings
- Always end with a Summary count and overall Recommendation
- Group findings by severity, CRITICAL first

---

## Review Behavior Rules

When performing code reviews on this project:

1. **Security first** — always check @security-architect policies before anything else
2. **Be specific** — include file path, line number, and concrete fix for every finding
3. **Be proportional** — don't block a PR over LOW/INFO findings
4. **No false positives** — if unsure, classify as INFO with a question, not CRITICAL with a demand
5. **Educate** — explain *why* something is wrong, not just *what* is wrong
6. **Acknowledge good patterns** — briefly note well-implemented security, testing, or architecture
7. **Scale review depth** — superficial for >1000 lines changed, deep for <200 lines
8. **Flag scope creep** — if a PR does too many things, recommend splitting before reviewing details

---

## References

- [SKILL.md](SKILL.md) — Full code review toolkit and CI/CD integration
- [resources/implementation-playbook.md](resources/implementation-playbook.md) — Semgrep, TruffleHog, AI review pipeline setup
- [@security-architect Governance](/skills/security-architect/SKILL.md) — Security policies (§1–§10)
- [@security-architect Enforcement](/skills/security-architect/AGENTS.md) — Enforced security rules
