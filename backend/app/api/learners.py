from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models import Profile, Role, Skill, User
from app.schemas.intelligence import (
    DashboardRead,
    EvidenceCreate,
    EvidenceRead,
    FusedSkillRead,
    GapItemRead,
    GapProfileRead,
    LearnerCreate,
    LearnerRead,
)
from app.services.dashboard.summary import build_dashboard
from app.services.profiling import repository as profiling

router = APIRouter(prefix="/v1")


def _learner(session: Session, learner_id: UUID) -> User:
    user = session.get(User, learner_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Learner not found")
    return user


@router.post("/learners", response_model=LearnerRead)
def create_learner(payload: LearnerCreate, session: Session = Depends(get_session)) -> LearnerRead:
    user = profiling.create_learner(
        session,
        payload.display_name,
        experience_level=payload.experience_level,
        weekly_hours=payload.weekly_hours,
        learning_style=payload.learning_style,
        timeline_weeks=payload.timeline_weeks,
        interests=payload.interests,
        target_role_slug=payload.target_role,
        goal_text=payload.goal_text,
    )
    profile = session.scalar(select(Profile).where(Profile.user_id == user.id))
    role_slug = None
    if profile and profile.target_role_id:
        role = session.get(Role, profile.target_role_id)
        role_slug = role.slug if role else None
    return LearnerRead(
        id=user.id,
        display_name=user.display_name,
        is_demo=user.is_demo,
        experience_level=profile.experience_level if profile else None,
        weekly_hours=float(profile.weekly_hours) if profile and profile.weekly_hours else None,
        learning_style=profile.learning_style if profile else None,
        timeline_weeks=profile.timeline_weeks if profile else None,
        interests=list(profile.interests or []) if profile and profile.interests else None,
        goal_text=profile.goal_text if profile else payload.goal_text,
        target_role=role_slug,
    )


@router.post("/learners/{learner_id}/evidence", response_model=EvidenceRead)
def add_evidence(
    learner_id: UUID,
    payload: EvidenceCreate,
    session: Session = Depends(get_session),
) -> EvidenceRead:
    _learner(session, learner_id)
    try:
        row = profiling.append_evidence(
            session,
            user_id=learner_id,
            skill_slug=payload.skill,
            source=payload.source,
            observed_level=payload.observed_level,
            confidence=payload.confidence,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return EvidenceRead(
        id=row.id,
        skill=payload.skill,
        source=row.source_type,
        observed_level=row.observed_level,
        reliability=row.reliability,
        confidence=row.confidence,
        created_at=row.created_at,
    )


@router.get("/learners/{learner_id}/evidence", response_model=list[EvidenceRead])
def list_evidence(
    learner_id: UUID,
    skill: str | None = Query(default=None, min_length=1, max_length=80),
    session: Session = Depends(get_session),
) -> list[EvidenceRead]:
    _learner(session, learner_id)
    rows = profiling.list_evidence_rows(session, learner_id, skill_slug=skill)
    if not rows:
        return []
    skill_ids = {row.skill_id for row in rows}
    slugs = {
        item.id: item.slug
        for item in session.scalars(select(Skill).where(Skill.id.in_(skill_ids))).all()
    }
    return [
        EvidenceRead(
            id=row.id,
            skill=slugs.get(row.skill_id, ""),
            source=row.source_type,
            observed_level=row.observed_level,
            reliability=row.reliability,
            confidence=row.confidence,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/learners/{learner_id}/skills", response_model=list[FusedSkillRead])
def learner_skills(learner_id: UUID, session: Session = Depends(get_session)) -> list[FusedSkillRead]:
    _learner(session, learner_id)
    fused = profiling.fuse_all_skills(session, learner_id)
    return [
        FusedSkillRead(
            skill=item.skill_slug,
            proficiency=item.proficiency,
            confidence=item.confidence,
            status=item.status.value,
            evidence_count=item.evidence_count,
            conflict=item.conflict,
            conflict_spread=item.conflict_spread,
            dominant_source=item.dominant_source,
            reason=item.reason,
        )
        for item in fused.values()
    ]


@router.get("/learners/{learner_id}/roles/{role_slug}/gaps", response_model=GapProfileRead)
def learner_gaps(
    learner_id: UUID,
    role_slug: str,
    session: Session = Depends(get_session),
) -> GapProfileRead:
    _learner(session, learner_id)
    try:
        profile = profiling.compute_gap_profile(session, user_id=learner_id, role_slug=role_slug)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return GapProfileRead(
        role=profile.role_slug,
        name=profile.role_name,
        items=[
            GapItemRead(
                skill=item.ranked.gap.skill_slug,
                name=item.ranked.gap.skill_name,
                target_level=item.ranked.gap.target_level,
                importance=item.ranked.gap.importance,
                required_status=item.ranked.gap.required_status,
                proficiency=item.ranked.gap.proficiency,
                confidence=item.ranked.gap.confidence,
                gap=item.ranked.gap.gap,
                normalized_gap=item.ranked.gap.normalized_gap,
                gap_status=item.ranked.gap.gap_status.value,
                severity=item.ranked.severity.value,
                priority=item.ranked.priority,
                is_blocking=item.ranked.is_blocking,
                hard_downstream=list(item.ranked.impact.hard_role_descendants),
                soft_downstream=list(item.ranked.impact.soft_role_descendants),
                prerequisite_criticality=item.ranked.prerequisite_criticality,
                evidence_count=item.ranked.gap.evidence_count,
                conflict=item.ranked.gap.conflict,
                dominant_source=item.ranked.gap.dominant_source,
                explanation=item.explanation,
                evidence_state=item.ranked.gap.evidence_state.value,
                attainment=item.ranked.gap.attainment.value,
                target_met=item.ranked.gap.target_met,
                gap_priority=item.ranked.gap_priority,
                verification_priority=item.ranked.verification_priority,
                action=item.action.value,
                action_priority=item.action_priority,
                blocked=item.gate.blocked,
                blockers=list(item.gate.blockers),
                preparation_needed=item.gate.preparation_needed,
                preparation_skills=list(item.gate.preparation_skills),
                downstream_impact=item.downstream_impact,
            )
            for item in profile.items
        ],
    )


@router.get("/learners/{learner_id}/roles/{role_slug}/dashboard", response_model=DashboardRead)
def learner_dashboard(
    learner_id: UUID,
    role_slug: str,
    session: Session = Depends(get_session),
) -> DashboardRead:
    _learner(session, learner_id)
    try:
        return build_dashboard(session, user_id=learner_id, role_slug=role_slug)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
