# Gap engine (Slice 1.1)

This is PathFinder's diagnostic layer. It answers: what do we know about the learner, what does the target career require, which gaps matter most, what is blocked, and what class of action comes next?

It does **not** retrieve resources, sequence a path, or call an LLM.

## Product distinctions

These are different objects. They must not collapse into one status.

| Concept | Question | Fields |
|---|---|---|
| Evidence state | Do we have a measurement? | `evidence_state`: UNKNOWN / KNOWN |
| Skill status | Legacy band vs target | `status` / `gap_status`: UNKNOWN / DEVELOPING / STRONG / GAP / SATISFIED |
| Target attainment | Has the role target been met? | `attainment`, `target_met` |
| Gap priority | What matters most for the career? | `gap_priority` (`priority` is an alias) |
| Blocking impact | What is gated, and by what? | `is_blocking`, `blocked`, `blockers` |
| Immediate action | What should the learner do next? | `action`, `action_priority`, `verification_priority` |

`gap_priority` is not `action_priority`. They may correlate. They are not the same ranking.

## 1. Learner model

Fused `user_skills` cache plus append-only `skill_evidence`. GET endpoints recompute fusion from evidence so results are deterministic.

## 2. Evidence model

Each record: skill, observed proficiency in `[0, 1]`, reliability, observer confidence, source, timestamp.

Sources: `SELF_REPORT`, `RESUME`, `PROJECT`, `ASSESSMENT`, `PROGRESS`, `FEEDBACK`.

Evidence is never overwritten. Conflicts remain inspectable.

## 3. Evidence fusion

For evidence `i = 1..n`:

```
recency_i = 0.5 ** (age_days_i / half_life_days)
weight_i  = reliability_i × confidence_i × recency_i
proficiency = Σ(observed_i × weight_i) / Σ(weight_i)
confidence  = 1 − exp(−k × Σ weight_i)
```

If `n = 0` or `Σ weight = 0`:

`proficiency = null`, `confidence = null`, `status = UNKNOWN`.

**No evidence is not zero.**

## 4. Reliability

Loaded from `data/ontology/reliability.yaml`. Prototype priors, not validated measurements:

| Source | Prior |
|---|---|
| ASSESSMENT | 0.90 |
| PROJECT | 0.80 |
| RESUME | 0.65 |
| FEEDBACK | 0.60 |
| PROGRESS | 0.60 |
| SELF_REPORT | 0.35 |

## 5. Recency

Exponential half-life, default **180 days** (`gap_engine.yaml`). A record at the half-life contributes half the weight of an otherwise identical fresh record.

## 6. Classification

`satisfied_max_gap` (0.15) is the **NEAR_TARGET band**. It does **not** mean the target is met.

A learner with `proficiency < target` has **not** reached the target.

| Condition | Evidence | Skill / gap_status | Attainment | target_met |
|---|---|---|---|---|
| No evidence | UNKNOWN | UNKNOWN | UNKNOWN | null |
| `proficiency >= target` | KNOWN | STRONG / SATISFIED | TARGET_MET | true |
| `0 < target − proficiency ≤ 0.15` | KNOWN | DEVELOPING | NEAR_TARGET | false |
| `target − proficiency ≥ 0.40` | KNOWN | GAP | GAP | false |
| otherwise below target | KNOWN | DEVELOPING | GAP | false |

Exact threshold hits are inclusive. Comparisons use a `1e-9` tolerance.

Without a target, proficiency ≥ 0.75 is STRONG, else DEVELOPING. Attainment is UNKNOWN until a role target exists.

## 7. Gap calculation

Only skills on the **selected role** are considered.

```
if UNKNOWN: gap = null
else: gap = max(target − proficiency, 0)
normalized_gap = gap / target
```

UNKNOWN never receives `gap = 0` or `gap = target`.

## 8. Gap priority

Not a resource score. Not an immediate-action score.

```
criticality = 1
  + hard_descendant_weight × |HARD role descendants|
  + soft_descendant_weight × |SOFT role descendants|

if UNKNOWN:
  gap_priority = 0
  verification_priority = importance × criticality × unknown_importance_weight
elif TARGET_MET:
  gap_priority = 0
  verification_priority = 0
else:
  conf_adj = min_confidence_adjustment + (1 − min) × fused_confidence
  gap_priority = gap × importance × criticality × conf_adj
  verification_priority = 0
```

