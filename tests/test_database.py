from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.enums import AdaptationEventType, PathStatus, SkillStatus
from app.core.ids import ontology_uuid
from app.db.seed import seed_ontology
from app.models import (
    AdaptationEvent,
    Assessment,
    AssessmentQuestion,
    LearningPath,
    LearningResource,
    PathItem,
    Role,
    Skill,
    SkillEvidence,
    SkillRelationship,
    User,
    UserSkill,
)
from app.ontology.load import load_ontology


def postgres_available() -> bool:
    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not postgres_available(),
    reason="PostgreSQL is not reachable at DATABASE_URL",
)


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(settings.database_url, pool_pre_ping=True)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_database_connection(engine):
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1


def test_migrated_tables_exist(engine):
    tables = set(inspect(engine).get_table_names())
    required = {
        "skills",
        "skill_relationships",
        "roles",
        "role_skills",
        "learning_resources",
        "resource_skills",
        "resource_prerequisites",
        "assessments",
        "assessment_questions",
        "users",
        "profiles",
        "skill_evidence",
        "user_skills",
        "learning_paths",
        "path_items",
        "adaptation_events",
        "alembic_version",
    }
    missing = required - tables
    assert missing == set(), f"Missing tables: {missing}"


def test_seed_populates_ontology(session: Session):
    bundle = load_ontology()
    assert session.scalar(select(Skill).limit(1)) is not None
    assert session.scalar(select(Role).limit(1)) is not None
    skill_count = len(session.scalars(select(Skill)).all())
    role_count = len(session.scalars(select(Role)).all())
    assert skill_count == len(bundle.skills)
    assert role_count == len(bundle.roles)


def test_seed_is_idempotent(session: Session):
    before_skills = len(session.scalars(select(Skill)).all())
    before_rel = len(session.scalars(select(SkillRelationship)).all())
    before_res = len(session.scalars(select(LearningResource)).all())
    seed_ontology(session)
    session.expire_all()
    after_skills = len(session.scalars(select(Skill)).all())
    after_rel = len(session.scalars(select(SkillRelationship)).all())
    after_res = len(session.scalars(select(LearningResource)).all())
    assert after_skills == before_skills
    assert after_rel == before_rel
    assert after_res == before_res


def test_skill_and_role_unique_in_db(session: Session):
    slugs = [row.slug for row in session.scalars(select(Skill)).all()]
    names = [row.canonical_name for row in session.scalars(select(Skill)).all()]
    roles = [row.slug for row in session.scalars(select(Role)).all()]
    assert len(slugs) == len(set(slugs))
    assert len(names) == len(set(names))
    assert len(roles) == len(set(roles))


def test_assessment_references_are_intact(session: Session):
    questions = session.scalars(select(AssessmentQuestion)).all()
    assert questions
    for question in questions:
        assert session.get(Skill, question.skill_id) is not None
    for assessment in session.scalars(select(Assessment)).all():
        assert session.get(Skill, assessment.primary_skill_id) is not None


def test_unknown_user_skill_allows_null_proficiency(session: Session):
    user = User(id=uuid.uuid4(), display_name="slice0-unknown")
    session.add(user)
    python_id = ontology_uuid("skill", "python")
    session.add(
        UserSkill(
            user_id=user.id,
            skill_id=python_id,
            proficiency=None,
            confidence=0.0,
            status=SkillStatus.UNKNOWN.value,
            evidence_summary={"sources": []},
        )
    )
    session.commit()
    row = session.get(UserSkill, (user.id, python_id))
    assert row is not None
    assert row.proficiency is None
    assert row.status == SkillStatus.UNKNOWN.value
    session.delete(row)
    session.delete(user)
    session.commit()


def test_evidence_is_append_only_multiple_rows(session: Session):
    user = User(id=uuid.uuid4(), display_name="slice0-evidence")
    session.add(user)
    python_id = ontology_uuid("skill", "python")
    session.add(
        SkillEvidence(
            id=uuid.uuid4(),
            user_id=user.id,
            skill_id=python_id,
            source_type="SELF_REPORT",
            observed_level=0.7,
            reliability=0.35,
            confidence=0.4,
            evidence_payload={"note": "first"},
        )
    )
    session.add(
        SkillEvidence(
            id=uuid.uuid4(),
            user_id=user.id,
            skill_id=python_id,
            source_type="ASSESSMENT",
            observed_level=0.4,
            reliability=0.90,
            confidence=0.8,
            evidence_payload={"note": "second"},
        )
    )
    session.commit()
    rows = session.scalars(
        select(SkillEvidence).where(
            SkillEvidence.user_id == user.id, SkillEvidence.skill_id == python_id
        )
    ).all()
    assert len(rows) == 2
    for row in rows:
        session.delete(row)
    session.delete(user)
    session.commit()


def test_path_versions_coexist(session: Session):
    user = User(id=uuid.uuid4(), display_name="slice0-paths")
    session.add(user)
    role_id = ontology_uuid("role", "ai-ml-engineer")
    v1 = LearningPath(
        id=uuid.uuid4(),
        user_id=user.id,
        role_id=role_id,
        version=1,
        status=PathStatus.SUPERSEDED.value,
        parent_path_id=None,
        extra_metadata={"note": "v1"},
    )
    session.add(v1)
    session.flush()
    v2 = LearningPath(
        id=uuid.uuid4(),
        user_id=user.id,
        role_id=role_id,
        version=2,
        status=PathStatus.ACTIVE.value,
        parent_path_id=v1.id,
        extra_metadata={"note": "v2"},
    )
    session.add(v2)
    session.flush()
    session.add(
        PathItem(
            id=uuid.uuid4(),
            learning_path_id=v2.id,
            item_type="RESOURCE",
            position=0,
            week_index=1,
            status="PENDING",
            score_breakdown={
                "skill_gap": 0.87,
                "role_importance": 0.92,
                "prerequisite_fit": 1.0,
                "difficulty_fit": 0.81,
                "duration_fit": 0.74,
                "style_fit": 0.90,
                "semantic_similarity": 0.83,
                "final_score": 0.86,
            },
            explanation_metadata={"why_this": "schema-only fixture"},
        )
    )
    session.add(
        AdaptationEvent(
            id=uuid.uuid4(),
            user_id=user.id,
            from_path_id=v1.id,
            to_path_id=v2.id,
            event_type=AdaptationEventType.REMEDIATION_INSERTED.value,
            summary="Schema check: v1 remains after v2 is created.",
            details={"inserted": ["probability-foundations"]},
        )
    )
    session.commit()
    kept_v1 = session.get(LearningPath, v1.id)
    kept_v2 = session.get(LearningPath, v2.id)
    assert kept_v1 is not None and kept_v2 is not None
    assert kept_v1.status == PathStatus.SUPERSEDED.value
    assert kept_v2.parent_path_id == v1.id
    session.query(AdaptationEvent).filter(AdaptationEvent.user_id == user.id).delete()
    session.query(PathItem).filter(PathItem.learning_path_id.in_([v1.id, v2.id])).delete()
    session.delete(v2)
    session.delete(v1)
    session.delete(user)
    session.commit()
