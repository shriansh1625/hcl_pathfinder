# PathFinder data model

YAML under `data/` is the source of truth for ontology and catalog. Postgres holds runtime state plus a seeded copy of that ontology.

## ER diagram

```mermaid
erDiagram
  skills ||--o{ skill_relationships : source
  skills ||--o{ skill_relationships : target
  roles ||--o{ role_skills : includes
  skills ||--o{ role_skills : required_by
  learning_resources ||--o{ resource_skills : teaches
  skills ||--o{ resource_skills : covered
  learning_resources ||--o{ resource_prerequisites : requires
  skills ||--o{ resource_prerequisites : min_level
  skills ||--o{ assessments : primary
  assessments ||--o{ assessment_questions : contains
  skills ||--o{ assessment_questions : tests
  users ||--o| profiles : has
  roles ||--o{ profiles : target
  users ||--o{ skill_evidence : observes
  skills ||--o{ skill_evidence : about
  users ||--o{ user_skills : fused
  skills ||--o{ user_skills : state
  users ||--o{ learning_paths : owns
  roles ||--o{ learning_paths : toward
  learning_paths ||--o{ learning_paths : parent
  learning_paths ||--o{ path_items : contains
  learning_resources ||--o{ path_items : optional
  assessments ||--o{ path_items : optional
  users ||--o{ adaptation_events : records
  learning_paths ||--o{ adaptation_events : from
  learning_paths ||--o{ adaptation_events : to
```

## Ontology

### skills

Canonical concepts. Primary key is a stable UUIDv5 from `slug`. `canonical_name` is unique. Display names may change; slugs must not.

### skill_relationships

`source` is the earlier skill, `target` is the later skill.

| type | Meaning |
|---|---|
| `HARD_PREREQUISITE` | Required before the target. Graph must be acyclic. |
| `SOFT_PREREQUISITE` | Strongly recommended before, not a hard gate. |
| `RELATED` | Association only. Does not order a path. |

Skill-graph prerequisites are **not** the same as resource prerequisites.

### roles / role_skills

Five careers. `target_level` and `importance` are in `[0, 1]`. `required_status` is `CORE`, `ELECTIVE`, or `OPTIONAL`.

## Catalog

### learning_resources

Types: `course`, `project`, `lab`, `assessment`.

`url_status`: `verified` (audit confirmed the endpoint), `claimed` (URL present but unconfirmed: 403/404/bot-block/transient), `pending`, `unavailable` (no usable URL — do not invent links). Never call a 403/404 URL `verified`.

### resource_skills

Coverage of a skill and expected level delta (for later scoring).

### resource_prerequisites

Per-resource gates: skill + `min_level`. Separate from the competency graph.

## Assessments

`assessments` + `assessment_questions`. Questions reference a skill and a `concept_tag` so later adaptation can insert remediation for a weak concept. No assessment engine in Slice 0.

## Learner runtime

### users / profiles

Guest identity, target role, weekly hours, learning style, timeline.

### skill_evidence

Append-only observations: `SELF_REPORT`, `RESUME`, `PROJECT`, `ASSESSMENT`, `PROGRESS`, `FEEDBACK`. Never update a row; insert another.

Reliability is stored on the row and sourced from `data/ontology/reliability.yaml`.

### user_skills

Fused cache. `proficiency` and `confidence` are **NULL** when `status = UNKNOWN`. Missing evidence is not stored as 0.

Statuses: `UNKNOWN`, `DEVELOPING`, `STRONG`, `GAP`. Role-relative gap status (`SATISFIED` only when `target_met`, plus `NEAR_TARGET` attainment) is computed by the gap engine, not stored on this row.

Immediate action (`VERIFY` / `REMEDIATE` / `REINFORCE` / `ADVANCE` / `REMEDIATE_BLOCKER`) is also computed, not stored.

## Paths

### learning_paths

Versioned. `(user_id, version)` is unique. `parent_path_id` points at the superseded path. v1 remains after v2 is created.

### path_items

Ordered items with optional `resource_id` / `assessment_id`. `score_breakdown` JSON is the explainability payload (schema ready; not computed yet).

Example shape:

```json
{
  "skill_gap": 0.87,
  "role_importance": 0.92,
  "prerequisite_fit": 1.0,
  "difficulty_fit": 0.81,
  "duration_fit": 0.74,
  "style_fit": 0.90,
  "semantic_similarity": 0.83,
  "final_score": 0.86
}
```

### adaptation_events

Why a path changed: `from_path_id` → `to_path_id` plus `event_type` and `summary`. Engine not implemented.

## Constraints worth knowing

- HARD prerequisite self-edges are rejected.
- HARD prerequisite cycles fail seed.
- Target level, importance, coverage, and observed levels are in `[0, 1]`.
- Resource duration must be positive.
- Ontology IDs are deterministic UUIDv5 values so seed is idempotent.
