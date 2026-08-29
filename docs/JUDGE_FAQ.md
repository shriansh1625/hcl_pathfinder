# PathFinder — Judge FAQ

Answers a hostile evaluator can verify in the **running product**, README, and proof artifacts — without reading source code.

---

## What problem does PathFinder solve?

Learners pick a career goal but platforms rarely show **what is actually missing**, **why a resource is next**, or **how proof changes the plan**. PathFinder diagnoses against a fixed role ontology, sequences dependency-aware resources, and **adapts the path when new evidence arrives**.

---

## How is it different from an LMS?

An LMS delivers content. PathFinder:

- Maintains a **competency model** from fused evidence
- Computes **role-relative gaps** (not generic completion %)
- Sequences resources with **prerequisite blockers**
- Versions paths (**V1 → V2**) when diagnosis changes
- **Freezes completed work** across adaptations

The LLM **explains**; it does not change scores, ranking, or sequencing.

---

## What does PathFinder know about me?

For your target role it knows:

- Which competencies are **UNKNOWN** (no evidence)
- Which are **GAP**, **NEAR TARGET**, **TARGET MET**, or **CONFLICT**
- Which resources are **executable**, **waiting**, or **blocked**
- Your path **version** and what changed between versions

See **Dashboard** and **Skill Map**.

---

## How does it know?

Evidence is fused from:

1. **Self-report** (onboarding profile)
2. **Assessments** (canonical gates)
3. **Progress feedback** (complete / struggled / skip + confidence)

Fusion → gap engine → recommendation → path sequencing. All deterministic Python against `data/` ontology.

---

## Why is UNKNOWN not zero?

**UNKNOWN** means *no evidence yet* — not “0% skilled.” Treating unknown as zero would falsely diagnose gaps and pollute recommendations. Dashboard and competency rows show **NO EVIDENCE** / dashed states instead of fake percentages.

**Verify:** onboarding with minimal evidence → many skills show UNKNOWN, not 0%.

---

## What am I missing?

**Dashboard → gaps** and **Blockers** list diagnosed gaps for your role. **Skill Map** shows dependency relationships. Gaps come from backend `gaps` API — the UI does not recalculate them.

---

## Why is that gap important?

Each gap is tied to a **role competency** in the ontology. Blockers explain **prerequisite chains** (e.g., Docker verification before ML deployment labs). Open **WHY** on a resource for diagnosed gap + role relevance + prerequisite fit.

---

## Why this resource?

Open **WHY THIS RESOURCE** on any path item. You will see backend-provided factors:

- Diagnosed gap
- Role relevance
- Prerequisite fit
- Difficulty / duration / learning-style fit
- Semantic relevance (bounded)
- Intervention + why now

Then **GROUNDED IN** verified facts for AI explanations.

---

## Why this order?

Path sequencing respects:

- **Hard prerequisites** (must verify first)
- **Gap priority** and intervention type
- **Completed / frozen** items (never reordered away)
- Adaptation **PathDiff** when evidence changes

**Verify:** blocked item shows **WAITING FOR VERIFICATION** with prerequisite named.

---

## Why can't I start?

Usually a **prerequisite blocker**: upstream skill lacks evidence or a verification gate is incomplete. **Blockers** screen and path item state (`EXECUTABLE` vs `WAITING` vs `BLOCKED`) make this explicit.

---

## Where is the ML?

1. **Optional semantic retrieval** — local `fastembed` (BGE) embeddings, capped at **5%** of recommendation weight
2. **Optional grounded LLM** — natural-language explanations only

Core diagnosis, gaps, scoring, eligibility, and adaptation are **deterministic**.

---

## What does BGE do?

When `PATHFINDER_SEMANTIC_ENABLED=true`, resource text is embedded locally. Query–resource similarity adds a **small bounded signal** to ranking — not a black-box reranker. Disabling semantic mode leaves deterministic retrieval intact.

---

## Why is semantic relevance bounded?

