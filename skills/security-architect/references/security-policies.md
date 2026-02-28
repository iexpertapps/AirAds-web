# Security Policies — Detailed Standards Mapping

This document maps AirAd security policies to international standards and provides detailed implementation guidance. It serves as the reference companion to the main [SKILL.md](../SKILL.md) governance policies.

---

## Standards Cross-Reference Matrix

| Policy § | Title | ISO 27001 | OWASP Top 10 | NIST CSF | Privacy-by-Design |
|----------|-------|-----------|--------------|----------|-------------------|
| §1 | Authentication & Authorization | A.9.1–A.9.4 | A01, A07 | PR.AC | — |
| §2 | Data Classification | A.8.1–A.8.3 | — | ID.AM | Principle 5: End-to-End Security |
| §3 | Encryption Requirements | A.10.1 | A02 | PR.DS | Principle 5: End-to-End Security |
| §4 | Secure API Design | A.14.1–A.14.2 | A01, A03, A04 | PR.DS, PR.IP | — |
| §5 | Logging & Audit | A.12.4 | A09 | DE.CM, DE.AE | — |
| §6 | Secret Management | A.9.2, A.10.1 | A02 | PR.AC, PR.DS | — |
| §7 | Least Privilege Access | A.9.1, A.9.2 | A01 | PR.AC | Principle 7: Respect for User Privacy |
| §8 | Secure SDLC | A.14.2 | A04 | PR.IP | Principle 1: Proactive not Reactive |
| §9 | Privacy & Personal Data | A.18.1 | — | PR.DS | Principles 1–7 |
| §10 | Security Review Checkpoints | A.14.2, A.18.2 | — | PR.IP, DE.CM | Principle 1: Proactive not Reactive |

---

## ISO 27001 Annex A — Applicable Controls

### A.8 — Asset Management

| Control | AirAd Implementation |
|---------|---------------------|
| A.8.1.1 Inventory of assets | All data entities classified in Policy §2 |
| A.8.2.1 Classification of information | Four-tier classification: RESTRICTED, CONFIDENTIAL, INTERNAL, PUBLIC |
| A.8.2.3 Handling of assets | Classification-appropriate controls enforced per §2 table |

### A.9 — Access Control

| Control | AirAd Implementation |
|---------|---------------------|
| A.9.1.1 Access control policy | RBAC with least privilege (§1, §7) |
| A.9.2.3 Management of privileged access | Admin roles explicitly assigned, quarterly review (§7) |
| A.9.4.1 Information access restriction | Every endpoint declares required permissions (§1) |
| A.9.4.2 Secure log-on procedures | Rate-limited login, brute force protection (§1) |
| A.9.4.3 Password management system | Argon2id/bcrypt, complexity requirements (§1) |

### A.10 — Cryptography

| Control | AirAd Implementation |
|---------|---------------------|
| A.10.1.1 Policy on use of cryptographic controls | AES-256-GCM for data at rest, TLS 1.2+ in transit (§3) |
| A.10.1.2 Key management | Keys in env vars, rotation procedures documented (§3, §6) |

### A.12 — Operations Security

| Control | AirAd Implementation |
|---------|---------------------|
| A.12.4.1 Event logging | Structured audit logs for all security events (§5) |
| A.12.4.2 Protection of log information | Audit logs immutable, no PII in logs (§5) |
| A.12.4.3 Administrator and operator logs | Admin actions logged with actor, resource, action, result (§5) |

### A.14 — System Development

| Control | AirAd Implementation |
|---------|---------------------|
| A.14.1.1 Information security requirements | Security requirements in PRD (§8, §10) |
| A.14.2.1 Secure development policy | Secure SDLC with checkpoints (§8) |
| A.14.2.5 Secure system engineering | Threat modeling for auth/data features (§10) |

### A.18 — Compliance

