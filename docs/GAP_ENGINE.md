# Gap engine (Slice 1)

This is PathFinder's diagnostic layer. It answers: what do we know about the learner, what does the target career require, and which gaps matter most?

It does **not** retrieve resources, sequence a path, or call an LLM.

## 1. Learner model

Fused `user_skills` cache plus append-only `skill_evidence`. GET endpoints recompute fusion from evidence so results are deterministic.

Statuses: `UNKNOWN`, `DEVELOPING`, `STRONG`, `GAP` (learner skill vs optional target).

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

From `gap_engine.yaml`, chosen against CORE targets that cluster around 0.70–0.90:

| Condition | Skill status | Gap status |
|---|---|---|
| No evidence / null proficiency | UNKNOWN | UNKNOWN |
| `target - proficiency ≤ 0.15` | STRONG | SATISFIED |
| `target - proficiency ≥ 0.40` | GAP | GAP |

Exact threshold hits are inclusive. Comparisons use a 1e-9 tolerance so YAML floats such as `0.85 - 0.45` classify as GAP, not DEVELOPING.
| otherwise | DEVELOPING | DEVELOPING |

Without a target, proficiency ≥ 0.75 is STRONG, else DEVELOPING.

## 7. Gap calculation

Only skills on the **selected role** are considered.

```
if UNKNOWN: gap = null
else: gap = max(target − proficiency, 0)
normalized_gap = gap / target
```

## 8. Gap priority

Not a resource score.

```
criticality = 1
  + hard_descendant_weight × |HARD role descendants|
  + soft_descendant_weight × |SOFT role descendants|

if SATISFIED:
  priority = 0
elif UNKNOWN:
  priority = importance × criticality × unknown_importance_weight
else:
  conf_adj = min_confidence_adjustment + (1 − min) × fused_confidence
  priority = gap × importance × criticality × conf_adj
```

Defaults: hard weight 0.20, soft weight 0.05, unknown weight 0.45, min confidence adjustment 0.55.

## 9. Downstream impact

BFS on the competency graph:

- `HARD_PREREQUISITE` → blocking descendants
- `SOFT_PREREQUISITE` → preparation descendants (do not block)
- `RELATED` → ignored

Impact is scoped to skills required by the current role. A skill that gates many CORE descendants outranks a larger raw gap with no downstream effect.

## 10. Hard vs soft vs related

HARD can later block sequencing. SOFT raises priority only. RELATED never affects priority.

## 11. Explanations

Templates filled from structured fields (current, target, importance, downstream counts, conflict). No LLM.

## 12. Known limitations

- Reliability and half-life are unvalidated priors.
- Fusion is a weighted mean, not a Bayesian skill model.
- UNKNOWN CORE skills still receive a discovery priority so they surface, without pretending the learner failed.
- Catalog resources are unused in this slice on purpose.
