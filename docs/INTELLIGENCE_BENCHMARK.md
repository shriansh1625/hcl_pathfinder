# PathFinder Intelligence Benchmark

## Executive Verdict
- Overall: **20/20** (100.0%)
- Commit: `35b5fc84e4dadaf5d0c7ce4760e964ef8bd26dad`
- Timestamp: 2026-08-29T22:02:55.275835+00:00

## Scenario Matrix
| ID | Scenario | Result | Duration ms |
|----|----------|--------|-------------|
| S01 | EMPTY EVIDENCE | PASS | 9243.26 |
| S02 | TARGET-MET SKILL | PASS | 1164.65 |
| S03 | DIAGNOSED GAP | PASS | 846.73 |
| S04 | UNKNOWN BLOCKER | PASS | 895.62 |
| S05 | KNOWN GAP BLOCKER | PASS | 799.02 |
| S06 | ROLE CHANGE | PASS | 1135.23 |
| S07 | LEARNER CHANGE | PASS | 1570.51 |
| S08 | WEEKLY BUDGET | PASS | 892.71 |
| S09 | LEARNING STYLE | PASS | 846.92 |
| S10 | SEMANTIC OFF VS ON | PASS | 773.72 |
| S11 | CONFLICTING EVIDENCE | PASS | 2224.26 |
| S12 | POSITIVE SURPRISE | PASS | 1663.2 |
| S13 | NEGATIVE SURPRISE | PASS | 1499.97 |
| S14 | DOCKER UNKNOWN→KNOWN | PASS | 1325.42 |
| S15 | NO-OP ADAPTATION | PASS | 957.37 |
| S16 | DUPLICATE ATTEMPT | PASS | 2236.98 |
| S17 | COMPLETED WORK | PASS | 1028.67 |
| S18 | MULTI-VERSION CHAIN | PASS | 1284.03 |
| S19 | ASSESSMENT DRIFT | PASS | 17.22 |
| S20 | CAUSAL EXPLANATIONS | PASS | 660.84 |

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
  "startup_ms": 31549.28,
  "scenario_timings_ms": {
    "S01": 9243.26,
    "S02": 1164.65,
    "S03": 846.73,
    "S04": 895.62,
    "S05": 799.02,
    "S06": 1135.23,
    "S07": 1570.51,
    "S08": 892.71,
    "S09": 846.92,
    "S10": 773.72,
    "S11": 2224.26,
    "S12": 1663.2,
    "S13": 1499.97,
    "S14": 1325.42,
    "S15": 957.37,
    "S16": 2236.98,
    "S17": 1028.67,
    "S18": 1284.03,
    "S19": 17.22,
    "S20": 660.84
  },
  "harness_timings_ms": {},
  "total_ms": 31066.33
}
```