| Control | AirAd Implementation |
|---------|---------------------|
| A.18.1.4 Privacy and protection of PII | Privacy-by-Design principles enforced (§9) |
| A.18.2.3 Technical compliance review | Security review checkpoints in CI/CD (§10) |

---

## OWASP Top 10 (2021) — Coverage

### A01: Broken Access Control

**AirAd Controls:**
- RBAC enforced on every endpoint (§1)
- Object-level permissions for multi-tenant data (§1)
- Default-deny for undefined routes (§1)
- Access control tested in CI (§10)

**Detection:** @code-review-ai-ai-review validates permission declarations on all new endpoints.

### A02: Cryptographic Failures

**AirAd Controls:**
- AES-256-GCM for RESTRICTED data at rest (§3)
- TLS 1.2+ enforced for all communication (§3)
- HSTS with 1-year max-age (§3)
- No weak algorithms permitted (§3)
- Secret entropy requirements defined (§6)

**Detection:** CI scans for hardcoded secrets (TruffleHog). Code review checks for weak crypto.

### A03: Injection

**AirAd Controls:**
- Django ORM / parameterized queries mandatory (§4)
- DRF serializer validation on all inputs (§4)
- No `dangerouslySetInnerHTML` without sanitization (§4)
- Output encoding via Django templates / React JSX (§4)

**Detection:** Semgrep and Bandit in CI. Code review checks for raw SQL construction.

### A04: Insecure Design

**AirAd Controls:**
- Threat modeling for auth/data features (§10)
- Security requirements in PRD (§8)
- Privacy impact assessment for PII features (§9)
- Phased security checkpoints (§10)

**Detection:** @product-manager includes security assessment in feature planning.

### A05: Security Misconfiguration

**AirAd Controls:**
- `DEBUG=False` enforced in production (§4)
- `ALLOWED_HOSTS` set to exact domain (§4)
- Security headers configured (§4)
- Default credentials never used (§6)

**Detection:** @senior-devops validates production Django settings before deploy.

### A06: Vulnerable and Outdated Components

**AirAd Controls:**
- Dependency scanning in CI: Safety (Python), npm audit (JS) (§8)
- Critical CVEs block merge (§8)
- Version pinning in requirements and lockfile (§8)

**Detection:** Automated CI gates. Quarterly dependency review.

### A07: Identification and Authentication Failures

**AirAd Controls:**
- Argon2id password hashing (§1)
- Short-lived JWT access tokens (§1)
- Brute force protection with rate limiting (§1)
- Session binding and timeout (§1)

**Detection:** Code review validates auth implementation. Rate limiting tested.

### A08: Software and Data Integrity Failures

**AirAd Controls:**
- Signed JWT tokens with validated claims (§1)
- CI/CD pipeline integrity (required reviews, branch protection) (§8)
- Dependency lockfiles for reproducible builds (§8)

**Detection:** CI validates lockfile integrity. Code review checks JWT validation.

### A09: Security Logging and Monitoring Failures

**AirAd Controls:**
- Structured audit logging for all security events (§5)
- Log retention: 90 days audit, 1 year security (§5)
- Log sanitization — no PII in logs (§5)

**Detection:** Code review verifies audit logging present on data mutations.

### A10: Server-Side Request Forgery (SSRF)

**AirAd Controls:**
- Validate and allowlist external URLs before server-side requests (§4)
- No user-controlled URLs passed to server-side HTTP clients without validation (§4)
- Network-level restrictions where possible (§4)

**Detection:** Code review flags any server-side HTTP requests with user-controlled URLs.

---

## NIST Cybersecurity Framework 2.0 — Mapping

### Identify (ID)

| Subcategory | AirAd Implementation |
|-------------|---------------------|
| ID.AM — Asset Management | Data classification (§2) |
| ID.RA — Risk Assessment | Threat modeling at feature design (§10) |

### Protect (PR)

