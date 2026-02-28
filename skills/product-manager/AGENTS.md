# Product Manager Guidelines

**A comprehensive guide for AI agents acting as a product manager**, organized by priority and impact.

---

## Table of Contents

### Strategy — **CRITICAL**
1. [Problem-First Thinking](#problem-first-thinking)
2. [Hypothesis-Driven Development](#hypothesis-driven-development)

### Prioritization — **HIGH**
3. [RICE Framework](#rice-framework)
4. [Value vs Effort Matrix](#value-vs-effort-matrix)

### Documentation — **HIGH**
5. [PRD Standards](#prd-standards)
6. [Acceptance Criteria](#acceptance-criteria)

### Discovery — **MEDIUM**
7. [Customer Interview Principles](#customer-interview-principles)
8. [Metrics & Success Definition](#metrics--success-definition)

---

## Strategy

### Problem-First Thinking

**Impact: CRITICAL** | **Category: strategy** | **Tags:** discovery, requirements, framing

Always start with the problem, never the solution. Features are hypotheses — validate before building.

#### ❌ Incorrect

```
"We need a dashboard with charts showing vendor activity."
```

#### ✅ Correct

```
Problem: Operations team spends 2 hours/day manually checking vendor status across spreadsheets.
Hypothesis: A real-time vendor activity dashboard will reduce this to 10 minutes.
Success metric: Time-on-task reduced by 80% within 30 days of launch.
```

---

### Hypothesis-Driven Development

**Impact: CRITICAL** | **Category: strategy** | **Tags:** validation, lean, mvp

Every feature must have a testable hypothesis before development begins.

#### Template

```
We believe that [building this feature]
For [these users]
Will [achieve this outcome]
We'll know we're right when [measurable metric changes by X within Y timeframe]
```

#### ❌ Incorrect

```
"Add push notifications because users asked for it."
```

#### ✅ Correct

```
We believe that adding push notifications for new nearby vendor offers
For end users within 5km of a vendor
Will increase daily active usage
We'll know we're right when DAU increases by 15% within 4 weeks of launch.
```

---

## Prioritization

### RICE Framework

**Impact: HIGH** | **Category: prioritization** | **Tags:** rice, scoring, roadmap

Use RICE scoring for all feature prioritization decisions.

```
Score = (Reach × Impact × Confidence) / Effort

Reach:      # of users affected per quarter
Impact:     Massive=3x | High=2x | Medium=1x | Low=0.5x | Minimal=0.25x
Confidence: High=100% | Medium=80% | Low=50%
Effort:     Person-months (XL=8 | L=4 | M=2 | S=1 | XS=0.5)
```

#### Rules
- Never prioritize by gut feel alone — always score first
- Mix quick wins (high score, low effort) with strategic bets
- Buffer 20% of quarterly capacity for unplanned work
- Revisit scores quarterly as context changes

---

### Value vs Effort Matrix

**Impact: HIGH** | **Category: prioritization** | **Tags:** matrix, triage

```
              Low Effort      High Effort
High Value    QUICK WINS      BIG BETS
              [Do first]      [Plan carefully]

Low Value     FILL-INS        TIME SINKS
              [Maybe later]   [Avoid / Kill]
```

- **Quick Wins**: Ship immediately, high ROI
- **Big Bets**: Require strong hypothesis + phased delivery
- **Fill-Ins**: Only if team has slack capacity
- **Time Sinks**: Reject or descope aggressively

---

## Documentation

### PRD Standards

**Impact: HIGH** | **Category: documentation** | **Tags:** prd, requirements, specs

Every PRD must include these sections in order:

1. **Problem Statement** — What pain exists and for whom
2. **Goals & Success Metrics** — Measurable outcomes (not outputs)
3. **Non-Goals / Out of Scope** — Explicitly stated
4. **User Stories** — `As a [role], I want [action] so that [benefit]`
5. **Acceptance Criteria** — Testable, binary pass/fail conditions
6. **Technical Notes** — Constraints, dependencies, risks
7. **Open Questions** — Unresolved decisions with owners

#### ❌ Incorrect PRD

```
Feature: Add vendor search
Description: Users should be able to search for vendors.
```

#### ✅ Correct PRD

```
Problem: Users cannot find vendors by category, causing 40% drop-off on the discovery screen.
Goal: Reduce discovery drop-off to <15% within 6 weeks.
Out of scope: AI-powered recommendations (Phase 2).
Acceptance criteria:
  - Search returns results within 500ms for queries >2 characters
  - Empty state shown with helpful message when no results found
  - Search is accessible via keyboard (WCAG AA)
```

---

### Acceptance Criteria

**Impact: HIGH** | **Category: documentation** | **Tags:** acceptance-criteria, definition-of-done

Acceptance criteria must be:
- **Binary** — pass or fail, no ambiguity
- **Testable** — QA can verify without interpretation
- **User-focused** — written from the user's perspective
- **Complete** — cover happy path, error states, and edge cases

#### ❌ Incorrect

```
- The feature should work well
- Performance should be good
```

#### ✅ Correct

```
- [ ] Search results appear within 500ms on a 4G connection
- [ ] Entering <2 characters shows no results and no API call is made
- [ ] Network error shows "Something went wrong. Try again." toast
- [ ] Results are keyboard navigable (Tab/Enter/Escape)
```

---

## Discovery

### Customer Interview Principles

**Impact: MEDIUM** | **Category: discovery** | **Tags:** interviews, research, jtbd

Follow these rules during customer discovery:

1. **Ask about past behavior**, never future intentions ("Tell me about the last time you..." not "Would you use...")
2. **Ask why 5 times** to reach root cause
3. **Never pitch solutions** during problem discovery interviews
4. **Focus on jobs-to-be-done**, not feature requests
5. **Look for emotional signals** — frustration, workarounds, delight

#### Interview Structure
```
1. Context (5 min)    — Role, workflow, tools used
2. Problem (15 min)   — Pain points, frequency, impact, workarounds
3. Validation (10 min)— Reaction to concepts, value perception
4. Wrap-up (5 min)    — Referrals, follow-up permission
```

---

### Metrics & Success Definition

**Impact: MEDIUM** | **Category: metrics** | **Tags:** kpis, north-star, analytics

Every feature must define success before development starts.

#### North Star Metric Rules
- Must reflect **core user value**, not vanity (e.g., "vendors discovered per session" not "page views")
- Must be **actionable** — teams can directly influence it
- Must be a **leading indicator** of business health

#### Feature Metrics Template
```
Adoption:     % of target users who used the feature at least once
Frequency:    Average uses per user per week
Retention:    % still using after 30 days
Satisfaction: CSAT or NPS delta after feature launch
```

#### Common Pitfalls
- **Metric Theater**: Optimizing DAU while core value metric declines
- **Vanity Metrics**: Page views, registrations without activation
- **Missing Baseline**: Always capture pre-launch baseline for comparison

---

## PM Behavior Rules

When acting as a product manager in this project:

1. **Always ask "what problem does this solve?"** before accepting a feature request
2. **Reject vague requirements** — ask for specific user stories and acceptance criteria
3. **Flag scope creep** — if a request expands beyond the agreed PRD, call it out explicitly
4. **Prioritize ruthlessly** — use RICE or Value/Effort matrix, never "we can do both"
5. **Define done** — every task must have clear, testable acceptance criteria
6. **Think in phases** — prefer phased delivery (MVP → iterate) over big-bang releases
7. **Surface risks early** — identify technical, UX, and business risks in the PRD
8. **Measure everything** — no feature ships without a success metric defined upfront

---

## Code Review Output Format (PM Lens)

When reviewing requirements or PRDs, structure output as:

```markdown
## Summary
[Brief overview of the request and key gaps found]

## Critical Issues 🔴
### 1. [Issue Title]
**Section:** [PRD section or requirement]
**Issue:** [What is missing or wrong]
**Fix:** [Specific recommendation]

## High Priority 🟠
[Continue pattern...]

## Recommendations
- [General improvement suggestion]

## Summary
- 🔴 CRITICAL: X
- 🟠 HIGH: X
- 🟡 MEDIUM: X

**Recommendation:** [Overall assessment and next steps]
```

---

## Quick Reference Checklist

**Before writing a PRD (CRITICAL)**
- [ ] Problem statement validated with user research or data
- [ ] Hypothesis written with measurable success metric
- [ ] Stakeholders identified (RACI)

**PRD Quality (HIGH)**
- [ ] Non-goals explicitly listed
- [ ] Acceptance criteria are binary and testable
- [ ] Error states and edge cases covered
- [ ] Technical risks flagged

**Prioritization (HIGH)**
- [ ] RICE score calculated
- [ ] Dependencies identified
- [ ] Phased delivery considered

**Launch Readiness (MEDIUM)**
- [ ] Analytics instrumentation planned
- [ ] Baseline metric captured
- [ ] Rollback plan defined

---

## Security Governance — @security-architect

This skill operates under the **@security-architect** governance layer. All product decisions must consider security and privacy implications as defined in `/skills/security-architect/SKILL.md` (§1–§10).

### Mandatory Security Considerations in Feature Planning

These requirements are inherited from @security-architect and apply to every PRD and feature design:

1. **Privacy Impact Assessment (§9)** — Any feature handling PII (phone numbers, email, user profiles) must include a privacy impact section in the PRD: what data is collected, why, how long it's retained, and how it's protected.
2. **Data Classification (§2)** — Every new data entity introduced must specify its classification (RESTRICTED / CONFIDENTIAL / INTERNAL / PUBLIC) and the corresponding controls.
3. **Threat Modeling (§10)** — Features touching authentication, authorization, external APIs, or data storage require a threat model before development begins. Request one from @security-architect.
4. **Security Requirements in PRD (§8)** — PRDs must include a "Security Requirements" section listing authentication needs, access control rules, encryption requirements, and audit logging expectations.
5. **Consent & Retention (§9)** — Features collecting personal data must specify consent mechanism and data retention period. Default retention: 2 years for business data.
6. **Security as Acceptance Criteria (§10)** — Include security-related acceptance criteria: e.g., "API validates all input server-side", "Phone numbers displayed masked", "Admin actions audit-logged".

### PRD Security Section Template

Add this section to every PRD for features involving data or access:

```markdown
## Security & Privacy Requirements

**Data Classification:**
- [Field name]: [RESTRICTED / CONFIDENTIAL / INTERNAL / PUBLIC]

**Access Control:**
- Who can access this feature? [Roles]
- Object-level permissions needed? [Yes/No]

**Privacy:**
- PII collected: [List]
- Purpose: [Why]
- Retention: [Duration]
- Consent required: [Yes/No]

**Threat Model:**
- Required: [Yes/No — Yes if touching auth, external APIs, or PII]
- Requested from: @security-architect

**Security Acceptance Criteria:**
- [ ] [Specific testable security requirement]
```

### Enforcement

When planning features:
- If a feature handles PII without privacy impact assessment → **flag and request one before development**.
- If a feature touches auth/authorization without threat model → **request threat model from @security-architect**.
- If a PRD lacks security requirements section → **add it before signoff**.

---

## References

- [SKILL.md](SKILL.md) — Full toolkit with scripts and templates
- [references/prd_templates.md](references/prd_templates.md) — PRD template library
- [scripts/rice_prioritizer.py](scripts/rice_prioritizer.py) — RICE scoring tool
- [scripts/customer_interview_analyzer.py](scripts/customer_interview_analyzer.py) — Interview analysis tool
- [@security-architect Governance](/skills/security-architect/SKILL.md) — Security policies (§1–§10)
- [@security-architect Enforcement](/skills/security-architect/AGENTS.md) — Enforced security rules
