# PathFinder architecture

Slice 0 is the data foundation. Slice 1 added the diagnostic gap engine. Slice 1.1 separates evidence, attainment, blocking, and immediate action. Retrieval, sequencing, and UI are still future slices.

## Product loop (future)

```
Learner profile / resume
        → skill extraction (AI, later)
        → learner skill model (evidence fusion)
        → target career competency graph
        → skill gap engine
        → resource retrieval
        → prerequisite-aware sequencer
        → personalized path
        → learn / assess / feedback
        → update skill model
        → adapt remaining path
```

The core domain object is the **learner-to-career gap**, not a course list.

## Layers

| Layer | What it is | Status |
|---|---|---|
| **Data** | YAML ontology + Postgres runtime | Slice 0 |
| **Domain logic** | Evidence fusion + gap engine + action classes | Slice 1.1 |
| **AI/ML** | Resume extract, embeddings, explanation polish | Not started. No LLM. |
| **UI** | Diagnostic → skill map → roadmap → prove-it | Next.js boots only |

## Runtime shape

Modular monolith:

- `frontend/` — Next.js
- `backend/app/api` — HTTP
- `backend/app/models` — SQLAlchemy
- `backend/app/schemas` — Pydantic contracts (not raw ORM leakage)
- `backend/app/ontology` — YAML load + validation
- `backend/app/services/profiling` — evidence ingest + fusion
- `backend/app/services/skill_graph` — role competencies + downstream impact
- `backend/app/services/gap_engine` — gap, priority, blocking, action classes, explanations
- `backend/app/services/retrieval|sequencing|adaptation` — empty until later slices
- `data/` — source of truth for skills, roles, edges, catalog, assessments

Path generate must not wait on an LLM. The LLM, when added, interprets and explains. Code will calculate gaps, rank, sequence, and version paths.

## Evidence vs claims

`skill_evidence` is append-only. `user_skills.proficiency` is nullable.

**No evidence ≠ zero.** Missing evidence is `UNKNOWN`.

See `docs/GAP_ENGINE.md` for fusion, attainment, gap priority, verification priority, blocking, and action classes.

SATISFIED / `target_met` requires `proficiency >= target`. Close is not met.

## Extension points (intentionally unused)

- Embeddings: add a later `resource_embeddings` table keyed by `learning_resources.id`. Do not put vectors on the resource row in a way that forces pgvector today.
- LLM: `services/profiling` and `services/explanation` are the boundaries.
- Graph UI: React Flow is deferred until edges actually gate recommendations.

## What Slice 1.1 does not contain

Resource scoring, embeddings, sequencing, assessment runtime, adaptation, resume parsing, dashboards.
