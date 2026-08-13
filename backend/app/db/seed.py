"""Deterministic, idempotent ontology/catalog import.

YAML is the source of truth. Re-running seed upserts by stable UUIDv5(slug).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import ontology_uuid
from app.models import (
    Assessment,
    AssessmentQuestion,
    LearningResource,
    ResourcePrerequisite,
    ResourceSkill,
    Role,
    RoleSkill,
    Skill,
    SkillRelationship,
)
from app.ontology.load import OntologyBundle, load_ontology
from app.ontology.validate import assert_valid


def _upsert_skill(session: Session, slug: str, **fields) -> Skill:
    skill_id = ontology_uuid("skill", slug)
    skill = session.get(Skill, skill_id)
    if skill is None:
        skill = Skill(id=skill_id, slug=slug, **fields)
        session.add(skill)
    else:
        for key, value in fields.items():
            setattr(skill, key, value)
    return skill


def seed_ontology(session: Session, bundle: OntologyBundle | None = None) -> OntologyBundle:
    bundle = bundle or load_ontology()
    assert_valid(bundle)

    for spec in bundle.skills:
        _upsert_skill(
            session,
            spec.slug,
            canonical_name=spec.canonical_name,
            category=spec.category,
            description=spec.description,
        )
    session.flush()

    for spec in bundle.relationships:
        rel_id = ontology_uuid("rel", f"{spec.source}:{spec.target}:{spec.type}")
        rel = session.get(SkillRelationship, rel_id)
        payload = dict(
            source_skill_id=ontology_uuid("skill", spec.source),
            target_skill_id=ontology_uuid("skill", spec.target),
            relationship_type=spec.type,
            strength=spec.strength,
            rationale=spec.rationale,
        )
        if rel is None:
            session.add(SkillRelationship(id=rel_id, **payload))
        else:
            for key, value in payload.items():
                setattr(rel, key, value)

    for spec in bundle.roles:
        role_id = ontology_uuid("role", spec.slug)
        role = session.get(Role, role_id)
        fields = dict(slug=spec.slug, name=spec.name, description=spec.description)
        if role is None:
            session.add(Role(id=role_id, **fields))
        else:
            for key, value in fields.items():
                setattr(role, key, value)
        session.flush()
        for rs in spec.skills:
            rs_id = ontology_uuid("role_skill", f"{spec.slug}:{rs.slug}")
            row = session.get(RoleSkill, rs_id)
            payload = dict(
                role_id=role_id,
                skill_id=ontology_uuid("skill", rs.slug),
                target_level=rs.target_level,
                importance=rs.importance,
                required_status=rs.required_status,
            )
            if row is None:
                session.add(RoleSkill(id=rs_id, **payload))
            else:
                for key, value in payload.items():
                    setattr(row, key, value)

    for spec in bundle.resources:
        res_id = ontology_uuid("resource", spec.slug)
        resource = session.get(LearningResource, res_id)
        fields = dict(
            slug=spec.slug,
            title=spec.title,
            description=spec.description,
            type=spec.type,
            difficulty=spec.difficulty,
            duration_hours=spec.duration_hours,
            source=spec.source,
            url=spec.url,
            url_status=spec.url_status,
            learning_modes=spec.learning_modes,
            is_active=spec.is_active,
        )
        if resource is None:
            session.add(LearningResource(id=res_id, **fields))
        else:
            for key, value in fields.items():
                setattr(resource, key, value)
        session.flush()

        existing_rs = session.scalars(
            select(ResourceSkill).where(ResourceSkill.resource_id == res_id)
        ).all()
        for row in existing_rs:
            session.delete(row)
        existing_pr = session.scalars(
            select(ResourcePrerequisite).where(ResourcePrerequisite.resource_id == res_id)
        ).all()
        for row in existing_pr:
            session.delete(row)
        session.flush()

        for rs in spec.skills:
            session.add(
                ResourceSkill(
                    id=ontology_uuid("resource_skill", f"{spec.slug}:{rs.slug}"),
                    resource_id=res_id,
                    skill_id=ontology_uuid("skill", rs.slug),
                    coverage_strength=rs.coverage_strength,
                    expected_level_delta=rs.expected_level_delta,
                    is_primary=rs.is_primary,
                )
            )
        for prereq in spec.prerequisites:
            session.add(
                ResourcePrerequisite(
                    id=ontology_uuid("resource_prereq", f"{spec.slug}:{prereq.slug}"),
                    resource_id=res_id,
                    skill_id=ontology_uuid("skill", prereq.slug),
                    min_level=prereq.min_level,
                )
            )

    for spec in bundle.assessments:
        a_id = ontology_uuid("assessment", spec.slug)
        assessment = session.get(Assessment, a_id)
        fields = dict(
            slug=spec.slug,
            title=spec.title,
            description=spec.description,
            primary_skill_id=ontology_uuid("skill", spec.primary_skill),
            pass_threshold=spec.pass_threshold,
        )
        if assessment is None:
            session.add(Assessment(id=a_id, **fields))
        else:
            for key, value in fields.items():
                setattr(assessment, key, value)
        session.flush()

        existing_q = session.scalars(
            select(AssessmentQuestion).where(AssessmentQuestion.assessment_id == a_id)
        ).all()
        for row in existing_q:
            session.delete(row)
        session.flush()

        for position, question in enumerate(spec.questions):
            session.add(
                AssessmentQuestion(
                    id=ontology_uuid("question", f"{spec.slug}:{position}"),
                    assessment_id=a_id,
                    position=position,
                    prompt=question.prompt,
                    skill_id=ontology_uuid("skill", question.skill),
                    difficulty=question.difficulty,
                    choices=question.choices,
                    correct_index=question.correct_index,
                    explanation=question.explanation,
                    concept_tag=question.concept_tag,
                )
            )

    yaml_slugs = {spec.slug for spec in bundle.resources}
    for row in session.scalars(select(LearningResource)).all():
        if row.slug not in yaml_slugs and row.is_active:
            row.is_active = False

    session.commit()
    return bundle
