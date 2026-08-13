# Resource intelligence (Slice 2)

PathFinder turns a **career gap profile** into a **personalized learning path**.

Stages are separate:

1. **Retrieval** — which catalog resources cover role skills
2. **Recommendation** — which of those fit this learner
3. **Sequencing** — in what order, under a weekly budget

No LLM. No embeddings required. No assessment runtime.

## Retrieval

Structured only. A resource is a candidate if it is active and covers a role skill at `coverage_strength >= 0.35`.

`SemanticRetriever` scores catalog relevance with local embeddings (`BAAI/bge-small-en-v1.5` via `fastembed`) against a deterministic gap/role query. Semantic relevance is an embedding-based catalog relevance signal with a **5% score contribution**. It is **not decision authority**. If embeddings are unavailable, the configured `fallback_similarity` (`0.50`) is used.

## Eligibility

Resource prerequisites are evaluated against fused proficiency:

| Evidence | State |
|---|---|
| no proficiency | UNKNOWN |
| proficiency < min_level | UNSATISFIED |
| proficiency ≥ min_level | SATISFIED |

| Mix of checks | Resource |
|---|---|
| any UNSATISFIED | BLOCKED_BY_KNOWN_GAP |
| else any UNKNOWN | BLOCKED_BY_UNKNOWN |
| else | ELIGIBLE |

UNKNOWN is not treated as mastery and is not treated as a failed score.

## Scoring

Each component is in `[0, 1]`. Final score is a convex combination:

```
skill_gap_fit        0.30
role_importance      0.20
prerequisite_fit     0.15
difficulty_fit       0.10
duration_fit         0.10
learning_style_fit   0.10
semantic_similarity  0.05
```

- **skill_gap_fit**: `max(coverage × action_priority_norm × attainment_boost)`
- **role_importance**: `max(coverage × role skill importance)`
- **prerequisite_fit**: 1.0 / 0.45 / 0.10 for eligible / unknown / unsatisfied
- **difficulty_fit**: `1 − |(difficulty−1)/4 − learner_level|`
- **duration_fit**: 1.0 if duration ≤ weekly hours, then 0.70 / 0.40 / 0.20 bands
- **learning_style_fit**: VIDEO/READING/HANDS_ON/PROJECT/MIXED vs resource modes
- **semantic_similarity**: local embedding cosine similarity against a deterministic gap/role query (5% weight; fallback `0.50` if unavailable)

Learning style cannot outrank gap + role weights (0.10 vs 0.50).

## Interventions

Mapped from gap action + resource type: VERIFY, FOUNDATION, REMEDIATION, PRACTICE, APPLICATION, ASSESSMENT, ADVANCEMENT.

Path selection uses waves, not raw diagnostic `action_priority`:

1. unblocked remediations
2. skills whose blockers were just covered
3. reinforcement
4. verification
5. still-blocked skills

After each selected resource, waves are recomputed so Python remediation is followed by ML, not by a queue of UNKNOWN verifies. `BLOCKED_BY_KNOWN_GAP` resources are classified, not deleted, so they can appear later in the path.

## Causality (Slice 2.1)

A high score is not enough to enter the path.

Selectable skills for **learning resources** are diagnosed gaps with evidence (`REMEDIATE` / `REINFORCE` / `REMEDIATE_BLOCKER`). UNKNOWN skills are not turned into courses.

## Verification gates (Slice 2.2)

UNKNOWN means "we need evidence", not "learner is weak".

If a role-relevant skill is UNKNOWN, the system may emit a `VerificationGate` (`intervention_type = VERIFY`). Gates do not execute assessments and do not bind a catalog URL.

- If the role has no diagnosed gaps, the path is verification-first (role competencies ranked by existing `verification_priority` and HARD-graph foundation order).
- If diagnosed gaps exist, gates are limited to UNKNOWN skills that HARD-block a focal gap or an otherwise selected resource.

## Path integrity

Candidates may be `ELIGIBLE`, `BLOCKED_BY_UNKNOWN`, or `BLOCKED_BY_KNOWN_GAP`. Persisted path items distinguish:

| kind | executable |
|---|---|
| `EXECUTABLE` | yes — `ELIGIBLE` learning resource |
| `VERIFICATION_GATE` | yes — next action is verify, not a course |
| `WAITING_FOR_VERIFICATION` | no |
| `WAITING_FOR_REMEDIATION` | no |

A blocked candidate can remain in the planning graph. It must not appear as a ready-to-start course.

Unknown role skills are **not** path-filler courses. A learner with no diagnosed gaps for the selected role receives verification gates rather than an empty path or a catalog tour.


Journey complements (lab / project / assessment) are added only for an already-selected skill, not as catalog filler.

Every path item stores `PathCause`:

- `why_selected`
- `why_this_skill`
- `why_this_position`
- `why_this_intervention`
- `why_this_resource`
- `why_not_earlier`

Path quality is a categorical report (`PREREQUISITES_VALID`, …), not a vanity score.

See `docs/AI_ARCHITECTURE.md` and `docs/CATALOG_AUDIT.md`.

## Sequencing

Not sort-by-score.

Hard edges come from HARD skill relationships and from resource prerequisites covered by another selected resource. Soft edges influence tie-breaks only.

Kahn topological order, then leftover slugs by score.

## Weekly packing

Place resources in sequence order. If the next item does not fit remaining hours in the week, start the next week. Items longer than `weekly_hours` occupy `ceil(duration / weekly_hours)` weeks alone.

## Paths

Versioned `learning_paths` + `path_items` with full `score_breakdown` JSON. v1 only in this slice (no adaptation).
