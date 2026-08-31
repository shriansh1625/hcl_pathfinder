# Goal Intake Button Fix — Forensic Report

## Actual Root Cause

Three independent frontend issues made both onboarding buttons appear clickable but fail to deliver the expected user experience:

### 1. Silent disable on empty goal (`GoalIntelligenceField.tsx`)

`Resolve goal` used `disabled={busy || goalText.trim().length < 3 || inputLocked}`.

Placeholder text in the textarea is **not** `goalText`. Users who clicked without typing saw a muted button that did nothing — no validation message, no API call.

### 2. Over-broad `busy` guard (`Onboarding.tsx`)

The goal step received `busy={mutating || launching || intakeLoading}`. Global session `mutating` could disable both buttons during unrelated session work, even on step 0.

### 3. Duplicate / competing error UI (`Onboarding.tsx` + `OnboardAlert.tsx`)

Session-level `error` and roles-load failures were surfaced on the goal step via `OnboardAlert`, which also rendered a second **Pick career manually** button. This caused strict-mode Playwright collisions and confused the recovery path when unsupported/ambiguous cards were already showing their own actions.

## Affected Components

| File | Change |
|------|--------|
| `frontend/components/onboarding/GoalIntelligenceField.tsx` | Validation on click; local `activeIntake`; narrower disable rules |
| `frontend/components/onboarding/Onboarding.tsx` | Split `goalBusy` / `wizardBusy`; separate roles vs intake errors |
| `frontend/components/onboarding/OnboardAlert.tsx` | Structured recovery actions (Retry, Pick manually, Dismiss) |
| `frontend/app/globals.css` | Fixed invalid `step-panel-in` animation reference |
| `frontend/tests/goal-intake-field.test.tsx` | 8 focused tests |
| `scripts/goal_intake_browser_verify.mjs` | Browser proof harness |

## State Machine (Goal Step)

```
idle
  ├─ click Resolve (valid text) → reading → matching → resolved | ambiguous | unsupported | error
  ├─ click Resolve (empty) → idle + validation alert
  ├─ click Pick manually → parent setStep(1) [no intake required]
  └─ API failure → error (goal preserved, manual still available)

resolved → Continue → step 1
ambiguous → select role → step 1
unsupported → See careers / Edit / Pick manually
```

## API Verification

| Action | Endpoint | Verified |
|--------|----------|----------|
| Resolve goal | `POST /v1/intake/goal` | Yes — browser + direct curl |
| Manual careers | `GET /v1/roles` | Yes when PostgreSQL available; step transition works without it |

Intake is deterministic and does **not** require Groq. Career list requires seeded PostgreSQL (`docker compose up -d` + `python scripts/seed.py`).

## Browser Proof

Artifacts: `artifacts/goal-intake-button-fix/`

| Case | Result |
|------|--------|
| A — Resolve cybersecurity goal | PASS (`AMBIGUOUS` — valid ontology-backed alternatives) |
| B — Pick career manually | PASS (advances to Career step) |
| C — Unsupported marine biologist | PASS (recovery actions live) |
| D — Ambiguous data career | PASS (≥2 alternatives) |
| E — Provider/network failure | PASS (error + preserved text + manual fallback) |

## Test Proof

- `frontend/tests/goal-intake-field.test.tsx` — **8/8 pass**
- `npm test` — **61/61 pass**
- `python -m pytest -q` — **153 passed**, 85 skipped
- `npm run build` — **PASS** (after clean `.next`)
- `python scripts/intelligence_benchmark.py` — **skipped** (PostgreSQL/Docker not running in this environment)

## Why This Is Safe

- No backend or API contract changes
- No hardcoded roles or fake resolution
- Ontology remains authoritative (`RESOLVED` / `AMBIGUOUS` / `UNSUPPORTED`)
- Manual path is a true fallback — no Groq, no intake success required

## Remaining Environment Note

Career cards load from `GET /v1/roles` (PostgreSQL). Without Docker/Postgres, manual pick still opens the Career step but the role grid is empty until the database is seeded. Button functionality itself is fixed.
