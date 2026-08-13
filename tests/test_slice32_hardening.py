"""Slice 3.2 production/judge hardening tests."""

from __future__ import annotations

import copy
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.enums import PathStatus
from app.core.ids import ontology_uuid
from app.db.session import SessionLocal
from app.main import app
from app.models import Assessment, LearningPath, PathItem, Role
from app.ontology.load import AssessmentSpec, OntologyBundle, QuestionSpec, load_ontology
from app.ontology.validate import assert_valid
from app.services.assessment.fingerprint import assessment_fingerprint
from app.services.assessment.loader import AssessmentDriftError, load_assessment_spec

client = TestClient(app)
BUNDLE = load_ontology()
SPECS = {item.slug: item for item in BUNDLE.assessments}
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


def _path(learner_id: str, role: str = AIML, hours: float = 10) -> dict:
    response = client.post(
        f"/v1/learners/{learner_id}/paths",
        json={"role": role, "weekly_hours": hours, "learning_style": "MIXED"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _submit(learner_id: str, slug: str, answers: list[int]):
    return client.post(
        f"/v1/learners/{learner_id}/assessments/{slug}/attempts",
        json={"answers": answers},
    )


def _wrong(slug: str) -> list[int]:
    return [(q.correct_index + 1) % len(q.choices) for q in SPECS[slug].questions]


def _correct(slug: str) -> list[int]:
    return [q.correct_index for q in SPECS[slug].questions]


def _db_path_snapshot(path_id: str) -> list[tuple]:
    session = SessionLocal()
    try:
        rows = session.scalars(
            select(PathItem)
            .where(PathItem.learning_path_id == uuid.UUID(path_id))
            .order_by(PathItem.position)
        ).all()
        return [
            (
                row.position,
                row.week_index,
                row.status,
                row.item_type,
                dict(row.explanation_metadata or {}),
            )
            for row in rows
        ]
    finally:
        session.close()


def _db_paths(learner_id: str) -> list[LearningPath]:
    session = SessionLocal()
    try:
        return list(
            session.scalars(
                select(LearningPath)
                .where(LearningPath.user_id == uuid.UUID(learner_id))
                .order_by(LearningPath.version)
            ).all()
        )
    finally:
        session.close()


def _executable_resource_keys(path: dict) -> list[str]:
    keys = []
    for item in path["items"]:
        if item["kind"] == "EXECUTABLE" and item["resource"]:
            keys.append(item["resource"])
    return keys


# ------------------------------------------------------------------ H1 V1→V2→V3


@requires_db
def test_v1_v2_v3_chain_immutability_in_database():
    learner_id = _learner(f"s32-chain-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.90)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    _evidence(learner_id, "supervised_learning", "ASSESSMENT", 0.85)

    v1 = _path(learner_id)
    v1_db_before = _db_path_snapshot(v1["id"])

    r2 = _submit(learner_id, "model-evaluation-gate", _wrong("model-evaluation-gate"))
    assert r2.status_code == 200, r2.text
    v2_id = r2.json()["path_id"]
    v2_db_after_first = _db_path_snapshot(v2_id)

    r3 = _submit(learner_id, "statistics-gate", _correct("statistics-gate"))
    assert r3.status_code == 200, r3.text
    v3_id = r3.json()["path_id"]
    assert v3_id != v2_id != v1["id"]

    rows = _db_paths(learner_id)
    assert len(rows) == 3
    by_version = {row.version: row for row in rows}
    assert by_version[1].status == PathStatus.SUPERSEDED.value
    assert by_version[2].status == PathStatus.SUPERSEDED.value
    assert by_version[3].status == PathStatus.ACTIVE.value
    assert by_version[2].parent_path_id == by_version[1].id
    assert by_version[3].parent_path_id == by_version[2].id

    assert _db_path_snapshot(v1["id"]) == v1_db_before
    assert _db_path_snapshot(v2_id) == v2_db_after_first

    active = [row for row in rows if row.status == PathStatus.ACTIVE.value]
    assert len(active) == 1

    timeline = client.get(
        f"/v1/learners/{learner_id}/roles/{AIML}/path-timeline"
    ).json()
    assert [entry["version"] for entry in timeline] == [1, 2, 3]
    assert timeline[-1]["status"] == "ACTIVE"


# ------------------------------------------------------------------ H2 one ACTIVE constraint


@requires_db
def test_database_rejects_two_active_paths_for_same_role():
    learner_id = _learner(f"s32-active-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.90)
    v1 = _path(learner_id)

    session = SessionLocal()
    try:
        role = session.scalar(select(Role).where(Role.slug == AIML))
        duplicate = LearningPath(
            id=uuid.uuid4(),
            user_id=uuid.UUID(learner_id),
            role_id=role.id,
            version=99,
            status=PathStatus.ACTIVE.value,
            parent_path_id=uuid.UUID(v1["id"]),
            total_estimated_hours=10.0,
            extra_metadata={"role": AIML},
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    finally:
        session.close()

    rows = _db_paths(learner_id)
    assert len([row for row in rows if row.status == PathStatus.ACTIVE.value]) == 1


# ------------------------------------------------------------------ H3 runtime validation


def test_load_ontology_validates_by_default():
    bundle = load_ontology()
    assert bundle.skills


def test_invalid_ontology_fails_validation():
    broken = AssessmentSpec(
        slug="broken-runtime",
        title="broken",
        description="",
        primary_skill="python",
        pass_threshold=0.7,
        questions=[
            QuestionSpec(
                prompt="q",
                skill="python",
                difficulty=1,
                choices=["a", "b"],
                correct_index=0,
                explanation="",
                concept_tag="c",
            )
        ],
        target_role=None,
        target_skills=["python", "not-a-real-skill"],
    )
    bundle = OntologyBundle(
        skills=BUNDLE.skills,
        relationships=BUNDLE.relationships,
        roles=BUNDLE.roles,
        resources=BUNDLE.resources,
        assessments=[*BUNDLE.assessments, broken],
    )
    with pytest.raises(Exception):
        assert_valid(bundle)


def test_assessment_fingerprint_is_stable():
    spec = SPECS["python-gate"]
    assert assessment_fingerprint(spec) == assessment_fingerprint(spec)
    assert len(assessment_fingerprint(spec)) == 64


# ------------------------------------------------------------------ H4 drift


@requires_db
def test_assessment_drift_is_detected_at_runtime():
    learner_id = _learner(f"s32-drift-{uuid.uuid4().hex[:8]}")
    _path(learner_id)
    session = SessionLocal()
    try:
        assessment_id = ontology_uuid("assessment", "python-gate")
        yaml_spec = next(spec for spec in BUNDLE.assessments if spec.slug == "python-gate")
        drifted = copy.deepcopy(yaml_spec)
        drifted = AssessmentSpec(
            slug=drifted.slug,
            title=drifted.title,
            description=drifted.description,
            primary_skill=drifted.primary_skill,
            pass_threshold=0.41,
            questions=drifted.questions,
            target_role=drifted.target_role,
            target_skills=drifted.target_skills,
        )
        with pytest.raises(AssessmentDriftError) as exc:
            load_assessment_spec(session, assessment_id=assessment_id, yaml_spec=drifted)
        assert exc.value.code == "DRIFT_DETECTED"
    finally:
        session.close()

    response = _submit(learner_id, "python-gate", _correct("python-gate"))
    assert response.status_code == 200


@requires_db
def test_seed_stores_definition_hash():
    session = SessionLocal()
    try:
        row = session.get(Assessment, ontology_uuid("assessment", "python-gate"))
        assert row is not None
        assert row.definition_hash
        yaml_spec = next(spec for spec in BUNDLE.assessments if spec.slug == "python-gate")
        assert row.definition_hash == assessment_fingerprint(yaml_spec)
    finally:
        session.close()


# ------------------------------------------------------------------ H5 completed + positive surprise


@requires_db
def test_completed_statistics_survives_positive_surprise_adaptation():
    learner_id = _learner(f"s32-pos-complete-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.90)
    _evidence(learner_id, "statistics", "SELF_REPORT", 0.45, confidence=0.60)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)

    v1 = _path(learner_id)
    stats_item = next(
        item
        for item in v1["items"]
        if item["target_skill"] == "statistics" and item["executable"]
    )
    client.post(
        f"/v1/learners/{learner_id}/paths/{v1['id']}/complete-item",
        json={"position": stats_item["position"]},
    ).raise_for_status()
    completed_snapshot = _db_path_snapshot(v1["id"])

    body = _submit(learner_id, "statistics-gate", _correct("statistics-gate")).json()
    assert body["adaptation"] == "CREATED"
    v2_id = body["path_id"]

    v2_completed = [
        row
        for row in _db_path_snapshot(v2_id)
        if row[2] == "COMPLETED" and row[4].get("resource_slug") == stats_item["resource"]
    ]
    assert len(v2_completed) == 1
    assert v2_completed[0][0] == stats_item["position"]
    assert v2_completed[0][1] == stats_item["week"]

    v2 = next(p for p in client.get(f"/v1/learners/{learner_id}/paths").json() if p["id"] == v2_id)
    pending_stats = [
        item
        for item in v2["items"]
        if item["target_skill"] == "statistics" and item["status"] != "COMPLETED"
    ]
    assert not pending_stats
    assert _db_path_snapshot(v1["id"]) == completed_snapshot


# ------------------------------------------------------------------ H9 completed invalidation


@requires_db
def test_completed_remediation_not_removed_when_skill_becomes_target_met():
    learner_id = _learner(f"s32-invalidate-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.90)
    _evidence(learner_id, "statistics", "SELF_REPORT", 0.45, confidence=0.60)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)

    v1 = _path(learner_id)
    stats = next(
        i for i in v1["items"] if i["target_skill"] == "statistics" and i["executable"]
    )
    client.post(
        f"/v1/learners/{learner_id}/paths/{v1['id']}/complete-item",
        json={"position": stats["position"]},
    ).raise_for_status()

    body = _submit(learner_id, "statistics-gate", _correct("statistics-gate")).json()
    v2_id = body["path_id"]
    frozen = [
        row
        for row in _db_path_snapshot(v2_id)
        if row[2] == "COMPLETED" and row[4].get("resource_slug") == stats["resource"]
    ]
    assert frozen, "completed statistics remediation must remain in V2"


# ------------------------------------------------------------------ H6 python UNKNOWN blocker


@requires_db
def test_python_unknown_blocks_ml_until_verified_and_target_met():
    learner_id = _learner(f"s32-python-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)

    v1 = _path(learner_id)
    python_gates = [
        item for item in v1["items"] if (item.get("gate") or {}).get("skill") == "python"
    ]
    assert python_gates, "Python verification gate required when Python is UNKNOWN"
    ml_items = [item for item in v1["items"] if item["target_skill"] == "ml_fundamentals"]
    assert ml_items
    assert all(not item["executable"] for item in ml_items)

    low = _submit(learner_id, "python-gate", _wrong("python-gate"))
    assert low.status_code == 200, low.text
    gaps = client.get(f"/v1/learners/{learner_id}/roles/{AIML}/gaps").json()["items"]
    python_gap = next(item for item in gaps if item["skill"] == "python")
    assert python_gap["evidence_state"] == "KNOWN"
    assert python_gap["attainment"] == "GAP"
    ml_gap = next(item for item in gaps if item["skill"] == "ml_fundamentals")
    assert ml_gap["blocked"] is True

    high = _submit(learner_id, "python-gate", _correct("python-gate"))
    assert high.status_code == 200, high.text
    gaps_after = client.get(f"/v1/learners/{learner_id}/roles/{AIML}/gaps").json()["items"]
    python_after = next(item for item in gaps_after if item["skill"] == "python")
    assert python_after["attainment"] == "TARGET_MET"
    v2 = next(
        p
        for p in client.get(f"/v1/learners/{learner_id}/paths").json()
        if p["status"] == "ACTIVE"
    )
    ml_v2 = [item for item in v2["items"] if item["target_skill"] == "ml_fundamentals"]
    assert any(item["executable"] for item in ml_v2)


# ------------------------------------------------------------------ H7 no-op material state


@requires_db
def test_no_adaptation_when_material_state_unchanged():
    learner_id = _learner(f"s32-noop-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.92)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.40)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    _evidence(learner_id, "model_evaluation", "ASSESSMENT", 0.88)
    v1 = _path(learner_id)
    body = _submit(learner_id, "model-evaluation-gate", _correct("model-evaluation-gate")).json()
    assert body["adaptation"] == "NO_ADAPTATION_REQUIRED"
    assert len(_db_paths(learner_id)) == 1
    assert _db_paths(learner_id)[0].id == uuid.UUID(v1["id"])


@requires_db
def test_completed_work_week_shift_triggers_adaptation():
    learner_id = _learner(f"s32-week-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.90)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    _evidence(learner_id, "supervised_learning", "ASSESSMENT", 0.85)
    v1 = _path(learner_id)
    first = next(i for i in v1["items"] if i["executable"] and i["kind"] == "EXECUTABLE")
    client.post(
        f"/v1/learners/{learner_id}/paths/{v1['id']}/complete-item",
        json={"position": first["position"]},
    ).raise_for_status()

    body = _submit(learner_id, "model-evaluation-gate", _wrong("model-evaluation-gate")).json()
    assert body["adaptation"] == "CREATED"
    moved = body["diff"]["moved"]
    assert moved, "week repack after completed work should produce MOVED entries"


# ------------------------------------------------------------------ H8 unique resource keys


@requires_db
def test_path_has_no_duplicate_executable_resource_keys():
    learner_id = _learner(f"s32-unique-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.90)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    _evidence(learner_id, "supervised_learning", "ASSESSMENT", 0.85)
    v1 = _path(learner_id)
    keys = _executable_resource_keys(v1)
    assert len(keys) == len(set(keys))

    body = _submit(learner_id, "model-evaluation-gate", _wrong("model-evaluation-gate")).json()
    v2 = next(
        p
        for p in client.get(f"/v1/learners/{learner_id}/paths").json()
        if p["id"] == body["path_id"]
    )
    keys_v2 = _executable_resource_keys(v2)
    assert len(keys_v2) == len(set(keys_v2))
