"""Assessment runtime: submit → score → evidence → fusion → adapt → V2.

One DB transaction. Any failure rolls back everything: no partial evidence,
no half-written Path V2, no orphan adaptation event. The assessment engine
never writes user_skills directly — it appends evidence and fusion decides.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import PathItemType, PathStatus
from app.core.ids import ontology_uuid
from app.models import Assessment, AssessmentAttempt, LearningPath, PathItem, Profile, Role, User
from app.ontology.load import load_ontology
from app.services.adaptation.diff import PathDiff
from app.services.adaptation.engine import (
    AdaptationResult,
    PathItemSnapshot,
    adapt_path,
)
from app.services.adaptation.repository import (
    persist_adaptation_event,
    persist_adapted_path,
)
from app.services.assessment.normalizer import evidence_rows_from_score
from app.services.assessment.scoring import AssessmentScore, score_attempt
from app.services.profiling import repository as profiling
from app.services.recommendation.models import LearnerPreferences

TRIGGER_ASSESSMENT_RESULT = "ASSESSMENT_RESULT"


@dataclass(frozen=True)
class AttemptOutcome:
    attempt_id: uuid.UUID
    attempt_number: int
    score: AssessmentScore
    adaptation: str  # CREATED | NO_ADAPTATION_REQUIRED | NO_ACTIVE_PATH | REPLAYED
    path_id: uuid.UUID | None
    diff: PathDiff | None


def snapshot_of(row: PathItem) -> PathItemSnapshot:
    meta = dict(row.explanation_metadata or {})
    gate = meta.get("gate") or None
    is_gate = row.item_type == PathItemType.VERIFICATION_GATE.value
    return PathItemSnapshot(
        position=row.position,
        week_index=row.week_index,
        status=row.status,
        kind=meta.get("kind")
        or (PathItemType.VERIFICATION_GATE.value if is_gate else "EXECUTABLE"),
        resource_slug=(meta.get("resource_slug") or None) if not is_gate else None,
        gate_skill=(gate or {}).get("skill") if gate else (meta.get("target_skill") if is_gate else None),
        item_type=row.item_type,
        score_breakdown=dict(row.score_breakdown or {}),
        explanation_metadata=meta,
    )


def _active_path(session: Session, user_id: uuid.UUID) -> LearningPath | None:
    return session.scalars(
        select(LearningPath)
        .where(
            LearningPath.user_id == user_id,
            LearningPath.status == PathStatus.ACTIVE.value,
        )
        .order_by(LearningPath.version.desc())
    ).first()


def _replay(attempt: AssessmentAttempt) -> AttemptOutcome:
    result = attempt.result or {}
    score = AssessmentScore(
        assessment_slug=result.get("assessment", ""),
        overall_score=result.get("overall_score", 0.0),
        passed=result.get("passed", False),
        skill_results=(),
    )
    return AttemptOutcome(
        attempt_id=attempt.id,
        attempt_number=attempt.attempt_number,
        score=score,
        adaptation="REPLAYED",
        path_id=uuid.UUID(result["path_id"]) if result.get("path_id") else None,
        diff=None,
    )


def submit_attempt(
    session: Session,
    *,
    user_id: uuid.UUID,
    assessment_slug: str,
    answers: list[int],
    attempt_id: uuid.UUID | None = None,
) -> AttemptOutcome:
    user = session.get(User, user_id)
    if user is None:
        raise KeyError("Learner not found")
    bundle = load_ontology()
    spec = next((a for a in bundle.assessments if a.slug == assessment_slug), None)
    if spec is None:
        raise KeyError(f"Unknown assessment: {assessment_slug}")
    assessment_uuid = ontology_uuid("assessment", assessment_slug)
    if session.get(Assessment, assessment_uuid) is None:
        raise KeyError(f"Assessment not seeded: {assessment_slug}")

    if attempt_id is not None:
        existing = session.get(AssessmentAttempt, attempt_id)
        if existing is not None:
            if existing.user_id != user_id or existing.assessment_id != assessment_uuid:
                raise ValueError("attempt_id already used for a different attempt")
            return _replay(existing)
    attempt_id = attempt_id or uuid.uuid4()

    score = score_attempt(spec, answers)

    previous_path = _active_path(session, user_id)
    role_slug: str | None = None
    if previous_path is not None:
        role = session.get(Role, previous_path.role_id)
        role_slug = role.slug if role else None
    if role_slug is None:
        profile = session.scalar(select(Profile).where(Profile.user_id == user_id))
        if profile is not None and profile.target_role_id is not None:
            role = session.get(Role, profile.target_role_id)
            role_slug = role.slug if role else None
    if role_slug is None and spec.target_role:
        role_slug = spec.target_role

    attempt_number = (
        session.scalar(
            select(func.max(AssessmentAttempt.attempt_number)).where(
                AssessmentAttempt.assessment_id == assessment_uuid,
                AssessmentAttempt.user_id == user_id,
            )
        )
        or 0
    ) + 1

    try:
        attempt = AssessmentAttempt(
            id=attempt_id,
            assessment_id=assessment_uuid,
            user_id=user_id,
            attempt_number=attempt_number,
            answers=list(answers),
        )
        session.add(attempt)
        session.flush()

        previous_profile = (
            profiling.compute_gap_profile(session, user_id=user_id, role_slug=role_slug)
            if role_slug
            else None
        )

        for row in evidence_rows_from_score(score, attempt_id=attempt_id):
            profiling.append_evidence(
                session,
                user_id=user_id,
                skill_slug=row["skill"],
                source=row["source"],
                observed_level=row["observed_level"],
                confidence=row["confidence"],
                payload=row["evidence_payload"],
                commit=False,
            )

        adaptation = "NO_ACTIVE_PATH"
        new_path_id: uuid.UUID | None = None
        diff: PathDiff | None = None

        if previous_path is not None and previous_profile is not None and role_slug:
            new_profile = profiling.compute_gap_profile(
                session, user_id=user_id, role_slug=role_slug
            )
            rows = session.scalars(
                select(PathItem)
                .where(PathItem.learning_path_id == previous_path.id)
                .order_by(PathItem.position.asc())
            ).all()
            snapshots = [snapshot_of(row) for row in rows]
            profile_row = session.scalar(select(Profile).where(Profile.user_id == user_id))
            prefs = LearnerPreferences(
                weekly_hours=profile_row.weekly_hours if profile_row else 10,
                learning_style=(profile_row.learning_style if profile_row else None) or "MIXED",
            )
            catalog = [r for r in bundle.resources if r.is_active]
            edges = profiling.load_skill_edges(session)
            result: AdaptationResult = adapt_path(
                previous_items=snapshots,
                previous_profile=previous_profile,
                new_profile=new_profile,
                catalog=catalog,
                edges=edges,
                prefs=prefs,
            )
            diff = result.diff
            if result.no_adaptation:
                adaptation = "NO_ADAPTATION_REQUIRED"
            else:
                new_path = persist_adapted_path(
                    session,
                    user_id=user_id,
                    previous=previous_path,
                    items=result.items,
                    total_estimated_hours=result.total_estimated_hours,
                    weekly_hours=prefs.weekly_hours,
                    learning_style=prefs.learning_style or "mixed",
                    role_slug=role_slug,
                    quality=result.quality,
                )
                new_path_id = new_path.id
                adaptation = "CREATED"
                persist_adaptation_event(
                    session,
                    user_id=user_id,
                    from_path_id=previous_path.id,
                    to_path_id=new_path.id,
                    diff=diff,
                    trigger_type=TRIGGER_ASSESSMENT_RESULT,
                    summary=(
                        f"Assessment {assessment_slug} (attempt {attempt_number}) changed "
                        f"{len(diff.changed_skills)} skill(s): "
                        f"{len(diff.added)} added, {len(diff.removed)} removed, "
                        f"{len(diff.moved)} moved."
                    ),
                    details={
                        "assessment": assessment_slug,
                        "attempt_id": str(attempt_id),
                        "overall_score": round(score.overall_score, 6),
                        "passed": score.passed,
                    },
                )

        attempt.result = {
            "assessment": assessment_slug,
            "overall_score": round(score.overall_score, 6),
            "passed": score.passed,
            "skill_results": [item.as_dict() for item in score.skill_results],
            "adaptation": adaptation,
            "path_id": str(new_path_id) if new_path_id else None,
            "diff": diff.as_dict() if diff else None,
        }
        session.flush()
        session.commit()
    except IntegrityError:
        session.rollback()
        replay = session.get(AssessmentAttempt, attempt_id)
        if replay is not None and replay.user_id == user_id:
            return _replay(replay)
        raise
    except Exception:
        session.rollback()
        raise

    return AttemptOutcome(
        attempt_id=attempt_id,
        attempt_number=attempt_number,
        score=score,
        adaptation=adaptation,
        path_id=new_path_id,
        diff=diff,
    )
