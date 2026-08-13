"""Slice 3 API: assessment attempts, path diff, complete-item.

Handlers stay thin — scoring lives in services/assessment, adaptation in
services/adaptation. No scoring or adaptation math here.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import PathItemStatus
from app.db.session import get_session
from app.models import AdaptationEvent, AssessmentAttempt, LearningPath, PathItem, User
from app.ontology.load import load_ontology
from app.schemas.intelligence import (
    AssessmentAttemptCreate,
    AssessmentAttemptRead,
    CompleteItemCreate,
    PathDiffRead,
    PathItemCompleteRead,
    SkillResultRead,
    SuggestedAssessmentRead,
)
from app.services.assessment.loader import AssessmentDriftError
from app.services.assessment import runtime
from app.services.assessment.selection import select_assessment
from app.services.profiling import repository as profiling

router = APIRouter(prefix="/v1")


def _learner(session: Session, learner_id: UUID) -> User:
    user = session.get(User, learner_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Learner not found")
    return user


def _owned_path(session: Session, learner_id: UUID, path_id: UUID) -> LearningPath:
    path = session.get(LearningPath, path_id)
    if path is None or path.user_id != learner_id:
        raise HTTPException(status_code=404, detail="Path not found")
    return path


@router.post(
    "/learners/{learner_id}/assessments/{slug}/attempts",
    response_model=AssessmentAttemptRead,
)
def submit_assessment_attempt(
    learner_id: UUID,
    slug: str,
    payload: AssessmentAttemptCreate,
    session: Session = Depends(get_session),
) -> AssessmentAttemptRead:
    _learner(session, learner_id)
    try:
        outcome = runtime.submit_attempt(
            session,
            user_id=learner_id,
            assessment_slug=slug,
            answers=payload.answers,
            attempt_id=payload.attempt_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AssessmentDriftError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": exc.code, "message": str(exc), "assessment": exc.slug},
        ) from exc

    if outcome.adaptation == "REPLAYED":
        # Stored result is authoritative; re-read it for the response.
        attempt = session.get(AssessmentAttempt, outcome.attempt_id)
        result = (attempt.result or {}) if attempt else {}
        return AssessmentAttemptRead(
            attempt_id=outcome.attempt_id,
            attempt_number=outcome.attempt_number,
            assessment=slug,
            overall_score=result.get("overall_score", 0.0),
            passed=result.get("passed", False),
            skill_results=[SkillResultRead(**item) for item in result.get("skill_results", [])],
            adaptation="REPLAYED",
            path_id=outcome.path_id,
            diff=result.get("diff"),
        )

    return AssessmentAttemptRead(
        attempt_id=outcome.attempt_id,
        attempt_number=outcome.attempt_number,
        assessment=slug,
        overall_score=round(outcome.score.overall_score, 6),
        passed=outcome.score.passed,
        skill_results=[SkillResultRead(**item.as_dict()) for item in outcome.score.skill_results],
        adaptation=outcome.adaptation,
        path_id=outcome.path_id,
        diff=outcome.diff.as_dict() if outcome.diff else None,
    )


@router.get(
    "/learners/{learner_id}/paths/{path_id}/diff",
    response_model=PathDiffRead,
)
def path_diff(
    learner_id: UUID,
    path_id: UUID,
    session: Session = Depends(get_session),
) -> PathDiffRead:
    _learner(session, learner_id)
    path = _owned_path(session, learner_id, path_id)
    event = session.scalars(
        select(AdaptationEvent)
        .where(AdaptationEvent.to_path_id == path.id)
        .order_by(AdaptationEvent.created_at.desc())
    ).first()
    if event is None:
        return PathDiffRead(
            path_id=path.id,
            from_path_id=path.parent_path_id,
            trigger_type=None,
            changed_skills=[],
            added=[],
            removed=[],
            moved=[],
            unchanged=[],
            blocked=[],
        )
    changes = event.changes or {}
    return PathDiffRead(
        path_id=path.id,
        from_path_id=event.from_path_id,
        trigger_type=event.trigger_type,
        changed_skills=list(event.changed_skills or []),
        added=list(changes.get("added", [])),
        removed=list(changes.get("removed", [])),
        moved=list(changes.get("moved", [])),
        unchanged=list(changes.get("unchanged", [])),
        blocked=list(changes.get("blocked", [])),
    )


@router.post(
    "/learners/{learner_id}/paths/{path_id}/complete-item",
    response_model=PathItemCompleteRead,
)
def complete_path_item(
    learner_id: UUID,
    path_id: UUID,
    payload: CompleteItemCreate,
    session: Session = Depends(get_session),
) -> PathItemCompleteRead:
    _learner(session, learner_id)
    path = _owned_path(session, learner_id, path_id)
    item = session.scalar(
        select(PathItem).where(
            PathItem.learning_path_id == path.id,
            PathItem.position == payload.position,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Path item not found")
    if item.status == PathItemStatus.COMPLETED.value:
        raise HTTPException(status_code=409, detail="Item already completed")
    meta = item.explanation_metadata or {}
    executable = bool(meta.get("executable")) and item.status == PathItemStatus.PENDING.value
    if not executable:
        raise HTTPException(
            status_code=422,
            detail="Item is not executable (waiting items cannot be completed)",
        )
    item.status = PathItemStatus.COMPLETED.value
    session.commit()
    return PathItemCompleteRead(
        path_id=path.id,
        position=item.position,
        status=item.status,
        item_type=item.item_type,
    )


@router.get(
    "/learners/{learner_id}/roles/{role_slug}/assessments/suggested",
    response_model=SuggestedAssessmentRead,
)
def suggested_assessment(
    learner_id: UUID,
    role_slug: str,
    session: Session = Depends(get_session),
) -> SuggestedAssessmentRead:
    _learner(session, learner_id)
    try:
        profile = profiling.compute_gap_profile(session, user_id=learner_id, role_slug=role_slug)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    bundle = load_ontology()
    spec = select_assessment(profile, bundle.assessments)
    if spec is None:
        return SuggestedAssessmentRead(
            assessment=None,
            title=None,
            question_count=None,
            covers=[],
            reason="No UNKNOWN role-relevant skills require verification.",
        )
    covers = [
        skill
        for skill in spec.target_skills
        if any(
            item.ranked.gap.skill_slug == skill
            and item.ranked.gap.evidence_state.value == "UNKNOWN"
            for item in profile.items
        )
    ]
    return SuggestedAssessmentRead(
        assessment=spec.slug,
        title=spec.title,
        question_count=len(spec.questions),
        covers=covers,
        reason=(
            f"Smallest assessment covering the highest-priority UNKNOWN skills "
            f"for {profile.role_name}."
        ),
    )