So semantic similarity cannot override prerequisite logic, gap priority, or eligibility. The engine stays auditable; ML assists tie-breaking, not authority.

---

## Where is the LLM?

Optional **Grounded AI** and **Ask PathFinder** call `PATHFINDER_AI_API_KEY` when configured. Default CI/demo uses **`stub`** provider — explanations fall back to deterministic copy.

---

## Can the LLM override the system?

**No.** The LLM cannot change proficiency, gaps, ranking, eligibility, sequencing, scoring, or adaptation. Grounded responses are validated against verified facts; malformed or unavailable AI shows a truthful fallback.

---

## What if AI fails?

UI shows **“Explanation is unavailable”** with deterministic context. Product actions (path, assessment, progress) continue. **Failure matrix case 6–7** documents this.

---

## What happens when evidence conflicts?

Fusion represents conflict (e.g., self-report vs assessment) with **CONFLICT** attainment where applicable. Gap engine uses fused levels; UI can show dual-signal competency rows.

---

## What happens after progress?

Submit progress → backend records evidence → competency model updates → if diagnosis changes, **Path V2** with diff. Completed items **freeze**. See `artifacts/adaptation-proof/progress-adaptation-*.png`.

---

## What happens after assessment?

Submit assessment → scored evidence → **Result** (before / evidence / after) → path consequence → **V1 → V2** if needed. See `artifacts/adaptation-proof/assessment-*.png`.

---

## Why did the path change?

Open **What changed** / **Why changed**: shows evidence, before/after state, action, **PathDiff**, preserved frozen work, timeline entry. No invented narrative — backend adaptation trace.

---

## What happened to completed work?

**Frozen anchors** on Path V2: completed steps stay visible and are not removed by adaptation. FLIP animation highlights ADDED / MOVED / REMOVED / BLOCKED only for non-frozen items.

---

## Why does another career get another path?

Different roles → different competency targets → different gaps → different resources. **Multi-career proof:** `artifacts/multi-career-proof/proof.json` — three unique path signatures for AI/ML, Cybersecurity, Backend.

---

## Why does another learner get another path?

Same role, different evidence → different gaps → different sequence. **Second-learner proof:** `artifacts/second-learner-proof/proof.json` — live API, not hardcoded UI.

---

## How do you prevent hallucinated resources?

Resources come from seeded ontology (`62` active resources). Recommendations reference known IDs. AI explanations are grounded in verified facts; invalid AI output is rejected or falls back.

---

## How do you prevent hallucinated skills?

Skills and roles are fixed in `data/` YAML. Intake resolves goals to **ontology roles** — the system does not invent skills at runtime.

---

## How do you know this isn't hardcoded?

| Proof | What it shows |
|-------|----------------|
| Intelligence benchmark **20/20** | Deterministic scenarios with expected outcomes |
| Multi-career proof | Different API paths per role |
| Second-learner proof | Different paths from different evidence payloads |
| Failure matrix **9/9** | Real network failures, real UI assertions |
| API smoke **19/19** | Live contract checks |

Run: `python scripts/intelligence_benchmark.py`, `scripts/second_learner_proof.mjs`, `scripts/multi_career_proof.mjs`.

---

## How do I run the demo?

```bash
cp .env.example .env.local && cp frontend/.env.example frontend/.env.local
docker compose up -d db
cd backend && pip install -r requirements.txt && alembic upgrade head && cd ..
python scripts/seed.py
cd backend && uvicorn app.main:app --port 8000
cd frontend && npm install && npm run build && PORT=3002 npm run start
```

Use **`next start`**, not `next dev`, for judging.

---

## What are known limitations?

- Semantic + LLM features require optional env configuration; stub mode is default
- Mobile path is a compact route compass; desktop is the full spatial composition
- No hosted public demo URL — judges run locally per README
- GitHub metadata (topics/description) requires manual setup if `gh` CLI is not authenticated

See `docs/FINAL_SUBMISSION_REPORT.md` for full gate checklist.
