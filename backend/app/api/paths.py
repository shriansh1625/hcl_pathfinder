"""Thin path and recommendation routes. Intelligence lives in services."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import LearningStyle
from app.db.session import get_session
from app.models import LearningPath, PathItem, Role, User
from app.ontology.load import load_ontology
from app.schemas.intelligence import (
    PathCreate,
    PathItemRead,
    PathRead,
    RecommendationRead,
)
from app.services.path.generator import generate_path
from app.services.path.repository import persist_path, upsert_preferences
from app.services.profiling import repository as profiling
from app.services.recommendation.models import LearnerPreferences
from app.services.recommendation.scorer import score_candidates
from app.services.retrieval.structured import retrieve_candidates

router = APIRouter(prefix="/v1")


def _learner(session: Session, learner_id: UUID) -> User:
    user = session.get(User, learner_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Learner not found")
    return user


def _prefs(weekly_hours: float, learning_style: str) -> LearnerPreferences:
    try:
        style = LearningStyle(learning_style).value
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid learning_style") from exc
    return LearnerPreferences(weekly_hours=weekly_hours, learning_style=style)


def _item_read(row: PathItem) -> PathItemRead:
    meta = row.explanation_metadata or {}
    return PathItemRead(
        position=row.position,
        week=row.week_index,
        resource=meta.get("resource_slug") or "",
        title=meta.get("title") or "",
        type=meta.get("type") or row.item_type,
        target_skill=meta.get("target_skill") or "",
        intervention=meta.get("intervention") or "",
        eligibility=meta.get("eligibility") or "",
        duration_hours=float(meta.get("duration_hours") or 0),
        url=meta.get("url"),
        score_breakdown=row.score_breakdown or {},
        explanation=meta.get("explanation") or "",
        prerequisites=list(meta.get("prerequisites") or []),
    )


def _path_read(session: Session, path: LearningPath, role_slug: str) -> PathRead:
    meta = path.extra_metadata or {}
    items = session.scalars(
        select(PathItem)
        .where(PathItem.learning_path_id == path.id)
        .order_by(PathItem.position)
    ).all()
    return PathRead(
        id=path.id,
        role=role_slug,
        version=path.version,
        status=path.status,
        weekly_hours=float(meta.get("weekly_hours") or 0),
        learning_style=str(meta.get("learning_style") or "MIXED"),
        total_estimated_hours=path.total_estimated_hours,
        items=[_item_read(item) for item in items],
    )


@router.post("/learners/{learner_id}/paths", response_model=PathRead)
def create_path(
    learner_id: UUID,
    payload: PathCreate,
    session: Session = Depends(get_session),
) -> PathRead:
    _learner(session, learner_id)
    prefs = _prefs(payload.weekly_hours, payload.learning_style)
    try:
        gap = profiling.compute_gap_profile(session, user_id=learner_id, role_slug=payload.role)
        edges = profiling.load_skill_edges(session)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    catalog = [item for item in load_ontology().resources if item.is_active]
    planned = generate_path(gap, catalog, edges, prefs)
    upsert_preferences(session, learner_id, prefs, role_slug=payload.role)
    path = persist_path(session, user_id=learner_id, planned=planned)
    return _path_read(session, path, payload.role)


@router.get("/learners/{learner_id}/paths", response_model=list[PathRead])
def list_paths(learner_id: UUID, session: Session = Depends(get_session)) -> list[PathRead]:
    _learner(session, learner_id)
    rows = session.scalars(
        select(LearningPath).where(LearningPath.user_id == learner_id)
    ).all()
    result: list[PathRead] = []
    for path in rows:
        role = session.get(Role, path.role_id)
        result.append(_path_read(session, path, role.slug if role else ""))
    result.sort(key=lambda item: item.version, reverse=True)
    return result


@router.get("/learners/{learner_id}/paths/{path_id}", response_model=PathRead)
def get_path(learner_id: UUID, path_id: UUID, session: Session = Depends(get_session)) -> PathRead:
    _learner(session, learner_id)
    path = session.get(LearningPath, path_id)
    if path is None or path.user_id != learner_id:
        raise HTTPException(status_code=404, detail="Path not found")
    role = session.get(Role, path.role_id)
    return _path_read(session, path, role.slug if role else "")


@router.get(
    "/learners/{learner_id}/roles/{role_slug}/recommendations",
    response_model=list[RecommendationRead],
)
def recommendations(
    learner_id: UUID,
    role_slug: str,
    weekly_hours: float = 8,
    learning_style: str = "MIXED",
    session: Session = Depends(get_session),
) -> list[RecommendationRead]:
    _learner(session, learner_id)
    prefs = _prefs(weekly_hours, learning_style)
    try:
        gap = profiling.compute_gap_profile(session, user_id=learner_id, role_slug=role_slug)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    catalog = retrieve_candidates(gap, [item for item in load_ontology().resources if item.is_active])
    scored = score_candidates(catalog, gap, prefs)
    return [
        RecommendationRead(
            resource=item.resource.slug,
            title=item.resource.title,
            primary_skill=item.primary_skill,
            intervention=item.intervention.value,
            eligibility=item.eligibility.status.value,
            final_score=item.breakdown.final_score,
            score_breakdown=item.breakdown.as_dict(),
            explanation=item.explanation,
        )
        for item in scored[:20]
    ]
