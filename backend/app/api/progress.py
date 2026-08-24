"""Progress feedback routes.

Outcome → evidence → fusion → adaptation lives in services/progress/feedback.py.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.intelligence import ProgressFeedbackCreate, ProgressFeedbackRead
from app.services.progress.feedback import record_feedback

router = APIRouter(prefix="/v1")


@router.post(
    "/learners/{learner_id}/progress",
    response_model=ProgressFeedbackRead,
)
def submit_progress(
    learner_id: UUID,
    payload: ProgressFeedbackCreate,
    session: Session = Depends(get_session),
) -> ProgressFeedbackRead:
    """Record how a path step went and re-plan when learner state changes materially."""
    try:
        outcome = record_feedback(
            session,
            user_id=learner_id,
            path_id=payload.path_id,
            position=payload.position,
            outcome=payload.outcome,
            self_reported_level=payload.self_reported_level,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ProgressFeedbackRead(
        path_id=payload.path_id,
        position=outcome.position,
        outcome=outcome.outcome,
        item_status=outcome.item_status,
        target_skill=outcome.target_skill,
        evidence_recorded=outcome.evidence_recorded,
        observed_level=outcome.observed_level,
        adaptation=outcome.adaptation,
        new_path_id=outcome.path_id,
        diff=outcome.diff.as_dict() if outcome.diff else None,
        summary=outcome.summary,
    )
