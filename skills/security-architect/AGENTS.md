# Security Architect Guidelines — AirAd Platform

**Enforced security governance rules for ALL AI agents** operating on the AirAd platform. These rules are mandatory and override any conflicting guidance in downstream skills.

This file is the **authoritative enforcement layer** for policies defined in [SKILL.md](SKILL.md). All engineering skills (@python-expert, @frontend-expert, @senior-devops, @code-review-ai-ai-review, @product-manager) must comply.

---

## Table of Contents

### Authentication & Authorization — **CRITICAL**
1. [Password & Credential Storage](#password--credential-storage)
2. [Token & Session Security](#token--session-security)
3. [Access Control Enforcement](#access-control-enforcement)

### Data Protection — **CRITICAL**
4. [Data Classification Enforcement](#data-classification-enforcement)
5. [Encryption Standards](#encryption-standards)
6. [Secret Management](#secret-management)

### API Security — **HIGH**
7. [Input Validation](#input-validation)
8. [Output & Error Handling](#output--error-handling)
9. [Rate Limiting & CORS](#rate-limiting--cors)

### Logging & Audit — **HIGH**
10. [Audit Logging Requirements](#audit-logging-requirements)
11. [Log Sanitization](#log-sanitization)

### Privacy — **HIGH**
12. [Personal Data Handling](#personal-data-handling)
13. [Data Minimization & Retention](#data-minimization--retention)

### Secure SDLC — **HIGH**
14. [Security Review Triggers](#security-review-triggers)
15. [Dependency & Supply Chain Security](#dependency--supply-chain-security)

---

## Authentication & Authorization

### Password & Credential Storage

**Impact: CRITICAL** | **Category: authentication** | **Tags:** passwords, hashing, credentials

Never store passwords in plaintext or with weak hashing. Use Django's default (Argon2id / PBKDF2) or bcrypt with cost ≥ 12.

#### ❌ Incorrect

```python
# Storing password as plain hash
import hashlib
hashed = hashlib.sha256(password.encode()).hexdigest()
user.password = hashed

# Storing password in plaintext
user.password = request.data["password"]
```

#### ✅ Correct

```python
# Use Django's built-in password hashing (Argon2id by default)
from django.contrib.auth.hashers import make_password
user.password = make_password(request.data["password"])

# Or let Django handle it entirely
user.set_password(request.data["password"])
user.save()
```

**Rules:**
- Never implement custom password hashing — use Django's `make_password` / `set_password`
- Never store, log, or return password values in any form
- Enforce minimum password complexity: 8+ characters, not entirely numeric, not a common password
- Use Django's built-in password validators (`AUTH_PASSWORD_VALIDATORS`)

---

### Token & Session Security

**Impact: CRITICAL** | **Category: authentication** | **Tags:** jwt, sessions, tokens

JWT access tokens must be short-lived. Refresh tokens must be rotated. Sessions must have absolute and idle timeouts.

#### ❌ Incorrect

```python
# Access token valid for 30 days
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
}

# Storing tokens in localStorage
localStorage.setItem("access_token", token);
```

#### ✅ Correct

```python
# Short-lived access token, rotated refresh token
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "SIGNING_KEY": os.environ["DJANGO_SECRET_KEY"],
    "ALGORITHM": "HS256",
}
```

```typescript
// Access token in memory only, refresh via httpOnly cookie when possible
// If sessionStorage is used (current AirAd pattern), clear on logout
const logout = () => {
  sessionStorage.removeItem("accessToken");
  sessionStorage.removeItem("refreshToken");
  sessionStorage.removeItem("user");
};
```

**Rules:**
- Access tokens: ≤ 15 minutes lifetime
- Refresh tokens: ≤ 24 hours, rotated on every use, blacklisted after rotation
- Never store access tokens in localStorage (sessionStorage is acceptable with XSS mitigations)
- Invalidate all tokens on password change
- Admin sessions: idle timeout ≤ 30 minutes

---

### Access Control Enforcement

**Impact: CRITICAL** | **Category: authorization** | **Tags:** rbac, permissions, least-privilege

Every API endpoint must explicitly declare required permissions. Default is deny.

#### ❌ Incorrect

```python
# No permission check — anyone authenticated can access
class VendorDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        Vendor.objects.get(pk=pk).delete()
```

#### ✅ Correct

```python
# Explicit role-based permission check
class VendorDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def delete(self, request, pk):
        vendor = get_object_or_404(Vendor, pk=pk)
        # Audit log before deletion
        AuditLog.objects.create(
            user=request.user,
            action="DELETE",
            resource="Vendor",
            resource_id=str(pk),
        )
        vendor.delete()
        return Response(status=204)
```

**Rules:**
- Every view must have explicit `permission_classes` — never rely on global defaults alone
- Use RBAC roles defined in the application (ADMIN, MANAGER, FIELD_AGENT, etc.)
- Object-level permissions for multi-tenant data (users can only access their own org's data)
- Never expose user enumeration via different error messages for "user not found" vs "wrong password"
- Test permission boundaries: verify that lower-privilege roles receive 403 on restricted endpoints

---

## Data Protection

### Data Classification Enforcement

**Impact: CRITICAL** | **Category: data-protection** | **Tags:** classification, pii, restricted

All data must be handled according to its classification level. RESTRICTED data requires encryption at rest and masking in display.

#### ❌ Incorrect

```python
# Returning raw phone number in API response
return Response({"phone": vendor.phone_number})

# Logging PII
logger.info(f"Processing vendor {vendor.name}, phone: {vendor.phone_number}")
```

#### ✅ Correct

```python
# Phone number masked in API response
from apps.core.utils import mask_phone
return Response({"phone": mask_phone(vendor.phone_number)})  # *********4567

# Logging without PII
logger.info(f"Processing vendor ID={vendor.id}")
```

**Classification Quick Reference:**

| Data | Classification | Required Controls |
|------|---------------|-------------------|
| Passwords, API keys, encryption keys | RESTRICTED | Encrypted, never logged, never in VCS |
| Phone numbers, email + identity | RESTRICTED | Encrypted at rest, masked in display/logs |
| User profiles, vendor business data | CONFIDENTIAL | Access-controlled, encrypted in transit |
| System config, operational logs | INTERNAL | Authenticated access only |
| Public vendor listings | PUBLIC | Integrity protection only |

---

### Encryption Standards

**Impact: CRITICAL** | **Category: encryption** | **Tags:** aes, tls, hsts, crypto

Use approved encryption algorithms only. Never implement custom cryptography.

#### ❌ Incorrect

```python
# Custom encryption — never do this
import base64
encrypted = base64.b64encode(phone_number.encode())

# Weak cipher
from Crypto.Cipher import DES
cipher = DES.new(key, DES.MODE_ECB)
```

#### ✅ Correct

```python
# AES-256-GCM for field-level encryption (as used in AirAd)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

key = bytes.fromhex(os.environ["PHONE_ENCRYPTION_KEY"])  # 32 bytes
nonce = os.urandom(12)
aesgcm = AESGCM(key)
encrypted = aesgcm.encrypt(nonce, plaintext.encode(), None)
```

**Rules:**
- **In transit**: TLS 1.2 minimum, TLS 1.3 preferred. HSTS with `max-age=31536000`.
- **At rest**: AES-256-GCM for field-level encryption. Database-level encryption for full-disk.
- **Hashing**: Argon2id for passwords. SHA-256 minimum for integrity checks. Never MD5 or SHA-1.
- **Keys**: 256-bit minimum for symmetric keys. Store in environment variables only.
- **No custom crypto**: Use established libraries (`cryptography`, `django.contrib.auth.hashers`).

---

### Secret Management

**Impact: CRITICAL** | **Category: secrets** | **Tags:** api-keys, credentials, env-vars

Secrets must never appear in code, logs, error messages, Docker images, or version control.

#### ❌ Incorrect

```python
# Hardcoded secret
API_KEY = "sk-1234567890abcdef"

# Secret in Dockerfile
ENV DJANGO_SECRET_KEY=my-super-secret-key

# Secret in git-tracked config
# config/settings/production.py
SECRET_KEY = "hardcoded-value-here"
```

#### ✅ Correct

```python
import os
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
# Fails fast if not set — never use a default value for secrets
```

**Rules:**
- All secrets in environment variables (Railway, Vercel dashboard, GitHub Secrets)
- TruffleHog in CI catches committed secrets — treat any detection as CRITICAL
- Different secrets per environment (dev ≠ staging ≠ production)
- Rotation procedure: rotate → deploy → verify → revoke old. Never revoke before verifying new secret works.
- If a secret is exposed: rotate immediately, invalidate derived sessions, post-incident review within 48h
- Minimum entropy: 256 bits for encryption keys, 50+ random characters for Django SECRET_KEY

---

## API Security

### Input Validation

**Impact: HIGH** | **Category: api-security** | **Tags:** validation, injection, xss, sqli

Validate all input server-side. Use allowlists. Never trust client-side validation.

#### ❌ Incorrect

```python
# String formatting SQL — SQL injection
query = f"SELECT * FROM vendors WHERE name = '{request.data['name']}'"
cursor.execute(query)

# No validation on user input
vendor.name = request.data.get("name")
vendor.save()
```

#### ✅ Correct

```python
# Parameterized query via ORM
vendors = Vendor.objects.filter(name=validated_data["name"])

# DRF serializer validates all input
class VendorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=200, min_length=1)
    phone = serializers.CharField(validators=[phone_validator])

    class Meta:
        model = Vendor
        fields = ["name", "phone", "category"]
```

**Rules:**
- Always use Django ORM or parameterized queries — never raw string-formatted SQL
- Validate via DRF serializers before any database operation
- Enforce type, length, format, and range constraints on all inputs
- Reject unexpected fields (use serializer `fields` explicitly, never `__all__` in production)
- File uploads: validate MIME type, enforce size limits, scan for malicious content

---

### Output & Error Handling

**Impact: HIGH** | **Category: api-security** | **Tags:** error-handling, information-disclosure

Never expose internal details in API responses. Use generic messages with correlation IDs.

#### ❌ Incorrect

```python
# Exposing stack trace and internal paths
except Exception as e:
    return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

# Different messages for "user not found" vs "wrong password" — enables enumeration
if not user:
    return Response({"error": "User does not exist"}, status=400)
if not user.check_password(password):
    return Response({"error": "Incorrect password"}, status=400)
```

#### ✅ Correct

```python
import uuid

# Generic error with correlation ID
except Exception as e:
    correlation_id = str(uuid.uuid4())
    logger.error(f"Internal error [{correlation_id}]: {e}", exc_info=True)
    return Response(
        {"error": "An internal error occurred.", "correlation_id": correlation_id},
        status=500,
    )

# Uniform authentication error — no enumeration
if not user or not user.check_password(password):
    return Response({"error": "Invalid credentials."}, status=401)
```

**Rules:**
- Never return stack traces, SQL errors, file paths, or server versions in responses
- Use identical error messages for "user not found" and "wrong password"
- Log detailed errors server-side with correlation ID
- Set response headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`
- Django `DEBUG=False` in production — enforced by @senior-devops

---

### Rate Limiting & CORS

**Impact: HIGH** | **Category: api-security** | **Tags:** rate-limiting, cors, dos

Rate limit all endpoints. CORS must use explicit origin allowlists.

#### ❌ Incorrect

```python
# No rate limiting on login — brute force possible
CORS_ALLOW_ALL_ORIGINS = True  # Anyone can call our API
```

#### ✅ Correct

```python
# DRF throttling
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/minute",
        "user": "100/minute",
        "login": "5/minute",
    },
}

# Explicit CORS origins
CORS_ALLOWED_ORIGINS = [
    "https://airaad.vercel.app",
]
CORS_ALLOW_CREDENTIALS = True
```

**Rules:**
- Authentication endpoints: ≤ 5 requests/minute/IP
- General API: ≤ 100 requests/minute/user
- Import/bulk operations: ≤ 10 requests/minute/user
- CORS: explicit origin list only. Never `CORS_ALLOW_ALL_ORIGINS = True` in production.
- Return `429 Too Many Requests` with `Retry-After` header when rate limited

---

## Logging & Audit

### Audit Logging Requirements

**Impact: HIGH** | **Category: audit** | **Tags:** logging, audit-trail, compliance

All security-relevant events must be logged with structured data.

#### Required Events

```python
# Events that MUST be logged:
AUDIT_EVENTS = [
    "auth.login",
    "auth.logout",
    "auth.login_failed",
    "auth.token_refresh",
    "auth.password_change",
    "user.create",
    "user.update",
    "user.delete",
    "user.role_change",
    "vendor.create",
    "vendor.update",
    "vendor.delete",
    "import.start",
    "import.complete",
    "import.fail",
    "admin.config_change",
    "security.rate_limit_hit",
    "security.permission_denied",
]
```

#### Log Format

```python
# Structured audit log entry
audit_entry = {
    "timestamp": "2026-02-25T22:00:00Z",  # ISO 8601 UTC
    "event": "vendor.update",
    "actor": {"user_id": 42, "role": "MANAGER"},
    "resource": {"type": "Vendor", "id": "vendor-123"},
    "action": "UPDATE",
    "result": "SUCCESS",
    "changes": {"name": {"old": "Acme", "new": "Acme Corp"}},
    "correlation_id": "abc-123-def",
    "ip_address": "192.168.1.1",
}
```

**Rules:**
- Use Django's AuditLog model for all data mutations
- Include actor, resource, action, result, and timestamp in every audit entry
- Retain audit logs for minimum 90 days
- Security logs (auth events, permission denials) retained for 1 year
- Audit logs must be immutable — no update or delete operations on audit records

---

### Log Sanitization

**Impact: HIGH** | **Category: audit** | **Tags:** logging, pii, sanitization

Never log RESTRICTED data. Sanitize all log entries before writing.

#### ❌ Incorrect

```python
logger.info(f"User login: email={email}, password={password}")
logger.info(f"Vendor created: phone={vendor.phone_number}")
logger.debug(f"JWT token: {token}")
```

#### ✅ Correct

```python
logger.info(f"User login: user_id={user.id}, result=success")
logger.info(f"Vendor created: vendor_id={vendor.id}")
logger.debug(f"Token refresh: user_id={user.id}, token_type=access")
```

**Rules:**
- Never log: passwords, tokens, encryption keys, full phone numbers, full emails combined with identity
- Mask phone numbers: show only last 4 digits (`*********4567`)
- Use user IDs and resource IDs for identification in logs, not PII
- Sanitize request bodies before logging — strip RESTRICTED fields

---

## Privacy

### Personal Data Handling

**Impact: HIGH** | **Category: privacy** | **Tags:** pii, gdpr, privacy-by-design

PII must be encrypted, masked, and access-controlled at every layer.

#### ❌ Incorrect

```typescript
// Displaying raw phone number in UI
<td>{vendor.phone_number}</td>

// Storing PII in browser storage without need
localStorage.setItem("vendorPhone", vendor.phone);
```

#### ✅ Correct

```typescript
// Masked phone in UI — decrypt only on explicit action with audit trail
<td>{vendor.masked_phone}</td>  {/* *********4567 */}

// Never store PII in browser storage
// Fetch from API on demand, display masked, discard after use
```

**Rules:**
- Phone numbers: encrypted at rest (AES-256-GCM), masked in all displays and API responses
- Email addresses: treated as RESTRICTED when combined with identity
- PII never stored in browser localStorage or sessionStorage
- PII never included in analytics payloads or error reporting
- Support data export and deletion requests (user rights)

---

### Data Minimization & Retention

**Impact: HIGH** | **Category: privacy** | **Tags:** retention, minimization, anonymization

Collect only what is necessary. Define retention limits. Auto-delete expired data.

**Rules:**
- Every new data field must justify its collection purpose
- Default retention: 2 years for business data, 90 days for audit logs, 1 year for security logs
- Analytics must use anonymized or aggregated data — never raw PII
- Soft-delete first, hard-delete after retention period
- Unused data fields should be deprecated and removed in scheduled cleanups

---

## Secure SDLC

### Security Review Triggers

**Impact: HIGH** | **Category: sdlc** | **Tags:** review, threat-model, checkpoints

Certain changes require explicit security review before merge.

**Triggers (require @security-architect review):**
- Any change to authentication or authorization logic
- Any change to encryption, hashing, or key management
- New API endpoints that accept user input
- Changes to CORS, CSP, or security headers
- New data models storing PII or RESTRICTED data
- Changes to deployment configuration or secret management
- New third-party service integrations
- Changes to user role definitions or permission matrices

**Review Checklist:**
- [ ] No hardcoded secrets or credentials
- [ ] Input validated on server side
- [ ] Output encoded/escaped properly
- [ ] RESTRICTED data encrypted and masked
- [ ] Audit logging present for mutations
- [ ] Error responses do not leak internals
- [ ] Rate limiting configured
- [ ] Permissions explicitly declared
- [ ] Dependencies free of critical CVEs

---

### Dependency & Supply Chain Security

**Impact: HIGH** | **Category: sdlc** | **Tags:** dependencies, cve, supply-chain

All dependencies must be scanned for vulnerabilities. Critical CVEs block merge.

#### ❌ Incorrect

```bash
pip install some-package          # No version pinning
npm install random-package        # No audit
```

#### ✅ Correct

```bash
pip install some-package==1.2.3   # Pinned version
pip-audit                         # Check for CVEs
npm ci                            # Reproducible install from lockfile
npm audit --audit-level=critical  # Block on critical CVEs
```

**Rules:**
- Pin all dependency versions in requirements files and package-lock.json
- `safety check` (Python) and `npm audit` run in every CI pipeline
- Critical CVEs: block merge. High CVEs: fix within 1 sprint. Medium: fix within 1 month.
- Review new dependencies before adding — check maintainer reputation, last update, known issues
- Prefer well-maintained packages with active security response

---

## Enforcement Summary

When reviewing or generating code, apply this decision matrix:

| Violation | Severity | Action |
|-----------|----------|--------|
| Hardcoded secret or credential | CRITICAL | **Block** — must fix before merge |
| Weak password hashing | CRITICAL | **Block** — must fix before merge |
| Missing encryption on RESTRICTED data | CRITICAL | **Block** — must fix before merge |
| SQL injection / raw string queries | CRITICAL | **Block** — must fix before merge |
| PII in logs or error responses | CRITICAL | **Block** — must fix before merge |
| Missing input validation | HIGH | **Warn** — should fix before merge |
| Missing audit logging | HIGH | **Warn** — should fix before merge |
| Missing rate limiting | HIGH | **Warn** — should fix before merge |
| Missing permission check on endpoint | HIGH | **Warn** — should fix before merge |
| Overly permissive CORS | HIGH | **Warn** — should fix before merge |
| Missing security headers | MEDIUM | **Warn** — fix or document justification |
| Non-pinned dependency versions | MEDIUM | **Warn** — fix or document justification |

**Escalation:**
- If a CRITICAL violation is found, do NOT approve the change. Request revision.
- If 3+ HIGH violations are found in a single PR, request architectural review.
- Always provide the specific policy reference (§ number from SKILL.md) when flagging a violation.

---

## Quick Reference Checklist

**Before Writing Code (CRITICAL)**
- [ ] Classified data being handled (RESTRICTED / CONFIDENTIAL / INTERNAL / PUBLIC)
- [ ] Identified authentication and authorization requirements
- [ ] Determined encryption requirements based on data classification

**During Implementation (HIGH)**
- [ ] Input validation on all user inputs (server-side)
- [ ] Parameterized queries only (no string-formatted SQL)
- [ ] RESTRICTED data encrypted and masked
- [ ] Audit logging for all data mutations
- [ ] Error responses do not expose internals
- [ ] Permissions explicitly declared on every endpoint

**Before Merge (HIGH)**
- [ ] No hardcoded secrets (TruffleHog passes)
- [ ] Dependencies scanned (no critical CVEs)
- [ ] Security-sensitive changes reviewed against SKILL.md policies
- [ ] PII handling compliant with privacy policies

---

## References

- [SKILL.md](SKILL.md) — Full governance policies (§1–§10)
- [references/security-policies.md](references/security-policies.md) — Detailed standards mapping
- [OWASP Top 10 (2021)](https://owasp.org/Top10/)
- [ISO 27001 Annex A Controls](https://www.iso.org/standard/27001)
- [NIST Cybersecurity Framework 2.0](https://www.nist.gov/cyberframework)
