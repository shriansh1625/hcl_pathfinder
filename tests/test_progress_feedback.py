"""Progress feedback → evidence → fusion → adaptation.

Invariants: feedback never fabricates proficiency, skips record no evidence,
and reported levels flow through append_evidence with PROGRESS reliability.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text

from app.core.config import settings
from app.core.reliability import reliability_for
from app.core.enums import EvidenceSource
from app.db.session import SessionLocal
from app.main import app
from app.models import PathItem
from app.services.progress.feedback import ProgressOutcome, _ITEM_STATUS

client = TestClient(app)
AIML = "ai-ml-engineer"


def postgres_available() -> bool:
    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not postgres_available(),
    reason="PostgreSQL is not reachable at DATABASE_URL",
)


def _learner(name: str) -> str:
    response = client.post("/v1/learners", json={"display_name": name})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _evidence(learner_id: str, skill: str, level: float, source: str = "ASSESSMENT"):
    response = client.post(
        f"/v1/learners/{learner_id}/evidence",
        json={
            "skill": skill,
            "source": source,
            "observed_level": level,
            "confidence": 0.85,
        },
    )
    assert response.status_code == 200, response.text


def _path(learner_id: str, hours: float = 10) -> dict:
    response = client.post(
        f"/v1/learners/{learner_id}/paths",
        json={"role": AIML, "weekly_hours": hours, "learning_style": "MIXED"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _feedback(learner_id: str, path_id: str, position: int, **body):
    return client.post(
        f"/v1/learners/{learner_id}/progress",
        json={"path_id": path_id, "position": position, **body},
    )


def _first_executable(path: dict) -> dict:
    for item in path["items"]:
        if item["executable"] and item["kind"] == "EXECUTABLE":
            return item
    raise AssertionError("no executable item on path")


def _seeded_learner(name: str) -> tuple[str, dict]:
    learner_id = _learner(name)
    _evidence(learner_id, "python", 0.9)
    _evidence(learner_id, "statistics", 0.35)
    _evidence(learner_id, "ml_fundamentals", 0.55)
    return learner_id, _path(learner_id)


def test_every_outcome_maps_to_a_path_item_status():
    assert set(_ITEM_STATUS) == {item.value for item in ProgressOutcome}
    assert _ITEM_STATUS[ProgressOutcome.COMPLETED.value] == "COMPLETED"
    assert _ITEM_STATUS[ProgressOutcome.SKIPPED.value] == "SKIPPED"
    assert _ITEM_STATUS[ProgressOutcome.STRUGGLED.value] == "IN_PROGRESS"


@requires_db
def test_unknown_outcome_is_rejected():
    learner_id, path = _seeded_learner("progress-bad-outcome")
    item = _first_executable(path)
    response = _feedback(learner_id, path["id"], item["position"], outcome="NOPE")
    assert response.status_code == 422


@requires_db
def test_missing_item_is_a_404():
    learner_id, path = _seeded_learner("progress-missing-item")
    response = _feedback(learner_id, path["id"], 999, outcome="SKIPPED")
    assert response.status_code == 404


@requires_db
def test_skip_records_no_evidence():
    learner_id, path = _seeded_learner("progress-skip")
    item = _first_executable(path)

    before = client.get(f"/v1/learners/{learner_id}/skills").json()
    response = _feedback(learner_id, path["id"], item["position"], outcome="SKIPPED")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["evidence_recorded"] is False
    assert body["observed_level"] is None
    assert body["item_status"] == "SKIPPED"

    after = client.get(f"/v1/learners/{learner_id}/skills").json()
    counts_before = {row["skill"]: row["evidence_count"] for row in before}
    counts_after = {row["skill"]: row["evidence_count"] for row in after}
    assert counts_after == counts_before


@requires_db
def test_completion_without_a_level_records_no_evidence():
    learner_id, path = _seeded_learner("progress-no-level")
    item = _first_executable(path)

    response = _feedback(learner_id, path["id"], item["position"], outcome="COMPLETED")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["evidence_recorded"] is False
    assert body["observed_level"] is None
    assert body["item_status"] == "COMPLETED"


@requires_db
def test_reported_level_becomes_progress_evidence_with_canonical_reliability():
    learner_id, path = _seeded_learner("progress-evidence")
    item = _first_executable(path)
    skill = item["target_skill"]

    response = _feedback(
        learner_id,
        path["id"],
        item["position"],
        outcome="COMPLETED",
        self_reported_level=0.9,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["evidence_recorded"] is True
    assert body["observed_level"] == 0.9
    assert body["target_skill"] == skill

    fused = {row["skill"]: row for row in client.get(f"/v1/learners/{learner_id}/skills").json()}
    assert fused[skill]["evidence_count"] >= 1

    evidence = client.get(
        f"/v1/learners/{learner_id}/evidence",
        params={"skill": skill},
    ).json()
    progress_rows = [row for row in evidence if row["source"] == "PROGRESS"]
    assert progress_rows
    assert progress_rows[-1]["reliability"] == reliability_for(EvidenceSource.PROGRESS)
    assert progress_rows[-1]["reliability"] == pytest.approx(0.60)


@requires_db
def test_progress_evidence_goes_through_fusion_not_direct_proficiency_write():
    learner_id, path = _seeded_learner("progress-fusion")
    item = _first_executable(path)
    skill = item["target_skill"]

    before = client.get(f"/v1/learners/{learner_id}/skills").json()
    before_prof = next(row["proficiency"] for row in before if row["skill"] == skill)

    response = _feedback(
        learner_id,
        path["id"],
        item["position"],
        outcome="COMPLETED",
        self_reported_level=0.9,
    )
    assert response.status_code == 200, response.text

    evidence = client.get(
        f"/v1/learners/{learner_id}/evidence",
        params={"skill": skill},
    ).json()
    assert any(row["source"] == "PROGRESS" for row in evidence)

    after = client.get(f"/v1/learners/{learner_id}/skills").json()
    after_prof = next(row["proficiency"] for row in after if row["skill"] == skill)
    assert after_prof is not None
    if before_prof is not None:
        assert after_prof >= before_prof


@requires_db
def test_self_reported_level_without_target_skill_context_is_rejected():
    learner_id, path = _seeded_learner("progress-no-skill")
    item = _first_executable(path)

    session = SessionLocal()
    try:
        row = session.scalar(
            select(PathItem).where(
                PathItem.learning_path_id == uuid.UUID(path["id"]),
                PathItem.position == item["position"],
            )
        )
        assert row is not None
        row.explanation_metadata = {
            "resource_slug": item.get("resource_slug") or item.get("resource") or "",
        }
        session.commit()
    finally:
        session.close()

    response = _feedback(
        learner_id,
        path["id"],
        item["position"],
        outcome="COMPLETED",
        self_reported_level=0.8,
    )
    assert response.status_code == 422


@requires_db
def test_invalid_skill_slug_on_path_item_is_rejected():
    learner_id, path = _seeded_learner("progress-bad-skill")
    item = _first_executable(path)

    session = SessionLocal()
    try:
        row = session.scalar(
            select(PathItem).where(
                PathItem.learning_path_id == uuid.UUID(path["id"]),
                PathItem.position == item["position"],
            )
        )
        assert row is not None
        row.explanation_metadata = {
            "target_skill": "not-a-real-skill",
            "resource_slug": item.get("resource_slug") or "",
        }
        session.commit()
    finally:
        session.close()

    response = _feedback(
        learner_id,
        path["id"],
        item["position"],
        outcome="COMPLETED",
        self_reported_level=0.8,
    )
    assert response.status_code == 422


@requires_db
def test_missing_path_context_is_rejected():
    learner_id, path = _seeded_learner("progress-no-context")
    item = _first_executable(path)

    session = SessionLocal()
    try:
        row = session.scalar(
            select(PathItem).where(
                PathItem.learning_path_id == uuid.UUID(path["id"]),
                PathItem.position == item["position"],
            )
        )
        assert row is not None
        row.explanation_metadata = {}
        session.commit()
    finally:
        session.close()

    response = _feedback(learner_id, path["id"], item["position"], outcome="SKIPPED")
    assert response.status_code == 422


@requires_db
def test_struggle_can_trigger_adaptation_when_state_changes():
    learner_id, path = _seeded_learner("progress-struggle")
    item = _first_executable(path)

    response = _feedback(
        learner_id,
        path["id"],
        item["position"],
        outcome="STRUGGLED",
        self_reported_level=0.15,
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["adaptation"] in {"CREATED", "NO_ADAPTATION_REQUIRED"}
    assert body["summary"]
    if body["adaptation"] == "CREATED":
        assert body["new_path_id"] is not None
        assert body["diff"] is not None
        paths = client.get(f"/v1/learners/{learner_id}/paths").json()
        active = [row for row in paths if row["status"] == "ACTIVE"]
        assert len(active) == 1
        assert active[0]["version"] == 2
        assert active[0]["id"] == body["new_path_id"]


@requires_db
def test_feedback_on_a_superseded_path_is_rejected():
    learner_id, path = _seeded_learner("progress-superseded")
    item = _first_executable(path)

    first = _feedback(
        learner_id,
        path["id"],
        item["position"],
        outcome="STRUGGLED",
        self_reported_level=0.1,
    )
    assert first.status_code == 200, first.text
    if first.json()["adaptation"] != "CREATED":
        pytest.skip("no adaptation was required, so no path was superseded")

    again = _feedback(learner_id, path["id"], item["position"], outcome="SKIPPED")
    assert again.status_code == 422


@requires_db
def test_adaptation_event_records_the_feedback_trigger():
    learner_id, path = _seeded_learner("progress-trigger")
    item = _first_executable(path)

    response = _feedback(
        learner_id,
        path["id"],
        item["position"],
        outcome="STRUGGLED",
        self_reported_level=0.1,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    if body["adaptation"] != "CREATED":
        pytest.skip("no adaptation was required")

    diff = client.get(
        f"/v1/learners/{learner_id}/paths/{body['new_path_id']}/diff"
    ).json()
    assert diff["trigger_type"] == "PROGRESS_FEEDBACK"


@requires_db
def test_duplicate_progress_on_active_path_appends_evidence():
    """Evidence is append-only; there is no idempotency key on progress feedback."""
    learner_id, path = _seeded_learner("progress-duplicate")
    item = _first_executable(path)
    skill = item["target_skill"]

    first = _feedback(
        learner_id,
        path["id"],
        item["position"],
        outcome="COMPLETED",
        self_reported_level=0.75,
    )
    assert first.status_code == 200, first.text
    if first.json()["adaptation"] == "CREATED":
        pytest.skip("first feedback superseded the path; duplicate must target the active path id")

    second = _feedback(
        learner_id,
        path["id"],
        item["position"],
        outcome="COMPLETED",
        self_reported_level=0.75,
    )
    assert second.status_code == 200, second.text

    evidence = client.get(
        f"/v1/learners/{learner_id}/evidence",
        params={"skill": skill},
    ).json()
    progress_rows = [row for row in evidence if row["source"] == "PROGRESS"]
    assert len(progress_rows) >= 2


@requires_db
def test_v1_remains_immutable_after_progress_adaptation():
    learner_id, path = _seeded_learner("progress-v1-immutable")
    item = _first_executable(path)
    v1_id = path["id"]

    response = _feedback(
        learner_id,
        path["id"],
        item["position"],
        outcome="STRUGGLED",
        self_reported_level=0.1,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    if body["adaptation"] != "CREATED":
        pytest.skip("adaptation did not create V2")

    v1 = client.get(f"/v1/learners/{learner_id}/paths/{v1_id}").json()
    assert v1["status"] == "SUPERSEDED"
    assert v1["version"] == 1


def _summary(outcome: str, adaptation: str, diff=None) -> str:
    from app.services.adaptation.diff import PathDiff
    from app.services.progress.feedback import ProgressOutcome, _summary as build

    return build(ProgressOutcome(outcome), adaptation, diff or PathDiff())


def test_skip_that_changes_nothing_says_the_step_is_still_required():
    text = _summary("SKIPPED", "NO_ADAPTATION_REQUIRED")
    assert "still open" in text
    assert "does not remove the requirement" in text


def test_replan_with_an_empty_diff_does_not_report_zeroes():
    text = _summary("SKIPPED", "CREATED")
    assert "0 step(s)" not in text
    assert "re-planned back onto your path" in text

    text = _summary("COMPLETED", "CREATED")
    assert "0 step(s)" not in text
    assert "unchanged" in text


def test_material_replan_reports_the_counts():
    from app.services.adaptation.diff import DiffEntry, PathDiff

    diff = PathDiff(
        added=(DiffEntry(key="resource:a", skill="s", title="A", reason="r"),),
        moved=(DiffEntry(key="resource:b", skill="s", title="B", reason="r"),),
    )
    text = _summary("STRUGGLED", "CREATED", diff)
    assert "1 step(s) added" in text
    assert "1 moved" in text


def test_no_active_path_is_reported_plainly():
    assert "No active path" in _summary("COMPLETED", "NO_ACTIVE_PATH")
