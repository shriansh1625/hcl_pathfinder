# PathFinder Intelligence Benchmark

## Executive Verdict
- Overall: **20/20** (100.0%)
- Commit: `ddea911c4ace61c810f91025fdc6df4558eb0b5b`
- Timestamp: 2026-08-30T18:01:35.505887+00:00

## Scenario Matrix
| ID | Scenario | Result | Duration ms |
|----|----------|--------|-------------|
| S01 | EMPTY EVIDENCE | PASS | 5230.52 |
| S02 | TARGET-MET SKILL | PASS | 757.84 |
| S03 | DIAGNOSED GAP | PASS | 687.34 |
| S04 | UNKNOWN BLOCKER | PASS | 772.58 |
| S05 | KNOWN GAP BLOCKER | PASS | 689.05 |
| S06 | ROLE CHANGE | PASS | 1026.89 |
| S07 | LEARNER CHANGE | PASS | 1039.16 |
| S08 | WEEKLY BUDGET | PASS | 494.51 |
| S09 | LEARNING STYLE | PASS | 558.4 |
| S10 | SEMANTIC OFF VS ON | PASS | 585.06 |
| S11 | CONFLICTING EVIDENCE | PASS | 446.37 |
| S12 | POSITIVE SURPRISE | PASS | 1769.02 |
| S13 | NEGATIVE SURPRISE | PASS | 897.26 |
| S14 | DOCKER UNKNOWN→KNOWN | PASS | 1279.79 |
| S15 | NO-OP ADAPTATION | PASS | 886.11 |
| S16 | DUPLICATE ATTEMPT | PASS | 1387.95 |
| S17 | COMPLETED WORK | PASS | 1409.52 |
| S18 | MULTI-VERSION CHAIN | PASS | 1739.26 |
| S19 | ASSESSMENT DRIFT | PASS | 12.94 |
| S20 | CAUSAL EXPLANATIONS | PASS | 480.01 |

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
  "startup_ms": 22564.0,
  "scenario_timings_ms": {
    "S01": 5230.52,
    "S02": 757.84,
    "S03": 687.34,
    "S04": 772.58,
    "S05": 689.05,
    "S06": 1026.89,
    "S07": 1039.16,
    "S08": 494.51,
    "S09": 558.4,
    "S10": 585.06,
    "S11": 446.37,
    "S12": 1769.02,
    "S13": 897.26,
    "S14": 1279.79,
    "S15": 886.11,
    "S16": 1387.95,
    "S17": 1409.52,
    "S18": 1739.26,
    "S19": 12.94,
    "S20": 480.01
  },
  "harness_timings_ms": {},
  "total_ms": 22149.58
}
```
