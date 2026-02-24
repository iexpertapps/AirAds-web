# AirAd — Fixation Prompts (Based on PM Implementation Status Report)
### Source: PM Review dated 2026-02-23 | Overall Completion: 72%
### Gaps: 5 Critical | 3 Business Rules | 3 Field Mismatches

---

> **HOW TO USE:**
> - P1 → P5 is execution order — do NOT skip ahead
> - Each fix prompt is self-contained — paste directly to the assigned expert
> - After each fix: PM re-reads those specific files to confirm — no tests needed yet

---

# ══════════════════════════════════════════
# PRIORITY 1 — VENDOR SUB-RESOURCE ENDPOINTS
# Assign to: @python-expert
# Blocks: 4 of 6 tabs on most-used page (VendorDetail) return 404
# ══════════════════════════════════════════

```
You are fixing the AirAd backend.

PM FINDING:
  vendors/urls.py has only 3 routes:
    /vendors/, /vendors/<pk>/, /vendors/<pk>/qc-status/
  VendorDetailPage.tsx calls 6 additional vendor-scoped endpoints that
  do not exist — all return 404 in production.

YOUR JOB:
  Add these 6 missing endpoints to the vendors app.
  Do NOT create new Django apps. Wire into existing apps.

ENDPOINTS TO ADD:

1. GET /api/v1/vendors/<vendor_pk>/photos/
   → Filter field_ops.FieldPhoto by visit__vendor=vendor_pk
   → Return list with presigned S3 URLs (use core.storage.generate_presigned_url())
   → RBAC: all authenticated roles can read

2. GET /api/v1/vendors/<vendor_pk>/visits/
   → Filter field_ops.FieldVisit by vendor=vendor_pk
   → Return list with agent name, visited_at, visit_notes, gps_confirmed_point
   → RBAC: all authenticated roles can read

3. GET /api/v1/vendors/<vendor_pk>/tags/
   → Return vendor.tags.all() with tag_type, tag_name, assigned_at
   → RBAC: all authenticated roles can read

4. POST /api/v1/vendors/<vendor_pk>/tags/
   → Body: { "tag_id": "<uuid>" }
   → Assign tag to vendor (vendor.tags.add(tag))
   → Validate: tag must exist and be is_active=True
   → Create AuditLog entry via log_action()
   → RBAC: DATA_MANAGER, SUPER_ADMIN

5. DELETE /api/v1/vendors/<vendor_pk>/tags/<tag_pk>/
   → Remove tag from vendor (vendor.tags.remove(tag))
   → Create AuditLog entry via log_action()
   → RBAC: DATA_MANAGER, SUPER_ADMIN

6. GET /api/v1/vendors/<vendor_pk>/analytics/
   → Return stub for Phase A:
     { "total_views": 0, "views_this_week": 0, "search_appearances": 0 }
   → (Real analytics is Phase B — stub is acceptable and expected)
   → RBAC: DATA_MANAGER, QC_REVIEWER, SUPER_ADMIN

IMPLEMENTATION RULES:
- Add views to vendors/views.py (not a new file)
- Add URL patterns to vendors/urls.py using nested routing
- Reuse existing serializers where possible — write new ones only if needed
- All mutations call log_action() from audit/utils.py
- Response envelope: { "success": true, "data": {...}, "message": "", "errors": [] }
- No business logic in views — put it in vendors/services.py

ACCEPTANCE: PM will verify vendors/urls.py has all 6 routes and
VendorDetailPage.tsx endpoint calls match exactly.
```

---

# ══════════════════════════════════════════
# PRIORITY 2A — ENFORCE R2: CATEGORY TAG REQUIRED BEFORE APPROVAL
# Assign to: @python-expert
# Blocks: Vendors with zero tags can be approved — bad data reaches production
# ══════════════════════════════════════════

