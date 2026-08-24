"""Slice 6.0 intelligence benchmark tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from app.core.config import settings  # noqa: E402

from intelligence_benchmark import (  # noqa: E402
    ARTIFACT_PATH,
    DOC_PATH,
    SCENARIOS,
    compute_metrics,
    postgres_available,
    run_benchmark,
)


def test_benchmark_module_defines_twenty_scenarios():
    assert len(SCENARIOS) == 20
    assert {sid for sid, _, _ in SCENARIOS} == {f"S{i:02d}" for i in range(1, 21)}


@pytest.mark.skipif(not postgres_available(), reason="PostgreSQL required")
def test_intelligence_benchmark_runs_and_writes_artifacts():
    payload = run_benchmark()
    assert ARTIFACT_PATH.exists()
    assert DOC_PATH.exists()
    body = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    assert body["version"] == "6.0"
    assert len(body["scenarios"]) == 20
    assert body["metrics"]["total"] == 20
    assert "overall_benchmark_score" in body["metrics"]
    assert payload["metrics"]["passed"] + len(payload["failures"]) + len(payload["inconclusive"]) == 20
    s11 = next(item for item in body["scenarios"] if item["id"] == "S11")
    s12 = next(item for item in body["scenarios"] if item["id"] == "S12")
    assert s11["result"] == "PASS", s11
    assert s12["result"] == "PASS", s12
    assert body["metrics"]["passed"] == 20
    assert not body["inconclusive"]


def test_compute_metrics_does_not_hide_failures():
    from intelligence_benchmark import ScenarioResult

    results = [
        ScenarioResult("S01", "a", "PASS"),
        ScenarioResult("S02", "b", "FAIL"),
    ]
    metrics = compute_metrics(results)
    assert metrics["passed"] == 1
    assert metrics["total"] == 2
    assert metrics["overall_benchmark_score"] == 0.5
