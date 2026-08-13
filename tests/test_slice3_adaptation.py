"""Slice 3 adaptation tests: V1 → evidence → V2 with completed-work freeze,
position-collision safety, diff, no-op, rollback, and determinism."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models import LearningPath, PathItem
from app.ontology.load import load_ontology
from app.services.adaptation.engine import PathItemSnapshot, _assign_positions, V2Item

client = TestClient(app)
BUNDLE = load_ontology()
SPECS = {item.slug: item for item in BUNDLE.assessments}


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

AIML = "ai-ml-engineer"


def _learner(name: str) -> str:
    response = client.post("/v1/learners", json={"display_name": name})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _evidence(learner_id: str, skill: str, source: str, level: float, confidence: float = 0.85):
    response = client.post(
        f"/v1/learners/{learner_id}/evidence",
        json={
            "skill": skill,
            "source": source,
            "observed_level": level,
            "confidence": confidence,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _path(learner_id: str, role: str = AIML, hours: float = 10) -> dict:
    response = client.post(
        f"/v1/learners/{learner_id}/paths",
        json={"role": role, "weekly_hours": hours, "learning_style": "MIXED"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _submit(learner_id: str, slug: str, answers: list[int], attempt_id: str | None = None):
    body: dict = {"answers": answers}
    if attempt_id:
        body["attempt_id"] = attempt_id
    return client.post(f"/v1/learners/{learner_id}/assessments/{slug}/attempts", json=body)


def _correct(slug: str) -> list[int]:
    return [q.correct_index for q in SPECS[slug].questions]


def _wrong(slug: str) -> list[int]:
    return [(q.correct_index + 1) % len(q.choices) for q in SPECS[slug].questions]


def _paths(learner_id: str) -> list[dict]:
    response = client.get(f"/v1/learners/{learner_id}/paths")
    assert response.status_code == 200, response.text
    return response.json()


def _first_executable(path: dict) -> dict:
    for item in path["items"]:
        if item["executable"] and item["kind"] == "EXECUTABLE":
            return item
    raise AssertionError("no executable resource item in path")


def _db_path_items(path_id: str) -> list[tuple]:
    session = SessionLocal()
    try:
        rows = session.scalars(
            select(PathItem)
            .where(PathItem.learning_path_id == uuid.UUID(path_id))
            .order_by(PathItem.position)
        ).all()
        return [
            (row.position, row.week_index, row.status, row.item_type, dict(row.explanation_metadata or {}))
            for row in rows
        ]
    finally:
        session.close()


# ---------------------------------------------------------------- pure: position collision safety


def _snapshot(position: int, status: str = "PENDING", week: int | None = 1) -> PathItemSnapshot:
    return PathItemSnapshot(
        position=position,
        week_index=week,
        status=status,
        kind="EXECUTABLE",
        resource_slug=f"res-{position}",
        gate_skill=None,
        item_type="RESOURCE",
        score_breakdown={},
        explanation_metadata={"resource_slug": f"res-{position}", "title": f"R{position}"},
    )


def _v2(position: int) -> V2Item:
    return V2Item(
        position=position,
        week_index=1,
        status="PENDING",
        kind="EXECUTABLE",
        executable=True,
        resource_slug=f"new-{position}",
        gate=None,
        item_type="RESOURCE",
        score_breakdown={},
        explanation_metadata={},
    )


def test_positions_never_collide_with_frozen_completed_items():
    completed = [_snapshot(0, "COMPLETED"), _snapshot(1, "COMPLETED")]
    frozen = [
        V2Item(
            position=s.position,
            week_index=s.week_index,
            status="COMPLETED",
            kind=s.kind,
            executable=False,
            resource_slug=s.resource_slug,
            gate=None,
            item_type=s.item_type,
            score_breakdown={},
            explanation_metadata={},
        )
        for s in completed
    ]
    remaining = _assign_positions(frozen, [_v2(0), _v2(0), _v2(0)])
    all_positions = [item.position for item in frozen] + [item.position for item in remaining]
    assert len(all_positions) == len(set(all_positions))
    assert [item.position for item in frozen] == [0, 1]
    assert [item.position for item in remaining] == [2, 3, 4]


def test_positions_collision_safe_when_completed_item_is_mid_path():
    completed = [_snapshot(2, "COMPLETED")]
    frozen = [
        V2Item(
            position=2,
            week_index=1,
            status="COMPLETED",
            kind="EXECUTABLE",
            executable=False,
            resource_slug="res-2",
            gate=None,
            item_type="RESOURCE",
            score_breakdown={},
            explanation_metadata={},
        )
    ]
    remaining = _assign_positions(frozen, [_v2(0), _v2(0), _v2(0)])
    all_positions = [item.position for item in frozen] + [item.position for item in remaining]
    assert len(all_positions) == len(set(all_positions))
    assert frozen[0].position == 2
    assert [item.position for item in remaining] == sorted(item.position for item in remaining)


# ---------------------------------------------------------------- primary demo: UNKNOWN → GAP


@requires_db
def test_primary_demo_negative_assessment_adapts_path():
    learner_id = _learner(f"s3-primary-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.90)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    _evidence(learner_id, "supervised_learning", "ASSESSMENT", 0.85)

    v1 = _path(learner_id)

    completed_item = _first_executable(v1)
    done = client.post(
        f"/v1/learners/{learner_id}/paths/{v1['id']}/complete-item",
        json={"position": completed_item["position"]},
    )
    assert done.status_code == 200, done.text
    # Snapshot V1 after completion: adaptation must not touch any of these rows.
    v1_items_before = _db_path_items(v1["id"])

    response = _submit(learner_id, "model-evaluation-gate", _wrong("model-evaluation-gate"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["adaptation"] == "CREATED"
    assert body["path_id"] and body["path_id"] != v1["id"]

    me = next(r for r in body["skill_results"] if r["skill"] == "model_evaluation")
    assert me["observed_level"] == pytest.approx(0.0)

    # model_evaluation is now a KNOWN gap against the role target (0.80).
    gaps = client.get(f"/v1/learners/{learner_id}/roles/{AIML}/gaps").json()["items"]
    me_gap = next(item for item in gaps if item["skill"] == "model_evaluation")
    assert me_gap["proficiency"] == pytest.approx(0.0)
    assert me_gap["attainment"] == "GAP"
    assert me_gap["evidence_state"] == "KNOWN"
    # Downstream: model_deployment remains gated behind unresolved
    # prerequisites while new model_evaluation remediation is inserted.
    deployment = next(item for item in gaps if item["skill"] == "model_deployment")
    assert deployment["action"] == "REMEDIATE_BLOCKER"
    assert deployment["blocked"] is True

    # Versioning: V1 SUPERSEDED and untouched; V2 ACTIVE with parent link.
    paths = {p["id"]: p for p in _paths(learner_id)}
    v1_after, v2 = paths[v1["id"]], paths[body["path_id"]]
    assert v1_after["status"] == "SUPERSEDED"
    assert v2["status"] == "ACTIVE"
    assert v2["version"] == v1["version"] + 1
    assert _db_path_items(v1["id"]) == v1_items_before  # V1 immutable

    # Completed work frozen in V2.
    v2_items = _db_path_items(v2["id"])
    v2_completed = [row for row in v2_items if row[2] == "COMPLETED"]
    assert len(v2_completed) == 1
    assert v2_completed[0][0] == completed_item["position"]
    assert v2_completed[0][1] == completed_item["week"]
    assert v2_completed[0][4].get("resource_slug") == completed_item["resource"]

    # Remediation inserted for the newly diagnosed gap; diff explains it.
    diff = body["diff"]
    assert "model_evaluation" in diff["changed_skills"]
    added_skills = {entry["skill"] for entry in diff["added"]}
    assert "model_evaluation" in added_skills
    me_added = next(e for e in diff["added"] if e["skill"] == "model_evaluation")
    assert "UNKNOWN" in me_added["reason"] and "GAP" in me_added["reason"]

    # No position collisions anywhere in V2.
    positions = [row[0] for row in v2_items]
    assert len(positions) == len(set(positions))

    # Diff API returns the same story.
    api_diff = client.get(f"/v1/learners/{learner_id}/paths/{v2['id']}/diff").json()
    assert api_diff["trigger_type"] == "ASSESSMENT_RESULT"
    assert {e["key"] for e in api_diff["added"]} == {e["key"] for e in diff["added"]}


# ---------------------------------------------------------------- positive surprise


@requires_db
def test_positive_surprise_removes_unjustified_remediation():
    learner_id = _learner(f"s3-positive-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.90)
    _evidence(learner_id, "statistics", "SELF_REPORT", 0.45, confidence=0.60)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)

    v1 = _path(learner_id)
    stats_v1 = [
        item
        for item in v1["items"]
        if item["target_skill"] == "statistics" and item["kind"] == "EXECUTABLE"
    ]
    assert stats_v1, "V1 should contain statistics remediation"

    response = _submit(learner_id, "statistics-gate", _correct("statistics-gate"))
    body = response.json()
    assert body["adaptation"] == "CREATED"

    skills = client.get(f"/v1/learners/{learner_id}/skills").json()
    fused_stats = next(item for item in skills if item["skill"] == "statistics")
    assert fused_stats["proficiency"] >= 0.80  # role target met → TARGET_MET

    diff = body["diff"]
    removed_stats = [e for e in diff["removed"] if e["skill"] == "statistics"]
    assert removed_stats, "statistics remediation should be removed"
    assert "target attainment" in removed_stats[0]["reason"]

    v2 = next(p for p in _paths(learner_id) if p["id"] == body["path_id"])
    v2_stats = [
        item
        for item in v2["items"]
        if item["target_skill"] == "statistics" and item["status"] != "COMPLETED"
    ]
    assert not v2_stats, "no remaining statistics remediation in V2"
    remaining_v2 = [i for i in v2["items"] if i["status"] != "COMPLETED"]
    remaining_v1 = [i for i in v1["items"] if i["status"] != "COMPLETED"]
    assert len(remaining_v2) < len(remaining_v1)


# ---------------------------------------------------------------- UNKNOWN → KNOWN (docker)


@requires_db
def test_unknown_to_known_resolves_gate_and_unblocks_resource():
    learner_id = _learner(f"s3-docker-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.92)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.85)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.88)
    _evidence(learner_id, "model_evaluation", "ASSESSMENT", 0.85)
    _evidence(learner_id, "model_deployment", "ASSESSMENT", 0.30)
    _evidence(learner_id, "supervised_learning", "ASSESSMENT", 0.85)

    v1 = _path(learner_id)
    gate_docker = [
        item for item in v1["items"] if (item.get("gate") or {}).get("skill") == "docker"
    ]
    assert gate_docker, "V1 should contain a docker verification gate"
    waiting_v1 = [item for item in v1["items"] if not item["executable"]]
    assert waiting_v1, "docker-dependent resources should be waiting"

    response = _submit(learner_id, "docker-gate", _correct("docker-gate"))
    body = response.json()
    assert body["adaptation"] == "CREATED"
    docker_result = next(r for r in body["skill_results"] if r["skill"] == "docker")
    assert docker_result["observed_level"] == pytest.approx(1.0)

    skills = client.get(f"/v1/learners/{learner_id}/skills").json()
    fused_docker = next(item for item in skills if item["skill"] == "docker")
    assert fused_docker["status"] != "UNKNOWN"
    assert fused_docker["proficiency"] >= 0.70  # role target → gate VERIFIED

    diff = body["diff"]
    removed_gates = [e for e in diff["removed"] if e["key"] == "gate:docker"]
    assert removed_gates, "resolved docker gate should be removed from remaining path"
    assert "role target" in removed_gates[0]["reason"]

    v2 = next(p for p in _paths(learner_id) if p["id"] == body["path_id"])
    assert not [i for i in v2["items"] if (i.get("gate") or {}).get("skill") == "docker"]
    # A resource that was waiting on docker is now executable.
    waiting_slugs_v1 = {i["resource"] for i in waiting_v1}
    executable_slugs_v2 = {i["resource"] for i in v2["items"] if i["executable"]}
    assert waiting_slugs_v1 & executable_slugs_v2, "blocked resource became eligible"


# ---------------------------------------------------------------- versioning / immutability


@requires_db
def test_v1_items_never_updated_and_parent_link():
    learner_id = _learner(f"s3-version-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.90)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    _evidence(learner_id, "supervised_learning", "ASSESSMENT", 0.85)
    v1 = _path(learner_id)
    before = _db_path_items(v1["id"])

    response = _submit(learner_id, "model-evaluation-gate", _wrong("model-evaluation-gate"))
    assert response.json()["adaptation"] == "CREATED"
    assert _db_path_items(v1["id"]) == before

    session = SessionLocal()
    try:
        v1_row = session.get(LearningPath, uuid.UUID(v1["id"]))
        v2_row = session.get(LearningPath, uuid.UUID(response.json()["path_id"]))
        assert v1_row.status == "SUPERSEDED"
        assert v2_row.parent_path_id == v1_row.id
        assert v2_row.version == v1_row.version + 1
    finally:
        session.close()


# ---------------------------------------------------------------- no-op


@requires_db
def test_assessment_that_changes_nothing_creates_no_v2():
    learner_id = _learner(f"s3-noop-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.92)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.40)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    _evidence(learner_id, "model_evaluation", "ASSESSMENT", 0.88)
    v1 = _path(learner_id)

    # model_evaluation already exceeds its 0.80 role target; a perfect
    # assessment only confirms it. Evidence is stored, but no V2 is created.
    response = _submit(learner_id, "model-evaluation-gate", _correct("model-evaluation-gate"))
    body = response.json()
    assert body["adaptation"] == "NO_ADAPTATION_REQUIRED"
    assert body["path_id"] is None

    paths = _paths(learner_id)
    assert len(paths) == 1
    assert paths[0]["id"] == v1["id"]

    evidence, attempts = _db_rows_for(learner_id)
    assert len(attempts) == 1
    assert any(
        row.evidence_payload.get("assessment") == "model-evaluation-gate" for row in evidence
    )


def _db_rows_for(learner_id: str):
    from app.models import AssessmentAttempt, SkillEvidence

    session = SessionLocal()
    try:
        evidence = session.scalars(
            select(SkillEvidence).where(SkillEvidence.user_id == uuid.UUID(learner_id))
        ).all()
        attempts = session.scalars(
            select(AssessmentAttempt).where(AssessmentAttempt.user_id == uuid.UUID(learner_id))
        ).all()
        return evidence, attempts
    finally:
        session.close()


# ---------------------------------------------------------------- determinism


@requires_db
def test_same_inputs_produce_same_adaptation():
    def run(tag: str):
        learner_id = _learner(f"s3-det-{tag}-{uuid.uuid4().hex[:6]}")
        _evidence(learner_id, "python", "ASSESSMENT", 0.90)
        _evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
        _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
        _evidence(learner_id, "supervised_learning", "ASSESSMENT", 0.85)
        _path(learner_id)
        body = _submit(learner_id, "model-evaluation-gate", _wrong("model-evaluation-gate")).json()
        v2 = next(p for p in _paths(learner_id) if p["id"] == body["path_id"])
        return body["diff"], [
            (i["position"], i["week"], i["resource"], i["kind"]) for i in v2["items"]
        ]

    diff_a, items_a = run("a")
    diff_b, items_b = run("b")
    assert diff_a["changed_skills"] == diff_b["changed_skills"]
    assert {e["key"] for e in diff_a["added"]} == {e["key"] for e in diff_b["added"]}
    assert {e["key"] for e in diff_a["removed"]} == {e["key"] for e in diff_b["removed"]}
    assert items_a == items_b


# ---------------------------------------------------------------- rollback


@requires_db
def test_failure_rolls_back_everything(monkeypatch):
    from app.services.assessment import runtime

    learner_id = _learner(f"s3-rollback-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.90)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    _evidence(learner_id, "supervised_learning", "ASSESSMENT", 0.85)
    v1 = _path(learner_id)
    evidence_before, attempts_before = _db_rows_for(learner_id)

    def boom(**kwargs):
        raise RuntimeError("simulated adaptation failure")

    monkeypatch.setattr(runtime, "persist_adapted_path", boom)
    failing = TestClient(app, raise_server_exceptions=False)
    response = failing.post(
        f"/v1/learners/{learner_id}/assessments/model-evaluation-gate/attempts",
        json={"answers": _wrong("model-evaluation-gate")},
    )
    assert response.status_code == 500

    evidence_after, attempts_after = _db_rows_for(learner_id)
    assert len(evidence_after) == len(evidence_before)  # no half-written evidence
    assert len(attempts_after) == len(attempts_before)  # no orphan attempt
    paths = _paths(learner_id)
    assert len(paths) == 1 and paths[0]["id"] == v1["id"] and paths[0]["status"] == "ACTIVE"

    session = SessionLocal()
    try:
        from app.models import AdaptationEvent

        events = session.scalars(
            select(AdaptationEvent).where(AdaptationEvent.user_id == uuid.UUID(learner_id))
        ).all()
        assert not events
    finally:
        session.close()


# ---------------------------------------------------------------- complete-item API


@requires_db
def test_complete_item_validations():
    learner_id = _learner(f"s3-complete-{uuid.uuid4().hex[:8]}")
    other_id = _learner(f"s3-other-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.90)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    path = _path(learner_id)

    # wrong owner
    response = client.post(
        f"/v1/learners/{other_id}/paths/{path['id']}/complete-item", json={"position": 0}
    )
    assert response.status_code == 404
    # unknown position
    response = client.post(
        f"/v1/learners/{learner_id}/paths/{path['id']}/complete-item", json={"position": 999}
    )
    assert response.status_code == 404
    # waiting items are not completable
    waiting = [item for item in path["items"] if not item["executable"]]
    if waiting:
        response = client.post(
            f"/v1/learners/{learner_id}/paths/{path['id']}/complete-item",
            json={"position": waiting[0]["position"]},
        )
        assert response.status_code == 422
    # happy path + double completion
    item = _first_executable(path)
    response = client.post(
        f"/v1/learners/{learner_id}/paths/{path['id']}/complete-item",
        json={"position": item["position"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "COMPLETED"
    response = client.post(
        f"/v1/learners/{learner_id}/paths/{path['id']}/complete-item",
        json={"position": item["position"]},
    )
    assert response.status_code == 409


# ---------------------------------------------------------------- suggested assessment


@requires_db
def test_suggested_assessment_prefers_unknown_impactful_skills():
    learner_id = _learner(f"s3-suggest-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.90)
    response = client.get(f"/v1/learners/{learner_id}/roles/{AIML}/assessments/suggested")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["assessment"] is not None
    assert body["question_count"] <= 10
    assert body["covers"], "suggestion should cover UNKNOWN role skills"