| Subcategory | AirAd Implementation |
|-------------|---------------------|
| PR.AC — Access Control | RBAC, least privilege, MFA for admins (§1, §7) |
| PR.DS — Data Security | Encryption at rest and in transit (§3), privacy controls (§9) |
| PR.IP — Information Protection | Secure SDLC, security checkpoints (§8, §10) |

### Detect (DE)

| Subcategory | AirAd Implementation |
|-------------|---------------------|
| DE.CM — Continuous Monitoring | Audit logging, secret scanning in CI (§5, §6) |
| DE.AE — Anomaly & Events | Rate limiting, failed auth tracking (§1, §4) |

### Respond (RS)

| Subcategory | AirAd Implementation |
|-------------|---------------------|
| RS.RP — Response Planning | Incident response: triage 4h, critical patch 24h (§8) |
| RS.AN — Analysis | Post-incident review within 1 week (§8) |

### Recover (RC)

| Subcategory | AirAd Implementation |
|-------------|---------------------|
| RC.RP — Recovery Planning | Rollback procedures documented per service (§8) |

---

## Privacy-by-Design — 7 Foundational Principles

| Principle | AirAd Implementation |
|-----------|---------------------|
| 1. Proactive not Reactive | Security checkpoints at design phase, not post-deployment (§8, §10) |
| 2. Privacy as the Default | Data classified CONFIDENTIAL by default, PII encrypted (§2, §9) |
| 3. Privacy Embedded into Design | Security requirements in PRD, threat modeling before build (§8, §10) |
| 4. Full Functionality | Security does not block features — graduated enforcement (SKILL.md Enforcement) |
| 5. End-to-End Security | Encryption in transit (TLS) and at rest (AES-256), full lifecycle (§3) |
| 6. Visibility and Transparency | Audit logging, structured logs, retention policies (§5) |
| 7. Respect for User Privacy | Data minimization, retention limits, user rights (export/delete) (§9) |

---

## AirAd-Specific Security Architecture

### Data Flow Security

```
User Browser (HTTPS/TLS 1.2+)
    │
    ├── Vercel (React SPA)
    │     ├── CSP headers enforced
    │     ├── X-Frame-Options: DENY
    │     ├── Access tokens in sessionStorage (XSS-mitigated)
    │     └── PII masked in display
    │
    ├── HTTPS API calls
    │
    └── Railway (Django API)
          ├── DRF serializer validation on all inputs
          ├── RBAC permission checks on all endpoints
          ├── RESTRICTED data encrypted at rest (AES-256-GCM)
          ├── Audit logging on all mutations
          ├── Rate limiting on all endpoints
          └── PostgreSQL (encrypted connection, least-privilege DB user)
```

### Secret Distribution

```
GitHub Secrets
    ├── RAILWAY_TOKEN → deploy only
    ├── VERCEL_TOKEN → deploy only
    └── CI-only secrets (never reach production)

Railway Dashboard (Backend)
    ├── DJANGO_SECRET_KEY
    ├── DATABASE_URL (auto-injected)
    ├── REDIS_URL (auto-injected)
    ├── PHONE_ENCRYPTION_KEY
    └── Third-party API keys

Vercel Dashboard (Frontend)
    ├── VITE_API_URL (public, non-secret)
    └── VITE_APP_ENV (public, non-secret)
    └── ⚠️ NEVER put secrets here — they are bundled into public JS
```

### Authentication Flow Security

```
Login Request
    │
    ├── Rate limit check (≤ 5/min/IP)
    ├── DRF serializer validation
    ├── Django authenticate() — Argon2id hash comparison
    ├── Audit log: auth.login / auth.login_failed
    │
    ├── Success:
    │     ├── Issue JWT access token (15 min)
    │     ├── Issue JWT refresh token (24h, rotated)
    │     └── Return user profile (PII masked)
    │
    └── Failure:
          ├── Generic "Invalid credentials" (no enumeration)
          ├── Progressive delay after 5+ failures
          └── Account lockout after 10 consecutive failures
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-25 | Security Architect | Initial governance layer creation |
