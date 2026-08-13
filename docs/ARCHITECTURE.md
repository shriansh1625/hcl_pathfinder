# PathFinder architecture

Slice 0 documents the intended system. Only the data foundation exists today.

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

| Layer | What it is | Slice 0 |
|---|---|---|
| **Data** | YAML ontology + Postgres runtime | Implemented |
| **Domain logic** | Fusion, gap, retrieval, sequencing, adaptation | Schema + status semantics only |
| **AI/ML** | Resume extract, normalize, embeddings, explanation polish | Service folders only. No LLM. No pgvector |
| **UI** | Diagnostic → skill map → roadmap → prove-it → path changed | Next.js boots. No product screens |

## Runtime shape

Modular monolith:

- `frontend/` — Next.js
- `backend/app/api` — HTTP
- `backend/app/models` — SQLAlchemy
- `backend/app/schemas` — Pydantic contracts (not raw ORM leakage)
- `backend/app/ontology` — YAML load + validation
- `backend/app/services/*` — empty packages for later engines
- `data/` — source of truth for skills, roles, edges, catalog, assessments

Path generate must not wait on an LLM. The LLM, when added, interprets and explains. Code will calculate gaps, rank, sequence, and version paths.

## Evidence vs claims

`skill_evidence` is append-only. `user_skills.proficiency` is nullable.

**No evidence ≠ zero.** Missing evidence is `UNKNOWN`.

Reliability weights live in `data/ontology/reliability.yaml` (prototype assumptions, not immutable truths).

## Extension points (intentionally unused)

- Embeddings: add a later `resource_embeddings` table keyed by `learning_resources.id`. Do not put vectors on the resource row in a way that forces pgvector today.
- LLM: `services/profiling` and `services/explanation` are the boundaries.
- Graph UI: React Flow is deferred until edges actually gate recommendations.

## What Slice 0 does not contain

Recommendation scoring, sequencing, assessment runtime, adaptation engine, resume parsing, chatbot, onboarding, dashboards.