```
You are fixing business rule R2 enforcement in the AirAd backend.

PM FINDING:
  update_qc_status() in vendors/services.py does NOT check for CategoryTag
  before allowing APPROVED status. Any vendor can be approved with zero tags.
  R2 states: vendor must have ≥1 CATEGORY tag before QC approval.

YOUR JOB:
  Add the R2 enforcement gate in vendors/services.py.

EXACT FIX — add this check inside update_qc_status() BEFORE saving:

  if new_status == QCStatus.APPROVED:
      has_category_tag = vendor.tags.filter(
          tag_type=TagType.CATEGORY,
          is_active=True
      ).exists()
      if not has_category_tag:
          raise ValueError(
              "Cannot approve vendor: at least one active CATEGORY tag must "
              "be assigned before approval. Assign a category tag first."
          )

ALSO FIX in QCStatusUpdateSerializer (or the view that catches ValueError):
  Ensure ValueError from the service maps to HTTP 400 with message in the
  standard envelope: { "success": false, "message": "Cannot approve vendor...", "errors": [] }

DO NOT:
- Add this logic to the view
- Add this logic to the serializer validate() method
- Bypass it for SUPER_ADMIN (rule applies to all roles equally)

ACCEPTANCE: PM will read update_qc_status() in vendors/services.py and
confirm the tag count check exists before the status save.
```

---

# ══════════════════════════════════════════
# PRIORITY 2B — ENFORCE R3: REJECTION REQUIRES NON-EMPTY NOTES
# Assign to: @python-expert
# Blocks: QC rejection audit trail can be blank — compliance failure
# ══════════════════════════════════════════

```
You are fixing business rule R3 enforcement in the AirAd backend.

PM FINDING:
  QCStatusUpdateSerializer has qc_notes as required=False, allow_blank=True.
  Frontend validates this but the backend accepts empty rejection notes via
  direct API calls. R3 states: rejection requires a non-empty reason.

YOUR JOB:
  Enforce R3 in QCStatusUpdateSerializer — NOT in the view, NOT in services.py.
  This is input validation, so it belongs in the serializer.

EXACT FIX — add this validate() method to QCStatusUpdateSerializer:

  def validate(self, attrs):
      status = attrs.get('qc_status')
      notes = attrs.get('qc_notes', '').strip()
      if status == QCStatus.REJECTED and not notes:
          raise serializers.ValidationError({
              'qc_notes': 'A rejection reason is required when rejecting a vendor.'
          })
      return attrs

ALSO: change qc_notes field declaration to:
  qc_notes = serializers.CharField(required=False, allow_blank=True, default='')
  (keep allow_blank=True at field level — validation happens at validate() level)

ACCEPTANCE: PM will read QCStatusUpdateSerializer and confirm validate()
method exists with the REJECTED + empty notes check.
```

---

# ══════════════════════════════════════════
# PRIORITY 3A — USER CREATE: ADD TEMP PASSWORD
# Assign to: @python-expert
# Blocks: New users cannot log in — no initial credential delivery
# ══════════════════════════════════════════

```
You are fixing the user creation flow in the AirAd backend.

PM FINDING:
  create_admin_user() service never generates or returns a temp_password.
  Frontend UsersPage.tsx expects CreateUserResponse.data.temp_password and
  shows a copy-to-clipboard modal. Without it, the modal is blank and new
  users have no way to receive initial credentials through the UI.

YOUR JOB:
  Modify create_admin_user() in accounts/services.py to generate and return
  a one-time temporary password.

EXACT FIX in accounts/services.py:

  import secrets
  import string

  def generate_temp_password(length=16):
      alphabet = string.ascii_letters + string.digits + "!@#$%"
      return ''.join(secrets.choice(alphabet) for _ in range(length))

  def create_admin_user(data: dict, actor) -> tuple[AdminUser, str]:
      temp_password = generate_temp_password()
      user = AdminUser(
          email=data['email'],
          full_name=data['full_name'],
          role=data['role'],
      )
      user.set_password(temp_password)
      user.must_change_password = True   # add this flag if not present
      user.save()
      log_action('admin_user.create', actor, user, after=AdminUserSerializer(user).data)
      return user, temp_password   # return BOTH

ALSO FIX the view that calls this service:
  user, temp_password = create_admin_user(data, request.user)
  return Response({
      "success": True,
      "data": {
          **AdminUserSerializer(user).data,
          "temp_password": temp_password   # included ONCE on create only
      },
      "message": "User created. Share this password securely — it will not be shown again.",
      "errors": []
  }, status=201)

IMPORTANT:
- temp_password is returned ONCE in the create response only
- It is NOT stored in the DB in plaintext — only the hash via set_password()
- The GET /users/<id>/ endpoint must NEVER return temp_password
- Add must_change_password BooleanField to AdminUser model if not present
  (default=False, set True on create, set False on first successful login)

ACCEPTANCE: PM will read create_admin_user() service and the create view,
confirm temp_password is generated, set via set_password(), returned in
response, and NOT stored plaintext.
```

