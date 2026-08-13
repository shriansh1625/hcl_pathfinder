"""Persist adapted paths + adaptation events. Flush only — the caller owns
the transaction boundary so assessment → evidence → adaptation is atomic."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.enums import PathStatus
from app.core.ids import ontology_uuid
from app.models import AdaptationEvent, LearningPath, PathItem
from app.services.adaptation.diff import PathDiff
from app.services.adaptation.engine import V2Item


def persist_adapted_path(
    session: Session,
    *,
    user_id: uuid.UUID,
    previous: LearningPath,
    items: list[V2Item] | tuple[V2Item, ...],
    total_estimated_hours: float,
    weekly_hours: int,
    learning_style: str,
    role_slug: str,
    quality: dict | None,
) -> LearningPath:
    previous.status = PathStatus.SUPERSEDED.value
    path = LearningPath(
        id=uuid.uuid4(),
        user_id=user_id,
        role_id=previous.role_id,
        version=previous.version + 1,
        status=PathStatus.ACTIVE.value,
        parent_path_id=previous.id,
        generated_at=datetime.now(timezone.utc),
        total_estimated_hours=total_estimated_hours,
        extra_metadata={
            "weekly_hours": weekly_hours,
            "learning_style": learning_style,
            "role": role_slug,
            "quality": quality,
            "adapted_from": str(previous.id),
        },
    )
    session.add(path)
    session.flush()
    for item in items:
        resource_id = (
            ontology_uuid("resource", item.resource_slug) if item.resource_slug else None
        )
        session.add(
            PathItem(
                id=uuid.uuid4(),
                learning_path_id=path.id,
                resource_id=resource_id,
                assessment_id=None,
                item_type=item.item_type,
                position=item.position,
                week_index=item.week_index,
                status=item.status,
                score_breakdown=item.score_breakdown,
                explanation_metadata=item.explanation_metadata,
            )
        )
    session.flush()
    return path


def persist_adaptation_event(
    session: Session,
    *,
    user_id: uuid.UUID,
    from_path_id: uuid.UUID,
    to_path_id: uuid.UUID,
    diff: PathDiff,
    trigger_type: str,
    summary: str,
    details: dict,
) -> AdaptationEvent:
    event = AdaptationEvent(
        id=uuid.uuid4(),
        user_id=user_id,
        from_path_id=from_path_id,
        to_path_id=to_path_id,
        event_type="PATH_ADAPTED",
        summary=summary,
        details=details,
        trigger_type=trigger_type,
        changed_skills=list(diff.changed_skills),
        changes=diff.as_dict(),
    )
    session.add(event)
    session.flush()
    return event
