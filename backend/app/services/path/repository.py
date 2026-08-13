"""Persist generated paths. No scoring math."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import PathItemType, PathStatus, ResourceType
from app.core.ids import ontology_uuid
from app.models import LearningPath, PathItem, Profile, Role, User
from app.services.recommendation.models import LearnerPreferences, PlannedPath


def upsert_preferences(
    session: Session,
    user_id: uuid.UUID,
    prefs: LearnerPreferences,
    *,
    role_slug: str | None = None,
) -> Profile:
    profile = session.scalar(select(Profile).where(Profile.user_id == user_id))
    role_id = None
    if role_slug:
        role = session.scalar(select(Role).where(Role.slug == role_slug))
        if role is None:
            raise KeyError(f"Unknown role: {role_slug}")
        role_id = role.id
    if profile is None:
        profile = Profile(
            id=uuid.uuid4(),
            user_id=user_id,
            weekly_hours=int(prefs.weekly_hours),
            learning_style=prefs.learning_style,
            target_role_id=role_id,
        )
        session.add(profile)
    else:
        profile.weekly_hours = int(prefs.weekly_hours)
        profile.learning_style = prefs.learning_style
        if role_id is not None:
            profile.target_role_id = role_id
    session.commit()
    session.refresh(profile)
    return profile


def persist_path(
    session: Session,
    *,
    user_id: uuid.UUID,
    planned: PlannedPath,
) -> LearningPath:
    user = session.get(User, user_id)
    if user is None:
        raise KeyError("Learner not found")
    role = session.scalar(select(Role).where(Role.slug == planned.role_slug))
    if role is None:
        raise KeyError(f"Unknown role: {planned.role_slug}")

    existing = session.scalars(select(LearningPath).where(LearningPath.user_id == user_id)).all()
    version = max((row.version for row in existing), default=0) + 1
    parent_id = None
    for row in existing:
        if row.role_id == role.id and row.status == PathStatus.ACTIVE.value:
            row.status = PathStatus.SUPERSEDED.value
            parent_id = row.id

    path = LearningPath(
        id=uuid.uuid4(),
        user_id=user_id,
        role_id=role.id,
        version=version,
        status=PathStatus.ACTIVE.value,
        parent_path_id=parent_id,
        generated_at=datetime.now(timezone.utc),
        total_estimated_hours=planned.total_estimated_hours,
        extra_metadata={
            "weekly_hours": planned.weekly_hours,
            "learning_style": planned.learning_style,
            "role": planned.role_slug,
        },
    )
    session.add(path)
    session.flush()
    for item in planned.items:
        resource_type = item.candidate.resource.type
        session.add(
            PathItem(
                id=uuid.uuid4(),
                learning_path_id=path.id,
                resource_id=ontology_uuid("resource", item.candidate.resource.slug),
                assessment_id=None,
                item_type=(
                    PathItemType.ASSESSMENT.value
                    if resource_type == ResourceType.ASSESSMENT.value
                    else PathItemType.RESOURCE.value
                ),
                position=item.position,
                week_index=item.week_index,
                status="PENDING",
                score_breakdown=item.candidate.breakdown.as_dict(),
                explanation_metadata={
                    "resource_slug": item.candidate.resource.slug,
                    "title": item.candidate.resource.title,
                    "target_skill": item.candidate.primary_skill,
                    "intervention": item.candidate.intervention.value,
                    "eligibility": item.candidate.eligibility.status.value,
                    "prerequisites": [
                        {
                            "skill": check.skill_slug,
                            "min_level": check.min_level,
                            "state": check.state.value,
                            "observed": check.observed,
                        }
                        for check in item.candidate.eligibility.checks
                    ],
                    "explanation": item.candidate.explanation,
                    "url": item.candidate.resource.url,
                    "url_status": item.candidate.resource.url_status,
                    "duration_hours": item.candidate.resource.duration_hours,
                    "type": item.candidate.resource.type,
                },
            )
        )
    session.commit()
    session.refresh(path)
    return path
