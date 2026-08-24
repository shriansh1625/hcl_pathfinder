"""Progress feedback: outcome → evidence → fusion → adaptation → Path V2.

Mirrors the assessment runtime contract in one transaction. Any failure rolls
everything back: no orphan evidence, no half-written path.

This module never writes proficiency directly. A learner-reported level is
stored as PROGRESS evidence (reliability from reliability.yaml, currently
0.60), weighted below scored assessments. Skipping a step records no evidence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import EvidenceSource, PathItemStatus, PathStatus
from app.models import LearningPath, PathItem, Profile, Role, User
from app.ontology.load import OntologyBundle, load_ontology
from app.services.adaptation.diff import PathDiff
from app.services.adaptation.engine import AdaptationResult, adapt_path
from app.services.adaptation.repository import (
    persist_adaptation_event,
    persist_adapted_path,
)
from app.services.assessment.runtime import snapshot_of
from app.services.profiling import repository as profiling
from app.services.recommendation.models import LearnerPreferences

TRIGGER_PROGRESS_FEEDBACK = "PROGRESS_FEEDBACK"


class ProgressOutcome(StrEnum):
    COMPLETED = "COMPLETED"
    STRUGGLED = "STRUGGLED"
    SKIPPED = "SKIPPED"


_ITEM_STATUS: dict[str, str] = {
    ProgressOutcome.COMPLETED.value: PathItemStatus.COMPLETED.value,
    ProgressOutcome.STRUGGLED.value: PathItemStatus.IN_PROGRESS.value,
    ProgressOutcome.SKIPPED.value: PathItemStatus.SKIPPED.value,
}


@dataclass(frozen=True)
class FeedbackOutcome:
    position: int
    outcome: str
    item_status: str
    target_skill: str
    evidence_recorded: bool
    observed_level: float | None
    adaptation: str
    path_id: uuid.UUID | None
    diff: PathDiff | None
    summary: str


def _role_slug(session: Session, path: LearningPath) -> str | None:
    role = session.get(Role, path.role_id)
    return role.slug if role else None


def _prefs(session: Session, user_id: uuid.UUID) -> LearnerPreferences:
    profile = session.scalar(select(Profile).where(Profile.user_id == user_id))
    return LearnerPreferences(
        weekly_hours=profile.weekly_hours if profile else 10,
        learning_style=(profile.learning_style if profile else None) or "MIXED",
    )


def _validate_item_context(
  meta: dict,
  *,
  bundle: OntologyBundle,
  self_reported_level: float | None,
  outcome: ProgressOutcome,
) -> str:
    """Ensure path-item metadata anchors feedback to catalog entities."""
    target_skill = str(meta.get("target_skill") or "").strip()
    resource_slug = str(meta.get("resource_slug") or "").strip()

    if not target_skill and not resource_slug:
        raise ValueError("Path item has no provenance-bearing skill or resource context")

    if resource_slug and resource_slug not in {row.slug for row in bundle.resources}:
        raise ValueError(f"Unknown resource slug: {resource_slug}")

    skill_slugs = {row.slug for row in bundle.skills}
    wants_evidence = (
        outcome is not ProgressOutcome.SKIPPED and self_reported_level is not None
    )
    if wants_evidence:
        if not target_skill:
            raise ValueError("self_reported_level requires a canonical target_skill on the path item")
        if target_skill not in skill_slugs:
            raise ValueError(f"Unknown skill slug: {target_skill}")

    if target_skill and target_skill not in skill_slugs:
        raise ValueError(f"Unknown skill slug: {target_skill}")

    return target_skill


def record_feedback(
    session: Session,
    *,
    user_id: uuid.UUID,
    path_id: uuid.UUID,
    position: int,
    outcome: str,
    self_reported_level: float | None = None,
) -> FeedbackOutcome:
    """Apply an outcome to one path item and re-plan from new evidence when needed."""
    if session.get(User, user_id) is None:
        raise KeyError("Learner not found")
    try:
        resolved = ProgressOutcome(outcome)
    except ValueError as exc:
        raise ValueError(f"Unknown outcome: {outcome}") from exc

    path = session.get(LearningPath, path_id)
    if path is None or path.user_id != user_id:
        raise KeyError("Path not found")
    if path.status != PathStatus.ACTIVE.value:
        raise ValueError("Feedback applies to the active path only")

    item = session.scalar(
        select(PathItem).where(
            PathItem.learning_path_id == path.id,
            PathItem.position == position,
        )
    )
    if item is None:
        raise KeyError("Path item not found")

    meta = dict(item.explanation_metadata or {})
    bundle = load_ontology()
    target_skill = _validate_item_context(
        meta,
        bundle=bundle,
        self_reported_level=self_reported_level,
        outcome=resolved,
    )
    role_slug = _role_slug(session, path)

    record_evidence = (
        resolved is not ProgressOutcome.SKIPPED
        and self_reported_level is not None
        and bool(target_skill)
    )

    try:
        previous_profile = (
            profiling.compute_gap_profile(session, user_id=user_id, role_slug=role_slug)
            if role_slug
            else None
        )

        if record_evidence:
            profiling.append_evidence(
                session,
                user_id=user_id,
                skill_slug=target_skill,
                source=EvidenceSource.PROGRESS.value,
                observed_level=float(self_reported_level),
                confidence=0.55,
                payload={
                    "skill_slug": target_skill,
                    "path_id": str(path.id),
                    "position": position,
                    "outcome": resolved.value,
                    "resource": meta.get("resource_slug") or None,
                },
                commit=False,
            )

        item.status = _ITEM_STATUS[resolved.value]
        session.flush()

        adaptation = "NO_ACTIVE_PATH"
        new_path_id: uuid.UUID | None = None
        diff: PathDiff | None = None

        if previous_profile is not None and role_slug:
            new_profile = profiling.compute_gap_profile(
                session, user_id=user_id, role_slug=role_slug
            )
            rows = session.scalars(
                select(PathItem)
                .where(PathItem.learning_path_id == path.id)
                .order_by(PathItem.position.asc())
            ).all()
            result: AdaptationResult = adapt_path(
                previous_items=[snapshot_of(row) for row in rows],
                previous_profile=previous_profile,
                new_profile=new_profile,
                catalog=[r for r in bundle.resources if r.is_active],
                edges=profiling.load_skill_edges(session),
                prefs=_prefs(session, user_id),
            )
            diff = result.diff
            if result.no_adaptation:
                adaptation = "NO_ADAPTATION_REQUIRED"
            else:
                prefs = _prefs(session, user_id)
                new_path = persist_adapted_path(
                    session,
                    user_id=user_id,
                    previous=path,
                    items=result.items,
                    total_estimated_hours=result.total_estimated_hours,
                    weekly_hours=prefs.weekly_hours,
                    learning_style=prefs.learning_style or "MIXED",
                    role_slug=role_slug,
                    quality=result.quality,
                )
                new_path_id = new_path.id
                adaptation = "CREATED"
                persist_adaptation_event(
                    session,
                    user_id=user_id,
                    from_path_id=path.id,
                    to_path_id=new_path.id,
                    diff=diff,
                    trigger_type=TRIGGER_PROGRESS_FEEDBACK,
                    summary=(
                        f"Learner reported {resolved.value} on step {position + 1}"
                        f"{f' ({target_skill})' if target_skill else ''}: "
                        f"{len(diff.added)} added, {len(diff.removed)} removed, "
                        f"{len(diff.moved)} moved."
                    ),
                    details={
                        "position": position,
                        "outcome": resolved.value,
                        "target_skill": target_skill,
                        "observed_level": self_reported_level,
                        "resource": meta.get("resource_slug") or None,
                    },
                )
        session.commit()
    except Exception:
        session.rollback()
        raise

    return FeedbackOutcome(
        position=position,
        outcome=resolved.value,
        item_status=_ITEM_STATUS[resolved.value],
        target_skill=target_skill,
        evidence_recorded=record_evidence,
        observed_level=self_reported_level if record_evidence else None,
        adaptation=adaptation,
        path_id=new_path_id,
        diff=diff,
        summary=_summary(resolved, adaptation, diff),
    )


_STILL_REQUIRED = (
    "The gap that justified this step is still open, so it was re-planned back "
    "onto your path — declining work does not remove the requirement."
)


def _summary(outcome: ProgressOutcome, adaptation: str, diff: PathDiff | None) -> str:
    if adaptation == "NO_ACTIVE_PATH":
        return "Recorded. No active path to re-plan."
    if adaptation == "NO_ADAPTATION_REQUIRED":
        if outcome is ProgressOutcome.SKIPPED:
            return f"Recorded. {_STILL_REQUIRED}"
        return "Recorded. Your diagnosis did not change enough to alter the path."

    added = len(diff.added) if diff else 0
    removed = len(diff.removed) if diff else 0
    moved = len(diff.moved) if diff else 0
    if not (added or removed or moved):
        if outcome is ProgressOutcome.SKIPPED:
            return f"Your remaining work is unchanged. {_STILL_REQUIRED}"
        return (
            "Your remaining work is unchanged — this step is still the right "
            "next move, so it stays where it is."
        )
    return (
        f"Path re-planned: {added} step(s) added, {removed} removed, {moved} moved."
    )