---

# ══════════════════════════════════════════
# PRIORITY 3B — FIX FIELD NAME MISMATCHES
# Assign to: @python-expert
# Blocks: Unlock broken (re-locks immediately), failed attempts always shows 0
# ══════════════════════════════════════════

```
You are fixing two field name mismatches between backend and frontend
in the AirAd user management module.

PM FINDINGS (two separate bugs):

BUG 1 — Unlock sends wrong field name:
  Frontend PATCH /api/v1/auth/users/<id>/ sends: { failed_attempts: 0 }
  Backend serializer accepts: failed_login_count (not failed_attempts)
  Result: failed_login_count never resets → account re-locks on next failure

BUG 2 — User list shows wrong field name:
  Frontend reads: user.failed_attempts
  Backend serializer exposes: user.failed_login_count
  Result: Failed Attempts column always shows 0 (undefined)

DECISION: Fix the backend to match the frontend field name.
(Frontend is already deployed and calling the right name — fix the source)

FIX 1 — In AdminUserSerializer:
  Change: failed_login_count = serializers.IntegerField(read_only=True)
  To:     failed_attempts = serializers.IntegerField(
              source='failed_login_count', read_only=True
          )

FIX 2 — In UpdateAdminUserSerializer (used for PATCH):
  Add this field so unlock PATCH works:
  failed_attempts = serializers.IntegerField(
      source='failed_login_count',
      required=False,
      min_value=0
  )

FIX 3 — In the unlock logic (service or view):
  Ensure when failed_attempts=0 is received, failed_login_count is set to 0
  AND locked_until is set to None in the same save():

  def unlock_admin_user(user: AdminUser, actor) -> AdminUser:
      user.failed_login_count = 0
      user.locked_until = None
      user.save(update_fields=['failed_login_count', 'locked_until'])
      log_action('admin_user.unlock', actor, user)
      return user

ALSO: Consider adding a dedicated unlock endpoint for clarity:
  POST /api/v1/auth/users/<id>/unlock/
  → calls unlock_admin_user(), no body needed
  → RBAC: SUPER_ADMIN only
  This is optional but cleaner than PATCH for a boolean action.

ACCEPTANCE: PM will read AdminUserSerializer and UpdateAdminUserSerializer,
confirm failed_attempts field exists with source='failed_login_count',
and confirm unlock service clears both failed_login_count AND locked_until.
```

---

# ══════════════════════════════════════════
# PRIORITY 4 — ENRICH DASHBOARD KPI ENDPOINT
# Assign to: @python-expert
# Blocks: Dashboard is cosmetically present but data-hollow for stakeholders
# ══════════════════════════════════════════

```
You are enriching the platform analytics endpoint in the AirAd backend.

PM FINDING:
  get_platform_kpis() in analytics/services.py returns only 4 scalar fields:
    total_vendors, approved_vendors, pending_vendors, import_batch_count
  Frontend PlatformHealthPage.tsx renders charts and feeds using 12+ fields
  that the backend never provides. All charts render empty.

YOUR JOB:
  Extend get_platform_kpis() to return the fields the frontend already expects.
  These are simple ORM queries — no new models needed.

ADD THESE FIELDS to get_platform_kpis() return dict:

  from django.utils import timezone
  from datetime import timedelta
  from django.db.models import Count
  from django.db.models.functions import TruncDate

  # QC breakdown (for pie chart)
  qc_breakdown = (
      Vendor.active_objects.values('qc_status')
      .annotate(count=Count('id'))
  )
  qc_status_breakdown = {item['qc_status']: item['count'] for item in qc_breakdown}

  # 14-day vendor creation trend (for line chart)
  today = timezone.now().date()
  fourteen_days_ago = today - timedelta(days=13)
  daily_counts = (
      Vendor.active_objects
      .filter(created_at__date__gte=fourteen_days_ago)
      .annotate(day=TruncDate('created_at'))
      .values('day')
      .annotate(count=Count('id'))
      .order_by('day')
  )
  daily_vendor_counts = [
      {"date": str(item['day']), "count": item['count']}
      for item in daily_counts
  ]

  # 7-day import activity (for bar chart)
  seven_days_ago = today - timedelta(days=6)
  import_activity_qs = (
      ImportBatch.objects
      .filter(created_at__date__gte=seven_days_ago)
      .annotate(day=TruncDate('created_at'))
      .values('day')
      .annotate(total=Count('id'))
      .order_by('day')
  )
  import_activity = [
      {"date": str(item['day']), "total": item['total']}
      for item in import_activity_qs
  ]

  # Recent activity feed (last 10 AuditLog entries)
  from audit.models import AuditLog
  recent_logs = AuditLog.objects.order_by('-created_at')[:10]
  recent_activity = [
      {
          "action": log.action,
          "actor": log.actor_label,
          "target_type": log.target_type,
          "created_at": log.created_at.isoformat(),
      }
      for log in recent_logs
  ]

  # Vendors approved today
  vendors_approved_today = Vendor.active_objects.filter(
      qc_status='APPROVED',
      qc_reviewed_at__date=today
  ).count()

RETURN all existing fields PLUS these new ones in the same endpoint response.
Do NOT create a new endpoint — extend the existing one.
Cache the full response in Redis for 5 minutes (already wired if caching exists).

ACCEPTANCE: PM will read get_platform_kpis() and confirm all 5 new data
structures are returned alongside the existing 4 scalar fields.
```

