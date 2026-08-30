# Goal Intake Hardening

## Problem

On onboarding step 0, learners can type careers in natural language that do not exactly match PathFinder's canonical role ontology (e.g. "penetration tester", "cloud security", "MLOps engineer", "build mobile apps"). When resolution did not produce a canonical `role`, the frontend set `phase = "resolved"` but rendered no recovery UI — the Resolve button stayed disabled with no path forward.

## Root Cause

**Frontend dead-end**, not a missing backend entirely.

`GoalIntelligenceField.tsx` only showed the success card when `resolvedIntake?.role` existed. After `onResolve()` returned an intake with `role: null` (ambiguous or unsupported), the component entered a hidden state: input hidden, no resolved/ambiguous/unsupported card, Resolve disabled because `phase !== "idle"`.

The backend could return partial structure, but there was no `resolution_status` field and no explicit AMBIGUOUS / UNSUPPORTED contract for the UI.

## Existing Architecture

```
USER GOAL
   ↓
RULE PATH (deterministic keyword resolver) — if RESOLVED, return immediately
   ↓ (otherwise)
GROQ openai/gpt-oss-120b (language interpretation only)
   ↓
STRUCTURED JSON (career_mentions, focus_mentions, skills)
   ↓
DETERMINISTIC ONTOLOGY RESOLVER (_finalize_resolution)
   ↓
RESOLVED | AMBIGUOUS | UNSUPPORTED
   ↓
EXISTING PATHFINDER PIPELINE (unchanged)
```

Key files:

| Layer | File |
|-------|------|
| API | `backend/app/api/intake.py` |
| Extraction | `backend/app/services/intake/extract.py` |
| Resolver | `backend/app/services/intake/resolver.py` |
| LLM provider | `backend/app/services/llm/provider.py` |
| Schema | `backend/app/schemas/intelligence.py` |
| UI | `frontend/components/onboarding/GoalIntelligenceField.tsx` |
| Session | `frontend/components/onboarding/Onboarding.tsx` |

## Groq Role

Groq **GPT-OSS-120B** (`openai/gpt-oss-120b`) is a **language interpretation layer only**.

- Extracts `career_mentions`, `focus_mentions`, `goal_summary`, skill mentions
- Does **not** output canonical role slugs
- Does **not** create skills, roles, prerequisites, or courses
- User text is delimited as untrusted: `Untrusted learner goal text:\n<<<...>>>`
- On timeout, malformed JSON, or provider unavailability → falls back to deterministic rule path
- Config via env only: `PATHFINDER_AI_PROVIDER`, `PATHFINDER_AI_BASE_URL`, `PATHFINDER_AI_MODEL`, `PATHFINDER_AI_API_KEY`

## Ontology Resolution

After extraction (rule or LLM), `_finalize_resolution()` is authoritative:

1. **Ambiguous phrase table** (`AMBIGUOUS_ROLE_PHRASES`) — e.g. `"career in data"` → Data Engineer + Data Analyst; `"cloud security"` → Cybersecurity Analyst + Cloud/DevOps Engineer
2. **Multi-role span collection** (`collect_roles_from_text`) with non-overlapping spans — prevents short alias `"analyst"` from conflicting with `"cybersecurity analyst"`
3. **Explicit aliases** (`ROLE_ALIASES`) — ontology-backed, test-covered:
   - `penetration tester`, `pen tester`, `pentester` → Cybersecurity Analyst
   - `mlops engineer`, `mlops` → AI/ML Engineer
   - `mobile apps`, `ios developer` → Frontend Developer
4. **Never invent roles** — unsupported mentions land in `unresolved` with `resolution_status: UNSUPPORTED`

## Ambiguous Handling

When multiple canonical roles are equally supported, the API returns:

```json
{
  "resolution_status": "AMBIGUOUS",
  "role": null,
  "role_alternatives": [ ... ]
}
```

UI shows **"Which route fits your goal?"** with selectable candidates. No automatic pick.

## Unsupported Handling

When no ontology-backed role matches:

```json
{
  "resolution_status": "UNSUPPORTED",
  "role": null,
  "unresolved": [ "marine biologist" ]
}
```

UI shows **"Goal not mapped yet"** with preserved goal text and actions: See supported careers, Edit goal, Pick career manually.

