"""Load assessment definitions from the database (runtime authority)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Assessment, AssessmentQuestion, Role, Skill
from app.ontology.load import AssessmentSpec, QuestionSpec
from app.services.assessment.fingerprint import assessment_fingerprint


class AssessmentDriftError(Exception):
    """YAML definition differs from the seeded database definition."""

    code = "DRIFT_DETECTED"

    def __init__(self, slug: str, *, db_hash: str, yaml_hash: str):
        self.slug = slug
        self.db_hash = db_hash
        self.yaml_hash = yaml_hash
        super().__init__(
            f"Assessment '{slug}' definition drift detected "
            f"(db={db_hash[:12]}… yaml={yaml_hash[:12]}…). Reseed required."
        )


def spec_from_db_row(
    assessment: Assessment,
    questions: list[AssessmentQuestion],
    skill_slugs: dict[uuid.UUID, str],
    *,
    target_role_slug: str | None,
) -> AssessmentSpec:
    ordered = sorted(questions, key=lambda row: row.position)
    return AssessmentSpec(
        slug=assessment.slug,
        title=assessment.title,
        description=assessment.description,
        primary_skill=skill_slugs[assessment.primary_skill_id],
        pass_threshold=assessment.pass_threshold,
        questions=[
            QuestionSpec(
                prompt=row.prompt,
                skill=skill_slugs[row.skill_id],
                difficulty=row.difficulty,
                choices=list(row.choices),
                correct_index=row.correct_index,
                explanation=row.explanation,
                concept_tag=row.concept_tag,
            )
            for row in ordered
        ],
        target_role=target_role_slug,
        target_skills=list(assessment.target_skills or []),
    )


def load_assessment_spec(
    session: Session,
    *,
    assessment_id: uuid.UUID,
    yaml_spec: AssessmentSpec | None = None,
) -> AssessmentSpec:
    """Return the DB-backed assessment spec; refuse if YAML drifts from DB."""
    assessment = session.scalar(
        select(Assessment)
        .where(Assessment.id == assessment_id)
        .options(selectinload(Assessment.questions))
    )
    if assessment is None:
        raise KeyError(f"Assessment not seeded: {assessment_id}")

    skill_ids = {assessment.primary_skill_id}
    for row in assessment.questions:
        skill_ids.add(row.skill_id)
    skill_rows = session.scalars(select(Skill).where(Skill.id.in_(skill_ids))).all()
    skill_slugs = {row.id: row.slug for row in skill_rows}

    target_role_slug: str | None = None
    if assessment.target_role_id is not None:
        role = session.get(Role, assessment.target_role_id)
        if role is not None:
            target_role_slug = role.slug

    spec = spec_from_db_row(
        assessment,
        list(assessment.questions),
        skill_slugs,
        target_role_slug=target_role_slug,
    )

    if not assessment.definition_hash:
        raise AssessmentDriftError(
            assessment.slug,
            db_hash="",
            yaml_hash=assessment_fingerprint(spec),
        )

    db_hash = assessment.definition_hash
    computed = assessment_fingerprint(spec)
    if db_hash != computed:
        raise AssessmentDriftError(assessment.slug, db_hash=db_hash, yaml_hash=computed)

    if yaml_spec is not None:
        yaml_hash = assessment_fingerprint(yaml_spec)
        if yaml_hash != db_hash:
            raise AssessmentDriftError(assessment.slug, db_hash=db_hash, yaml_hash=yaml_hash)

    return spec
