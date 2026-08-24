"""Database adapters for profiling and gap analysis. No ranking math here."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import EvidenceSource, RequiredStatus
from app.core.reliability import reliability_for
from app.models import Role, RoleSkill, Skill, SkillEvidence, SkillRelationship, User, UserSkill
from app.services.gap_engine.profile import GapProfile, build_gap_profile
from app.services.profiling.evidence_fusion import EvidenceRecord, FusedSkill, fuse_skill_evidence
from app.services.skill_graph.competency import RoleCompetency, RoleCompetencySet
from app.services.skill_graph.dependency import SkillEdge


def create_learner(session: Session, display_name: str, *, is_demo: bool = False) -> User:
    user = User(id=uuid.uuid4(), display_name=display_name, is_demo=is_demo)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def append_evidence(
    session: Session,
    *,
    user_id: uuid.UUID,
    skill_slug: str,
    source: str,
    observed_level: float,
    confidence: float,
    created_at: datetime | None = None,
    payload: dict | None = None,
    commit: bool = True,
) -> SkillEvidence:
    EvidenceSource(source)
    skill = session.scalar(select(Skill).where(Skill.slug == skill_slug))
    if skill is None:
        raise KeyError(f"Unknown skill slug: {skill_slug}")
    if not 0.0 <= observed_level <= 1.0:
        raise ValueError("observed_level must be in [0, 1]")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be in [0, 1]")

    row = SkillEvidence(
        id=uuid.uuid4(),
        user_id=user_id,
        skill_id=skill.id,
        source_type=source,
        observed_level=observed_level,
        reliability=reliability_for(source),
        confidence=confidence,
        evidence_payload=payload or {"skill_slug": skill_slug},
        created_at=created_at or datetime.now(timezone.utc),
    )
    session.add(row)
    session.flush()
    _refresh_fused_skill(session, user_id=user_id, skill=skill)
    if commit:
        session.commit()
    else:
        session.flush()
    session.refresh(row)
    return row


def _refresh_fused_skill(session: Session, *, user_id: uuid.UUID, skill: Skill) -> FusedSkill:
    fused = fuse_user_skill(session, user_id=user_id, skill_slug=skill.slug)
    existing = session.get(UserSkill, (user_id, skill.id))
    payload = {
        "proficiency": fused.proficiency,
        "confidence": fused.confidence,
        "status": fused.status.value,
        "evidence_summary": {
            "count": fused.evidence_count,
            "conflict": fused.conflict,
            "dominant_source": fused.dominant_source,
            "reason": fused.reason,
        },
        "last_updated": datetime.now(timezone.utc),
    }
    if existing is None:
        session.add(UserSkill(user_id=user_id, skill_id=skill.id, **payload))
    else:
        for key, value in payload.items():
            setattr(existing, key, value)
    return fused


def list_evidence_rows(
    session: Session,
    user_id: uuid.UUID,
    *,
    skill_slug: str | None = None,
) -> list[SkillEvidence]:
    query = select(SkillEvidence).where(SkillEvidence.user_id == user_id)
    if skill_slug is not None:
        skill = session.scalar(select(Skill).where(Skill.slug == skill_slug))
        if skill is None:
            return []
        query = query.where(SkillEvidence.skill_id == skill.id)
    return list(
        session.scalars(query.order_by(SkillEvidence.created_at.asc())).all()
    )


def load_evidence_records(session: Session, user_id: uuid.UUID) -> list[EvidenceRecord]:
    rows = session.scalars(
        select(SkillEvidence)
        .where(SkillEvidence.user_id == user_id)
        .order_by(SkillEvidence.created_at.asc())
    ).all()
    if not rows:
        return []
    skill_ids = {row.skill_id for row in rows}
    slugs = {
        skill.id: skill.slug
        for skill in session.scalars(select(Skill).where(Skill.id.in_(skill_ids))).all()
    }
    return [
        EvidenceRecord(
            skill_slug=slugs[row.skill_id],
            source=row.source_type,
            observed_level=row.observed_level,
            reliability=row.reliability,
            confidence=row.confidence,
            created_at=row.created_at,
        )
        for row in rows
    ]


def fuse_user_skill(session: Session, *, user_id: uuid.UUID, skill_slug: str) -> FusedSkill:
    records = [
        item for item in load_evidence_records(session, user_id) if item.skill_slug == skill_slug
    ]
    return fuse_skill_evidence(records, skill_slug=skill_slug)


def fuse_all_skills(session: Session, user_id: uuid.UUID) -> dict[str, FusedSkill]:
    grouped: dict[str, list[EvidenceRecord]] = defaultdict(list)
    for record in load_evidence_records(session, user_id):
        grouped[record.skill_slug].append(record)
    return {
        slug: fuse_skill_evidence(records, skill_slug=slug) for slug, records in grouped.items()
    }


def load_role_competencies(session: Session, role_slug: str) -> RoleCompetencySet:
    role = session.scalar(select(Role).where(Role.slug == role_slug))
    if role is None:
        raise KeyError(f"Unknown role: {role_slug}")
    rows = session.execute(
        select(RoleSkill, Skill)
        .join(Skill, Skill.id == RoleSkill.skill_id)
        .where(RoleSkill.role_id == role.id)
    ).all()
    competencies = tuple(
        RoleCompetency(
            skill_slug=skill.slug,
            skill_name=skill.canonical_name,
            target_level=role_skill.target_level,
            importance=role_skill.importance,
            required_status=RequiredStatus(role_skill.required_status),
        )
        for role_skill, skill in rows
    )
    return RoleCompetencySet(
        role_slug=role.slug, role_name=role.name, competencies=competencies
    )


def load_skill_edges(session: Session) -> list[SkillEdge]:
    slugs = {skill.id: skill.slug for skill in session.scalars(select(Skill)).all()}
    return [
        SkillEdge(
            source=slugs[rel.source_skill_id],
            target=slugs[rel.target_skill_id],
            relationship_type=rel.relationship_type,
            strength=rel.strength,
        )
        for rel in session.scalars(select(SkillRelationship)).all()
    ]


def compute_gap_profile(session: Session, *, user_id: uuid.UUID, role_slug: str) -> GapProfile:
    fused = fuse_all_skills(session, user_id)
    role = load_role_competencies(session, role_slug)
    edges = load_skill_edges(session)
    return build_gap_profile(fused_by_slug=fused, role=role, edges=edges)
