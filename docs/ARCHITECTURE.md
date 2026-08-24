# PathFinder architecture

Slice 0 is the data foundation. Slice 1/1.1 diagnose the career gap. Slice 2 retrieves, scores, and sequences a personalized path. Assessment runtime, adaptation, and UI are still future slices.

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
| **Domain logic** | Gap engine + retrieval + scoring + sequencing | Slice 2 |
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
- `backend/app/services/retrieval` — structured candidate retrieval; optional semantic stub
- `backend/app/services/recommendation` — eligibility, scoring, explanations
- `backend/app/services/sequencing` — dependency order + weekly packing
- `backend/app/services/path` — path generation, persistence, causality metadata, quality checks
- `backend/app/services/adaptation` — empty until later slices
- `data/` — source of truth for skills, roles, edges, catalog, assessments

Path generate must not wait on an LLM. The LLM, when added, interprets and explains. Code will calculate gaps, rank, sequence, and version paths.

## Evidence vs claims

`skill_evidence` is append-only. `user_skills.proficiency` is nullable.

**No evidence ≠ zero.** Missing evidence is `UNKNOWN`.

### Progress feedback (Slice 5.1 selective port)

Learner progress on a path step is **evidence**, not direct proficiency truth.

```
learning activity / outcome on path item
        → PROGRESS evidence (when learner reports a level)
        → append_evidence()
        → evidence fusion
        → gap profile
        → adapt_path() when material state changes
        → Path V2 (optional)
```

- Source: `PROGRESS` with reliability from `data/ontology/reliability.yaml` (currently 0.60).
- Skips record **no** evidence — declining work is not an ability observation.
- The server never invents a level the learner did not supply.
- Feedback is anchored to an active path item with catalog-backed `target_skill` / `resource_slug` metadata.
- Adaptation uses the existing engine; completed work and V1 immutability are preserved.

**Known constraint — idempotency:** Progress feedback is append-only. There is no idempotency key today, so a client retry on the same active path can record duplicate `PROGRESS` evidence rows. That is deliberate for auditability but may be tightened later (e.g. idempotency key or dedupe window). If the first feedback supersedes the path (V2), further calls to the old `path_id` are rejected with 422.

See `docs/GAP_ENGINE.md`, `docs/RECOMMENDATION.md`, and `docs/AI_ARCHITECTURE.md`.

## Extension points (intentionally unused)

- Embeddings: add a later `resource_embeddings` table keyed by `learning_resources.id`. Do not put vectors on the resource row in a way that forces pgvector today.
- LLM: `services/profiling` and `services/explanation` are the boundaries.
- Graph UI: React Flow is deferred until edges actually gate recommendations.

## What Slice 2 does not contain

Assessment runtime, adaptation, embeddings backend, resume parsing, LLM, dashboards.
