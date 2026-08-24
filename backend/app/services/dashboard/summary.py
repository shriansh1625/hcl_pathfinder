"""Learner command-center aggregation. Read-only composition of existing intelligence."""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AdaptationEvent, LearningPath, PathItem, Profile, Role, Skill, SkillEvidence, User
from app.ontology.load import load_ontology
from app.schemas.intelligence import DashboardRead, GapItemRead, MilestoneRead, SuggestedAssessmentRead
from app.services.profiling import repository as profiling


def _gap_item_read(profile, item) -> GapItemRead:
    return GapItemRead(
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


def _skill_categories() -> dict[str, str]:
    return {item.slug: item.category for item in load_ontology().skills}


def _milestones_from_path(path: LearningPath | None, items: list[PathItem]) -> list[MilestoneRead]:
    if path is None or not items:
        return []
    categories = _skill_categories()
    buckets: dict[str, dict] = defaultdict(lambda: {"items": [], "skills": set()})
    for row in items:
        meta = row.explanation_metadata or {}
        skill = meta.get("target_skill") or ""
        category = categories.get(skill, "General")
        buckets[category]["items"].append(row)
        if skill:
            buckets[category]["skills"].add(skill)

    milestones: list[MilestoneRead] = []
    for category, payload in sorted(buckets.items(), key=lambda pair: pair[0]):
        rows = payload["items"]
        completed = sum(1 for row in rows if row.status == "COMPLETED")
        total = len(rows)
        if completed == total and total > 0:
            status = "COMPLETED"
        elif completed > 0:
            status = "IN_PROGRESS"
        else:
            status = "PENDING"
        milestones.append(
            MilestoneRead(
                id=category.lower().replace(" ", "-"),
                label=category,
                category=category,
                status=status,
                completed_items=completed,
                total_items=total,
                skills=sorted(payload["skills"]),
            )
        )
    return milestones


def build_dashboard(session: Session, *, user_id: uuid.UUID, role_slug: str) -> DashboardRead:
    profile = profiling.compute_gap_profile(session, user_id=user_id, role_slug=role_slug)
    gap_items = [_gap_item_read(profile, item) for item in profile.items]
    top_gaps = sorted(
        [item for item in gap_items if item.attainment in {"GAP", "UNKNOWN", "NEAR_TARGET"}],
        key=lambda row: row.action_priority,
        reverse=True,
    )[:5]
    blockers = [item for item in gap_items if item.blocked]

    role = session.scalar(select(Role).where(Role.slug == role_slug))
    learner_profile = session.scalar(select(Profile).where(Profile.user_id == user_id))
    active_path = session.scalar(
        select(LearningPath)
        .where(LearningPath.user_id == user_id, LearningPath.status == "ACTIVE")
        .order_by(LearningPath.version.desc())
    )
    path_items: list[PathItem] = []
    if active_path:
        path_items = list(
            session.scalars(
                select(PathItem)
                .where(PathItem.learning_path_id == active_path.id)
                .order_by(PathItem.position)
            ).all()
        )

    milestones = _milestones_from_path(active_path, path_items)
    current_milestone = next((item for item in milestones if item.status == "IN_PROGRESS"), None)
    if current_milestone is None:
        current_milestone = next((item for item in milestones if item.status == "PENDING"), None)

    completed = sum(1 for row in path_items if row.status == "COMPLETED")
    total = len(path_items)
    planned_hours = sum(float((row.explanation_metadata or {}).get("duration_hours") or 0) for row in path_items)
    completed_hours = sum(
        float((row.explanation_metadata or {}).get("duration_hours") or 0)
        for row in path_items
        if row.status == "COMPLETED"
    )

    current_week = None
    for row in path_items:
        meta = row.explanation_metadata or {}
        executable = bool(meta.get("executable", row.status == "PENDING"))
        if row.status != "COMPLETED" and executable:
            current_week = row.week_index
            break
    this_week = []
    if current_week is not None:
        for row in path_items:
            if row.week_index == current_week:
                meta = row.explanation_metadata or {}
                this_week.append(
                    {
                        "position": row.position,
                        "title": meta.get("title") or "",
                        "status": row.status,
                        "target_skill": meta.get("target_skill") or "",
                        "duration_hours": float(meta.get("duration_hours") or 0),
                    }
                )

    next_action = None
    for row in path_items:
        meta = row.explanation_metadata or {}
        executable = bool(meta.get("executable", row.status == "PENDING"))
        if executable and row.status not in {"COMPLETED", "BLOCKED"}:
            next_action = {
                "position": row.position,
                "title": meta.get("title") or "",
                "target_skill": meta.get("target_skill") or "",
                "intervention": meta.get("intervention") or "",
                "status": row.status,
            }
            break

    evidence_rows = list(
        session.scalars(
            select(SkillEvidence)
            .where(SkillEvidence.user_id == user_id)
            .order_by(SkillEvidence.created_at.desc())
            .limit(5)
        ).all()
    )
    skill_ids = {row.skill_id for row in evidence_rows}
    slugs = {
        item.id: item.slug
        for item in session.scalars(select(Skill).where(Skill.id.in_(skill_ids))).all()
    } if skill_ids else {}
    recent_evidence = [
        {
            "skill": slugs.get(row.skill_id, ""),
            "source": row.source_type,
            "observed_level": row.observed_level,
            "created_at": row.created_at.isoformat(),
        }
        for row in evidence_rows
    ]

    recent_adaptation = None
    if active_path:
        event = session.scalar(
            select(AdaptationEvent)
            .where(AdaptationEvent.to_path_id == active_path.id)
            .order_by(AdaptationEvent.created_at.desc())
        )
        if event:
            recent_adaptation = {
                "event_type": event.event_type,
                "summary": event.summary,
                "from_path_id": str(event.from_path_id),
                "to_path_id": str(event.to_path_id),
                "created_at": event.created_at.isoformat(),
            }

    competency_snapshot = sorted(
        [
            {
                "skill": item.skill,
                "name": item.name,
                "proficiency": item.proficiency,
                "target_level": item.target_level,
                "evidence_state": item.evidence_state,
                "attainment": item.attainment,
            }
            for item in gap_items
            if item.required_status == "CORE"
        ],
        key=lambda row: row["target_level"],
        reverse=True,
    )[:6]

    why = None
    if top_gaps:
        why = top_gaps[0].explanation

    upcoming = None
    try:
        from app.ontology.load import load_ontology
        from app.services.assessment.selection import select_assessment

        bundle = load_ontology()
        spec = select_assessment(profile, bundle.assessments)
        if spec is None:
            upcoming = SuggestedAssessmentRead(
                assessment=None,
                title=None,
                question_count=None,
                covers=[],
                reason="No UNKNOWN role-relevant skills require verification.",
            )
        else:
            covers = [
                skill
                for skill in spec.target_skills
                if any(
                    item.ranked.gap.skill_slug == skill
                    and item.ranked.gap.evidence_state.value == "UNKNOWN"
                    for item in profile.items
                )
            ]
            upcoming = SuggestedAssessmentRead(
                assessment=spec.slug,
                title=spec.title,
                question_count=len(spec.questions),
                covers=covers,
                reason=(
                    f"Smallest assessment covering the highest-priority UNKNOWN skills "
                    f"for {profile.role_name}."
                ),
            )
    except Exception:
        upcoming = SuggestedAssessmentRead(
            assessment=None,
            title=None,
            question_count=None,
            covers=[],
            reason="No assessment suggested yet",
        )

    return DashboardRead(
        role=role_slug,
        role_name=profile.role_name,
        goal_text=learner_profile.goal_text if learner_profile else None,
        experience_level=learner_profile.experience_level if learner_profile else None,
        weekly_hours=float(learner_profile.weekly_hours) if learner_profile and learner_profile.weekly_hours else None,
        learning_style=learner_profile.learning_style if learner_profile else None,
        interests=list(learner_profile.interests or []) if learner_profile and learner_profile.interests else None,
        path_version=active_path.version if active_path else None,
        path_status=active_path.status if active_path else None,
        overall_progress={
            "completed_items": completed,
            "total_items": total,
            "completed_hours": completed_hours,
            "planned_hours": planned_hours,
            "evidence_coverage": sum(1 for item in gap_items if item.evidence_state != "UNKNOWN"),
            "competency_total": len(gap_items),
        },
        competency_snapshot=competency_snapshot,
        top_gaps=top_gaps,
        blockers=blockers,
        current_milestone=current_milestone,
        this_week=this_week,
        next_action=next_action,
        recent_evidence=recent_evidence,
        recent_adaptation=recent_adaptation,
        upcoming_assessment=upcoming,
        milestones=milestones,
        why_this_matters=why,
    )
