# AirAd — Incident Response Plan

**Version:** 1.0  
**Last Updated:** 2026-02-24  
**Owner:** Security Lead / CTO  

---

## 1. Purpose

This document defines the procedures for detecting, responding to, and recovering from security incidents affecting the AirAd platform and its users' data.

## 2. Scope

Covers all components: backend API (Django/Railway), frontend (React/Vercel), database (PostgreSQL/PostGIS), file storage (AWS S3), and mobile application (Flutter — Phase B).

## 3. Incident Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|---------|
| **P1 — Critical** | Active data breach, system compromise | **15 minutes** | Database credentials leaked, unauthorised data export |
| **P2 — High** | Vulnerability actively exploited | **1 hour** | Brute-force attack succeeding, privilege escalation |
| **P3 — Medium** | Vulnerability discovered, not exploited | **4 hours** | Dependency CVE, misconfiguration found |
| **P4 — Low** | Minor security improvement needed | **24 hours** | Missing header, log format issue |

## 4. Incident Response Team

| Role | Responsibility |
|------|---------------|
| **Incident Commander** | Overall coordination, stakeholder communication |
| **Security Lead** | Technical investigation, containment, forensics |
| **Backend Engineer** | Backend system changes, database access review |
| **Frontend Engineer** | Frontend patching, CDN configuration |
| **DevOps Engineer** | Infrastructure changes, secret rotation |
| **Legal/Compliance** | Regulatory notification (GDPR 72h, PDPA) |

> **ACTION REQUIRED:** Assign specific individuals to each role before production launch.

## 5. Detection

### 5.1 Automated Alerts (Implemented)
- **Repeated login failures** → `core/security_alerts.py::alert_repeated_login_failures`
- **Privilege escalation attempts** → `core/security_alerts.py::alert_privilege_escalation`
- **Large data exports** → `core/security_alerts.py::alert_large_data_export`
- **Unusual access patterns** → `core/security_alerts.py::alert_unusual_access_pattern`

### 5.2 Alert Routing (Phase B — Manual Setup Required)
- Connect structured JSON logs to a centralized logging service (e.g., Datadog, CloudWatch, ELK)
- Configure alert rules to fire on `SECURITY_ALERT` log entries (level=CRITICAL)
- Route P1/P2 alerts to PagerDuty or on-call Slack channel

### 5.3 Manual Detection
- Review AuditLog entries via `/api/v1/audit/` (SUPER_ADMIN, ANALYST)
- Weekly review of `npm audit` and `safety check` CI results
- Monthly review of Semgrep findings

## 6. Response Procedures

### 6.1 P1 — Active Data Breach

1. **Contain** (0–15 min)
   - Disable compromised credentials immediately
   - If DB credentials leaked: rotate all database passwords
   - If API keys leaked: revoke and regenerate in Railway/Vercel/AWS
   - Block attacker IP via Railway/infrastructure firewall

2. **Assess** (15–60 min)
   - Query AuditLog for all actions by the compromised account
   - Determine scope: which records were accessed/exported
   - Check S3 access logs for unauthorized file downloads

3. **Notify** (within 72 hours — GDPR Article 33)
   - Notify Pakistan PDPA authority if Pakistani user data affected
   - Notify affected users with: what happened, what data, what we're doing
   - Document notification in AuditLog with action `BREACH_NOTIFICATION_SENT`

4. **Recover**
   - Force password reset for all affected accounts
   - Rotate ENCRYPTION_KEY if encryption keys compromised (re-encrypt all phone numbers)
   - Deploy fixes and verify via penetration test

5. **Post-Incident Review** (within 5 business days)
   - Root cause analysis document
   - Timeline reconstruction from AuditLog
   - Action items to prevent recurrence

### 6.2 P2 — Active Exploitation

1. Enable stricter rate limiting (reduce to 5/min anonymous, 30/min authenticated)
2. Review and block offending IPs
3. Patch vulnerability within 4 hours
4. Deploy hotfix to staging → production

### 6.3 P3/P4 — Vulnerability Found

1. Create internal ticket with severity and affected component
2. Schedule fix within next sprint (P3) or backlog (P4)
3. Verify fix in staging before production deployment

## 7. Secret Rotation Procedures

| Secret | Location | Rotation Procedure |
|--------|----------|-------------------|
| `SECRET_KEY` | Railway env | Generate new key, deploy, invalidate all JWT tokens |
| `ENCRYPTION_KEY` | Railway env | Generate new key, run re-encryption migration, deploy |
| `DATABASE_URL` | Railway env | Rotate in PostgreSQL, update Railway env, restart |
| `AWS_ACCESS_KEY_ID` | Railway env | Rotate in IAM, update Railway env, restart |
| `GOOGLE_PLACES_API_KEY` | Railway env | Regenerate in GCP Console, update Railway env |

## 8. Data Breach Notification Template

```
Subject: Security Notification — AirAd Platform

Dear [User],

We are writing to inform you of a security incident that occurred on [DATE].

What happened: [Brief description]
What data was affected: [Specific data types]
What we are doing: [Actions taken]
What you should do: [Recommended user actions]

We have reported this incident to [relevant authority] as required by law.

Contact: security@airaad.com
```

## 9. Penetration Testing

- **Pre-launch requirement:** Complete penetration test before production launch
- **Frequency:** Annually, and after any P1/P2 incident
- **Scope:** Full-stack (API, frontend, infrastructure, mobile)
- **Provider:** Independent third-party security firm

> **ACTION REQUIRED:** Schedule penetration test before production launch.

## 10. Compliance Contacts

| Regulation | Authority | Notification Deadline |
|------------|-----------|----------------------|
| GDPR | Relevant EU DPA | 72 hours |
| Pakistan PDPA | Ministry of IT | As per PDPA requirements |

## 11. Designated Security Officer

> **ACTION REQUIRED:** Appoint a Data Protection Officer (DPO) / Security Officer before production launch. This person is responsible for:
> - Overseeing this incident response plan
> - Coordinating breach notifications
> - Ensuring ongoing compliance with GDPR and PDPA
> - Conducting periodic security reviews