`priority` on the API is `gap_priority`, kept for Slice 1 compatibility.

**Change from Slice 1:** UNKNOWN no longer shares the known-gap ranking channel. The previous UNKNOWN term moved to `verification_priority`. Known-gap weights were not retuned.

Defaults: hard weight 0.20, soft weight 0.05, unknown weight 0.45, min confidence adjustment 0.55.

## 9. Downstream impact

BFS on the competency graph:

- `HARD_PREREQUISITE` → blocking descendants (`is_blocking` if this unmet skill gates others)
- `SOFT_PREREQUISITE` → preparation descendants (do not block)
- `RELATED` → ignored

Label: HIGH if ≥3 HARD role descendants, MODERATE if ≥1, LOW if only SOFT, else NONE.

## 10. Incoming blockers

Direct incoming edges only. No invented blockers.

A prerequisite is **met** only when `target_met is true` for that skill.

| Edge | Unmet effect on the target skill |
|---|---|
| HARD | `blocked = true`, listed in `blockers` |
| SOFT | `preparation_needed = true`, listed in `preparation_skills` |
| RELATED | none |

NEAR_TARGET prerequisites are unmet. Close is not enough to unlock a HARD-gated skill.

## 11. Immediate action

Not a roadmap. Not a resource pick.

| Attainment / gate | Action | Meaning |
|---|---|---|
| UNKNOWN, not blocked | VERIFY | Collect evidence. Do not tell the learner to "learn" it. |
| Known GAP | REMEDIATE | Materially below target |
| NEAR_TARGET | REINFORCE | Close, but not met |
| TARGET_MET | ADVANCE | Target reached |
| Any skill with unmet HARD prereqs | REMEDIATE_BLOCKER | Do not start here; close the blocker first |

Action ranking uses **class tiers** so UNKNOWN cannot outrank a known remediable gap:

```
action_priority = TIER[action] + 0.05 × within
```

| Action | Tier |
|---|---|
| REMEDIATE | 3.0 |
| REINFORCE | 2.0 |
| VERIFY | 1.0 |
| REMEDIATE_BLOCKER | 0.5 |
| ADVANCE | 0.0 |

`within` is `gap_priority` except for VERIFY, which uses `verification_priority`. Tiers never cross.

## 12. Explanations

Templates filled from structured fields. No LLM.

## 13. Persona A investigation

Persona A / AI/ML Engineer:

| Skill | Evidence | Why the engine ranks it this way |
|---|---|---|
| Python 0.90 vs 0.85 | TARGET_MET | SATISFIED / ADVANCE. Does not block downstream. |
| Statistics 0.35 vs 0.80 | GAP | Large raw gap. Ontology edge to ML is **SOFT**, so it does not HARD-block ML. |
| ML fundamentals 0.55 vs 0.85 | GAP / DEVELOPING | Smaller raw gap than Statistics, but HARD-gates supervised / unsupervised / neural nets and further descendants. Higher **gap_priority** is graph-correct. |
| MLOps UNKNOWN | UNKNOWN | `gap_priority = 0`. Docker is an unmet HARD prereq, so action is `REMEDIATE_BLOCKER`, not VERIFY. Docker itself is VERIFY. |

Slice 1 reported ML fundamentals above Statistics. That ranking is **gap priority**, not "do this first because Statistics is wrong." Statistics does not HARD-block ML in the ontology (`SOFT_PREREQUISITE`, rationale: metrics "make more sense" with stats). Changing that edge to HARD would be a curriculum claim, not a bugfix. The edge was left as SOFT.

Immediate action for both Statistics and ML fundamentals is REMEDIATE (ML is not blocked). ML still ranks higher inside that class because of downstream criticality. Slice 2 can still choose to sequence Statistics first as SOFT preparation; that is sequencing, not this diagnostic.

## 14. Known limitations

- Reliability and half-life are unvalidated priors.
- Fusion is a weighted mean, not a Bayesian skill model.
- Incoming blockers are **direct** edges only. Transitive blocking appears on the next node.
- Catalog resources are unused by the Slice 1.1 gap engine on purpose. Slice 2 consumes GapProfile plus the catalog.