---

# ══════════════════════════════════════════
# PRIORITY 5 — FRONTEND: FIX FIELD NAME READS
# Assign to: @frontend-expert
# Blocks: Failed attempts column always blank in User Management
# Depends on: Priority 3B backend fix must be deployed first
# ══════════════════════════════════════════

```
You are fixing two frontend field name reads in the AirAd React portal.

PM FINDING:
  UsersPage.tsx reads user.failed_attempts from the API response.
  After the backend fix (Priority 3B), the API will now correctly return
  failed_attempts (was failed_login_count). Verify the frontend is reading
  the right field name everywhere.

YOUR JOB:
  Audit UsersPage.tsx for all references to failed_login_count and
  failed_attempts and ensure they use failed_attempts consistently
  (matching the now-fixed backend serializer).

SEARCH FOR in UsersPage.tsx and any related components:
  - failed_login_count  → replace with  failed_attempts
  - is_locked           → confirm this field name matches backend (should be fine)

ALSO VERIFY in the unlock PATCH call:
  Frontend sends: { is_locked: false, failed_attempts: 0 }
  This should now work correctly with the backend fix.
  If the frontend sends { is_locked: false, failed_login_count: 0 } anywhere,
  change it to failed_attempts.

ALSO VERIFY temp_password display:
  After user create, frontend shows copy-to-clipboard modal with
  response.data.temp_password — this will now work since backend returns it.
  Confirm the modal correctly reads data.temp_password (not data.password
  or data.temp_pass or similar).

ACCEPTANCE: PM will verify UsersPage.tsx reads failed_attempts and
temp_password field names, matching the fixed backend serializer output.
```

---

## EXECUTION ORDER SUMMARY

```
┌─────────────────────────────────────────────────────────────────────┐
│  Fix #   │  Who              │  What                    │  Unblocks  │
├─────────────────────────────────────────────────────────────────────┤
│  P1      │  @python-expert   │  6 vendor sub-endpoints  │  4 tabs    │
│  P2A     │  @python-expert   │  R2 enforcement          │  data QC   │
│  P2B     │  @python-expert   │  R3 enforcement          │  compliance│
│  P3A     │  @python-expert   │  Temp password           │  onboarding│
│  P3B     │  @python-expert   │  Field name mismatches   │  unlock    │
│  P4      │  @python-expert   │  Dashboard KPI data      │  demos     │
│  P5      │  @frontend-expert │  Frontend field names    │  UI fixes  │
└─────────────────────────────────────────────────────────────────────┘

P1 + P2A + P2B + P3A + P3B → can all run in parallel (@python-expert)
P4 → after P1-P3 confirmed (avoid merge conflicts in services.py)
P5 → after P3B confirmed deployed (needs backend fix first)

Estimated gap after all fixes: 72% → 95%+
Remaining 5%: discovery/ and subscriptions/ are Phase B stubs — correct.
```

---

*Fixation Prompts v1.0 — derived from PM Implementation Status Report 2026-02-23*
*Authority: AirAd_Master_Super_Prompt_MERGED.md (Unified Edition v3.0)*
*All fixes scoped to Phase A only — Phase B stubs intentionally excluded*