## Fallback

| Condition | Behavior |
|-----------|----------|
| Rule path RESOLVED | LLM skipped (cost + latency) |
| LLM unavailable / timeout / bad JSON | Rule path returned |
| LLM returns invented role | Resolver rejects → UNSUPPORTED or rule fallback |
| API network failure | Frontend `error` phase + manual fallback |
| Empty / too-short goal | 422 validation |

Manual career selection is always available on the input phase and in ambiguous/unsupported cards.

## Timeout

`PATHFINDER_AI_TIMEOUT_SECONDS` (default 8s, 30s in Groq config) bounds LLM calls. Frontend `error` phase shows: *"Goal interpretation did not complete. You can try again or pick a career manually."* Onboarding state and goal text are preserved.

## Prompt Injection

System prompt instructs the model to ignore in-text instructions to create entities. Structured parser treats adversarial text as mentions only. Resolver remains authoritative — high model confidence cannot create unsupported roles.

## Security

- API key: backend env only (`PATHFINDER_AI_API_KEY`), never frontend, never committed
- No key logging
- User goal rendered as React text nodes (no `dangerouslySetInnerHTML`)
- Input truncated to 2000 characters

## Tests

### Backend (`tests/test_goal_intake_hardening.py`) — 19 tests

Covers: exact role, aliases, synonyms, specialization, ambiguity, unsupported, empty input, long input, malformed LLM JSON, timeout, provider unavailable, invented role/skill, prompt injection, API contract.

### Frontend (`frontend/tests/goal-intake-field.test.tsx`) — 3 tests

Covers: resolved, ambiguous, unsupported UI states.

### Product completion (`tests/test_product_completion.py`)

Updated API assertion for `resolution_status` field.

## Browser Proof

Script: `scripts/goal_intake_browser_qa.mjs`

Stack: `next start` :3002, API :8000, Postgres :5433

**15/15 PASS** at 1440×900 and 390×844 — see `artifacts/goal-intake-qa/summary.json`

| Goal | Result |
|------|--------|
| ML engineer + computer vision | RESOLVED |
| pen tester | RESOLVED → Cybersecurity Analyst |
| cloud security | AMBIGUOUS |
| MLOps engineer | RESOLVED → AI/ML Engineer |
| career in data | AMBIGUOUS |
| marine biologist | UNSUPPORTED |
| quantum potato infrastructure architect | UNSUPPORTED |
| Provider failure (aborted API) | Error + manual fallback |

0 console errors (except expected `ERR_FAILED` on injected failure). 0 network errors on happy path.

## Latency

Live Groq verification (`artifacts/goal-intake-qa/live-groq.json`):

| Goal | Status | Source | Latency |
|------|--------|--------|---------|
| penetration tester + web apps | RESOLVED | DETERMINISTIC (rule short-circuit) | ~0ms |
| career in data | AMBIGUOUS | DETERMINISTIC | ~0ms |
| adversarial quantum engineer | UNSUPPORTED | LLM + resolver | ~1–2s |
| underwater asteroid farming architect | UNSUPPORTED | LLM + resolver | ~1–2s |

Most common aliases resolve deterministically without an LLM call.

## Cost

Rule-path short-circuit avoids Groq when deterministic resolution succeeds. No caching layer added in this pass (existing architecture unchanged). LLM called only when rule path does not produce RESOLVED.

## Known Limitations

- Alias table is explicit, not exhaustive — new synonyms require ontology-backed alias entries
- `"product engineer"` has no alias (UNSUPPORTED unless learner picks manually)
- Ambiguous phrase table is curated, not learned
- Frontend timeout is network-level (fetch) not a separate server-side streaming cancel
- Live Groq latency varies; deterministic path is preferred for known phrases
- Dual-theme files were modified in the same working tree but theme system was not redesigned in this pass

## Regression (2026-08-30)

| Gate | Result |
|------|--------|
| `python -m pytest -q` | **237 passed**, 1 skipped |
| `npm test` | **56 passed** |
| `npm run build` | **PASS** |
| `python scripts/intelligence_benchmark.py` | **20/20** |
| Browser QA | **15/15** |

Intelligence engines (`retrieval`, `recommendation`, `gap_engine`, `adaptation`) were not modified.
