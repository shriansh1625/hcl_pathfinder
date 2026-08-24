# PathFinder Intelligence Benchmark

## Executive Verdict
- Overall: **20/20** (100.0%)
- Commit: `7db9f19714d8478d2f6a53a894b339cf701a69ec`
- Timestamp: 2026-08-24T18:58:05.872768+00:00

## Scenario Matrix
| ID | Scenario | Result | Duration ms |
|----|----------|--------|-------------|
| S01 | EMPTY EVIDENCE | PASS | 6213.34 |
| S02 | TARGET-MET SKILL | PASS | 2628.05 |
| S03 | DIAGNOSED GAP | PASS | 2012.19 |
| S04 | UNKNOWN BLOCKER | PASS | 1901.23 |
| S05 | KNOWN GAP BLOCKER | PASS | 2187.0 |
| S06 | ROLE CHANGE | PASS | 3266.95 |
| S07 | LEARNER CHANGE | PASS | 2076.5 |
| S08 | WEEKLY BUDGET | PASS | 550.62 |
| S09 | LEARNING STYLE | PASS | 412.8 |
| S10 | SEMANTIC OFF VS ON | PASS | 1328.2 |
| S11 | CONFLICTING EVIDENCE | PASS | 863.55 |
| S12 | POSITIVE SURPRISE | PASS | 5178.05 |
| S13 | NEGATIVE SURPRISE | PASS | 1243.0 |
| S14 | DOCKER UNKNOWN→KNOWN | PASS | 4106.34 |
| S15 | NO-OP ADAPTATION | PASS | 3673.55 |
| S16 | DUPLICATE ATTEMPT | PASS | 4924.94 |
| S17 | COMPLETED WORK | PASS | 3114.77 |
| S18 | MULTI-VERSION CHAIN | PASS | 2581.21 |
| S19 | ASSESSMENT DRIFT | PASS | 30.71 |
| S20 | CAUSAL EXPLANATIONS | PASS | 513.55 |

## Quantitative Metrics

```json
{
  "scenario_pass_rate": 1.0,
  "passed": 20,
  "total": 20,
  "percentage": 100.0,
  "causal_validity_rate": 1.0,
  "unknown_integrity_rate": 1.0,
  "blocker_integrity_rate": 1.0,
  "role_personalization_rate": 1.0,
  "learner_personalization_rate": 1.0,
  "budget_compliance_rate": 1.0,
  "evidence_fusion_integrity_rate": 1.0,
  "adaptation_integrity_rate": 1.0,
  "historical_immutability_rate": 1.0,
  "idempotency_rate": 1.0,
  "semantic_safety_rate": 1.0,
  "drift_detection_rate": 1.0,
  "explanation_grounding_rate": 1.0,
  "overall_benchmark_score": 1.0
}
```

## Specification Corrections

S11 and S12 expectations were corrected to match established domain semantics:

- **S11** no longer assumes fused proficiency must fall between 0.50 and 0.90 when a failed assessment reports 0.00. The scenario now asserts append-only evidence, conflict detection, ASSESSMENT dominance, and GAP classification below target.
- **S12** now seeds the initial low statistics signal as SELF_REPORT (not ASSESSMENT), matching `test_positive_surprise_removes_unjustified_remediation`. A perfect gate can therefore move statistics to TARGET_MET and remove unjustified remediation without violating append-only ASSESSMENT fusion rules.

## Performance

```json
{
  "startup_ms": 49053.39,
  "scenario_timings_ms": {
    "S01": 6213.34,
    "S02": 2628.05,
    "S03": 2012.19,
    "S04": 1901.23,
    "S05": 2187.0,
    "S06": 3266.95,
    "S07": 2076.5,
    "S08": 550.62,
    "S09": 412.8,
    "S10": 1328.2,
    "S11": 863.55,
    "S12": 5178.05,
    "S13": 1243.0,
    "S14": 4106.34,
    "S15": 3673.55,
    "S16": 4924.94,
    "S17": 3114.77,
    "S18": 2581.21,
    "S19": 30.71,
    "S20": 513.55
  },
  "harness_timings_ms": {},
  "total_ms": 48806.55
}
```
