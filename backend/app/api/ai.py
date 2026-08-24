"""Grounded explanation API. Never mutates learner, path, or assessment state."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models import User
from app.schemas.intelligence import (
    AIClaimRead,
    AIExplainRead,
    AIExplainRequest,
    AIFactRead,
)
from app.services.explanation.schema import Intent
from app.services.explanation.service import explain

router = APIRouter(prefix="/v1")

_INTENTS: set[str] = {
    "WHY_GAP",
    "WHY_RESOURCE",
    "WHAT_CHANGED",
    "NEXT_ACTION",
    "COACH",
    "QUERY",
}


def _learner(session: Session, learner_id: UUID) -> User:
    user = session.get(User, learner_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Learner not found")
    return user


@router.post("/learners/{learner_id}/ai/explain", response_model=AIExplainRead)
def explain_intelligence(
    learner_id: UUID,
    payload: AIExplainRequest,
    session: Session = Depends(get_session),
) -> AIExplainRead:
    _learner(session, learner_id)
    intent = (payload.intent or "QUERY").upper()
    if intent not in _INTENTS:
        raise HTTPException(status_code=422, detail="Unknown explanation intent")
    query = None
    if payload.query:
        query = "".join(ch for ch in payload.query if ch.isprintable())[:500]
    try:
        result = explain(
            session,
            user_id=learner_id,
            intent=intent,  # type: ignore[arg-type]
            skill=payload.skill,
            resource=payload.resource,
            query=query,
        )
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AIExplainRead(
        answer=result.answer,
        claims=[AIClaimRead(text=item.text, fact_ids=item.fact_ids) for item in result.claims],
        confidence=result.confidence,
        source=result.source,
        facts=[AIFactRead(id=item.id, label=item.label, value=item.value) for item in result.facts],
        intent=result.intent,
    )
