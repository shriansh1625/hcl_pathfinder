"""Slice 3 assessment domain tests: scoring, confidence, normalization,
selection, gate resolution, evidence persistence, idempotency, retakes,
and conflict with prior evidence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text

from app.core.config import settings
from app.core.enums import EvidenceSource
from app.db.session import SessionLocal
from app.main import app
from app.models import AssessmentAttempt, LearningPath, Skill, SkillEvidence
from app.ontology.load import AssessmentSpec, OntologyBundle, QuestionSpec, load_ontology
from app.services.assessment.normalizer import evidence_rows_from_score
from app.services.assessment.scoring import score_attempt, skill_confidence
from app.services.assessment.selection import select_assessment
from app.services.profiling.evidence_fusion import EvidenceRecord, fuse_skill_evidence
from app.services.verification.gates import resolve_gate_state

client = TestClient(app)


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

BUNDLE = load_ontology()
SPECS = {item.slug: item for item in BUNDLE.assessments}


def _spec(slug: str, question_count: int, difficulty: int = 1) -> AssessmentSpec:
    questions = [
        QuestionSpec(
            prompt=f"Q{i}",
            skill="python",
            difficulty=difficulty,
            choices=["a", "b"],
            correct_index=0,
            explanation="",
            concept_tag=f"c{i}",
        )
        for i in range(question_count)
    ]
    return AssessmentSpec(
        slug=f"synthetic-{question_count}",
        title="synthetic",
        description="",
        primary_skill="python",
        pass_threshold=0.7,
        questions=questions,
        target_role=None,
        target_skills=["python"],
    )


# ---------------------------------------------------------------- scoring


def test_skill_level_scoring_is_difficulty_weighted():
    spec = SPECS["python-gate"]
    # q0 (python, d2) correct, q1 (python, d2) wrong, q2 (data_structures, d3) correct
    score = score_attempt(spec, [1, 0, 2])
    by_skill = {item.skill_slug: item for item in score.skill_results}
    assert by_skill["python"].observed_level == pytest.approx(0.5)
    assert by_skill["data_structures"].observed_level == pytest.approx(1.0)
    assert by_skill["python"].correct_count == 1
    assert set(by_skill) == {"python", "data_structures"}
    assert score.overall_score == pytest.approx(5 / 7)


def test_overall_scoring_and_pass_threshold():
    spec = SPECS["python-gate"]
    perfect = score_attempt(spec, [q.correct_index for q in spec.questions])
    assert perfect.overall_score == pytest.approx(1.0)
    assert perfect.passed is True
    empty = score_attempt(spec, [(q.correct_index + 1) % len(q.choices) for q in spec.questions])
    assert empty.overall_score == pytest.approx(0.0)
    assert empty.passed is False


def test_scoring_rejects_malformed_answers():
    spec = SPECS["python-gate"]
    with pytest.raises(ValueError):
        score_attempt(spec, [0])
    with pytest.raises(ValueError):
        score_attempt(spec, [0, 0, 99])


# ---------------------------------------------------------------- confidence


def test_confidence_grows_with_question_count():
    spec_1 = _spec("a", 1)
    spec_5 = _spec("b", 5)
    spec_10 = _spec("c", 10)
    c1 = score_attempt(spec_1, [0]).skill_results[0].confidence
    c5 = score_attempt(spec_5, [0] * 5).skill_results[0].confidence
    c10 = score_attempt(spec_10, [0] * 10).skill_results[0].confidence
    assert c1 < c5 < c10
    assert c10 <= 0.95


def test_confidence_clamped_and_mixed_penalty():
    high = skill_confidence(question_count=20, difficulty_avg=5.0, all_agree=True)
    assert high == 0.95
    mixed = skill_confidence(question_count=4, difficulty_avg=2.0, all_agree=False)
    agree = skill_confidence(question_count=4, difficulty_avg=2.0, all_agree=True)
    assert mixed == pytest.approx(agree - 0.20)
    low = skill_confidence(question_count=3, difficulty_avg=1.0, all_agree=False)
    assert low >= 0.30


def test_tiny_assessment_does_not_overpower_strong_project_evidence():
    # Strong prior PROJECT evidence: reliability 0.80.
    now = datetime.now(timezone.utc)
    prior = EvidenceRecord(
        skill_slug="python",
        source="PROJECT",
        observed_level=0.90,
        reliability=0.80,
        confidence=0.85,
        created_at=now,
    )
    weak_quiz = EvidenceRecord(
        skill_slug="python",
        source="ASSESSMENT",
        observed_level=0.30,
        reliability=0.90,
        confidence=score_attempt(_spec("one", 1), [1]).skill_results[0].confidence,
        created_at=now,
    )
    fused = fuse_skill_evidence([prior, weak_quiz], skill_slug="python")
    # One answered-wrong question must not collapse a strong project record.
    assert fused.proficiency > 0.55
    assert fused.evidence_count == 2
    assert fused.conflict is True

    strong_quiz_conf = score_attempt(_spec("ten", 10), [1] * 10).skill_results[0].confidence
    strong_quiz = EvidenceRecord(
        skill_slug="python",
        source="ASSESSMENT",
        observed_level=0.30,
        reliability=0.90,
        confidence=strong_quiz_conf,
        created_at=now,
    )
    fused_strong = fuse_skill_evidence([prior, strong_quiz], skill_slug="python")
    # A longer, consistent assessment moves the state further than a tiny quiz.
    assert fused_strong.proficiency < fused.proficiency


def test_strong_assessment_dominates_weak_self_report():
    now = datetime.now(timezone.utc)
    prior = EvidenceRecord(
        skill_slug="statistics",
        source="SELF_REPORT",
        observed_level=0.40,
        reliability=0.40,
        confidence=0.50,
        created_at=now,
    )
    quiz = EvidenceRecord(
        skill_slug="statistics",
        source="ASSESSMENT",
        observed_level=0.90,
        reliability=0.90,
        confidence=0.90,
        created_at=now,
    )
    fused = fuse_skill_evidence([prior, quiz], skill_slug="statistics")
    assert fused.proficiency > 0.75


# ---------------------------------------------------------------- normalizer


def test_normalizer_emits_one_row_per_skill_with_payload():
    spec = SPECS["statistics-gate"]
    score = score_attempt(spec, [q.correct_index for q in spec.questions])
    attempt_id = uuid.uuid4()
    rows = evidence_rows_from_score(score, attempt_id=attempt_id)
    assert {row["skill"] for row in rows} == {"statistics", "probability"}
    for row in rows:
        assert row["source"] == EvidenceSource.ASSESSMENT.value
        payload = row["evidence_payload"]
        assert payload["assessment"] == "statistics-gate"
        assert payload["attempt_id"] == str(attempt_id)
        assert payload["question_count"] >= 1
        assert "difficulty_avg" in payload
        assert payload["consistency"] in {"AGREE", "MIXED"}


# ---------------------------------------------------------------- gate resolution


def _profile_for(levels: dict[str, float | None], targets: dict[str, float]):
    from app.services.gap_engine.profile import build_gap_profile
    from app.services.profiling.evidence_fusion import FusedSkill
    from app.core.enums import RequiredStatus, SkillStatus
    from app.services.skill_graph.competency import RoleCompetency, RoleCompetencySet

    fused = {}
    for slug, level in levels.items():
        if level is None:
            fused[slug] = FusedSkill(
                skill_slug=slug,
                proficiency=None,
                confidence=None,
                status=SkillStatus.UNKNOWN,
                evidence_count=0,
                conflict=False,
                conflict_spread=None,
                dominant_source=None,
                weights=(),
                reason="no evidence",
            )
        else:
            fused[slug] = FusedSkill(
                skill_slug=slug,
                proficiency=level,
                confidence=0.8,
                status=SkillStatus.DEVELOPING,
                evidence_count=1,
                conflict=False,
                conflict_spread=0.0,
                dominant_source="ASSESSMENT",
                weights=(),
                reason="",
            )
    competencies = tuple(
        RoleCompetency(
            skill_slug=slug,
            skill_name=slug,
            target_level=targets[slug],
            importance=0.9,
            required_status=RequiredStatus.CORE,
        )
        for slug in targets
    )
    role = RoleCompetencySet(role_slug="r", role_name="R", competencies=competencies)
    return build_gap_profile(fused_by_slug=fused, role=role, edges=[])


def test_gate_resolution_uses_role_target_not_pass_threshold():
    # Role target 0.75. A fused 0.72 would PASS a 0.70 assessment threshold,
    # but the gate must still be FAILED against the role target.
    profile = _profile_for({"docker": 0.72}, {"docker": 0.75})
    from app.core.enums import GateState

    assert resolve_gate_state("docker", profile) is GateState.FAILED
    profile = _profile_for({"docker": 0.78}, {"docker": 0.75})
    assert resolve_gate_state("docker", profile) is GateState.VERIFIED
    profile = _profile_for({"docker": None}, {"docker": 0.75})
    assert resolve_gate_state("docker", profile) is GateState.PENDING


# ---------------------------------------------------------------- selection


def test_selection_prefers_covering_unknown_skills():
    profile = _profile_for(
        {"docker": None, "statistics": None},
        {"docker": 0.70, "statistics": 0.80},
    )
    picked = select_assessment(profile, list(BUNDLE.assessments))
    assert picked is not None
    assert set(picked.target_skills) & {"docker", "statistics"}
    assert len(picked.questions) <= 10


def test_selection_returns_none_when_nothing_unknown():
    profile = _profile_for({"docker": 0.9}, {"docker": 0.70})
    assert select_assessment(profile, list(BUNDLE.assessments)) is None


# ---------------------------------------------------------------- ontology validation


def test_invalid_target_skills_fail_validation():
    from app.ontology.validate import validate_ontology

    spec = AssessmentSpec(
        slug="broken-gate",
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
        target_skills=["python", "deep-learning-foo"],
    )
    bundle = OntologyBundle(
        skills=BUNDLE.skills,
        relationships=BUNDLE.relationships,
        roles=BUNDLE.roles,
        resources=BUNDLE.resources,
        assessments=[*BUNDLE.assessments, spec],
    )
    errors = validate_ontology(bundle)
    assert any("deep-learning-foo" in error for error in errors)


# ---------------------------------------------------------------- DB-backed flow


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


def _path(learner_id: str, role: str = "ai-ml-engineer", hours: float = 8) -> dict:
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


def _db_rows(learner_id: str):
    session = SessionLocal()
    try:
        evidence = session.scalars(
            select(SkillEvidence).where(SkillEvidence.user_id == uuid.UUID(learner_id))
        ).all()
        attempts = session.scalars(
            select(AssessmentAttempt).where(AssessmentAttempt.user_id == uuid.UUID(learner_id))
        ).all()
        paths = session.scalars(
            select(LearningPath).where(LearningPath.user_id == uuid.UUID(learner_id))
        ).all()
        skill_slugs = {s.id: s.slug for s in session.scalars(select(Skill)).all()}
        return evidence, attempts, paths, skill_slugs
    finally:
        session.close()


@requires_db
def test_submission_persists_attempt_and_append_only_evidence():
    learner_id = _learner(f"s3-submit-{uuid.uuid4().hex[:8]}")
    _path(learner_id)
    spec = SPECS["statistics-gate"]
    answers = [q.correct_index for q in spec.questions]
    response = _submit(learner_id, "statistics-gate", answers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["passed"] is True
    assert {r["skill"] for r in body["skill_results"]} == {"statistics", "probability"}

    evidence, attempts, _, skill_slugs = _db_rows(learner_id)
    assert len(attempts) == 1
    assessment_rows = [row for row in evidence if row.source_type == "ASSESSMENT"]
    assert {skill_slugs[row.skill_id] for row in assessment_rows} == {"statistics", "probability"}
    for row in assessment_rows:
        assert row.evidence_payload["assessment"] == "statistics-gate"
        assert row.evidence_payload["attempt_id"] == body["attempt_id"]


@requires_db
def test_duplicate_attempt_id_is_idempotent():
    learner_id = _learner(f"s3-idem-{uuid.uuid4().hex[:8]}")
    _path(learner_id)
    spec = SPECS["statistics-gate"]
    answers = [q.correct_index for q in spec.questions]
    attempt_id = str(uuid.uuid4())
    first = _submit(learner_id, "statistics-gate", answers, attempt_id)
    assert first.status_code == 200, first.text
    evidence_before, attempts_before, paths_before, _ = _db_rows(learner_id)

    second = _submit(learner_id, "statistics-gate", answers, attempt_id)
    assert second.status_code == 200, second.text
    assert second.json()["adaptation"] == "REPLAYED"
    assert second.json()["attempt_id"] == attempt_id

    evidence_after, attempts_after, paths_after, _ = _db_rows(learner_id)
    assert len(evidence_after) == len(evidence_before)
    assert len(attempts_after) == len(attempts_before) == 1
    assert len(paths_after) == len(paths_before)


@requires_db
def test_retake_creates_new_attempt_and_evidence():
    learner_id = _learner(f"s3-retake-{uuid.uuid4().hex[:8]}")
    _path(learner_id)
    spec = SPECS["model-evaluation-gate"]
    wrong = [(q.correct_index + 1) % len(q.choices) for q in spec.questions]
    right = [q.correct_index for q in spec.questions]
    first = _submit(learner_id, "model-evaluation-gate", wrong)
    second = _submit(learner_id, "model-evaluation-gate", right)
    assert first.json()["attempt_number"] == 1
    assert second.json()["attempt_number"] == 2
    assert first.json()["attempt_id"] != second.json()["attempt_id"]

    evidence, attempts, _, _ = _db_rows(learner_id)
    assert len(attempts) == 2
    me_rows = [
        row
        for row in evidence
        if row.source_type == "ASSESSMENT"
        and row.evidence_payload.get("assessment") == "model-evaluation-gate"
    ]
    assert len(me_rows) == 2  # both attempts remain auditable


@requires_db
def test_conflicting_evidence_is_retained_and_fused():
    learner_id = _learner(f"s3-conflict-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "SELF_REPORT", 0.90)
    _path(learner_id)
    # python: q0 (d2) correct, q1 (d2) wrong → observed 0.50; conflicts with 0.90.
    response = _submit(learner_id, "python-gate", [1, 0, 0])
    assert response.status_code == 200, response.text

    session = SessionLocal()
    try:
        rows = session.scalars(
            select(SkillEvidence)
            .join(Skill, Skill.id == SkillEvidence.skill_id)
            .where(SkillEvidence.user_id == uuid.UUID(learner_id), Skill.slug == "python")
        ).all()
        assert len(rows) == 2
        assert {row.source_type for row in rows} == {"SELF_REPORT", "ASSESSMENT"}
    finally:
        session.close()

    skills = client.get(f"/v1/learners/{learner_id}/skills").json()
    python = next(item for item in skills if item["skill"] == "python")
    assert python["conflict"] is True
    assert 0.50 < python["proficiency"] < 0.90
