"""Assemble AIContext from verified learner intelligence. No LLM. No DB dumps."""

from __future__ import annotations

import hashlib
import json
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import PathStatus
from app.models import AdaptationEvent, LearningPath, Profile, Role, User
from app.ontology.load import load_ontology
from app.services.explanation.schema import AIContext, Fact, Intent
from app.services.profiling import repository as profiling

_SKILL_IN_QUERY = re.compile(r"\b([a-z][a-z0-9]+(?:_[a-z0-9]+)+)\b", re.I)


def classify_query(query: str) -> Intent:
    text = query.lower()
    if any(token in text for token in ("can't start", "cannot start", "blocked", "why this resource", "why this course")):
        return "WHY_RESOURCE"
    if any(token in text for token in ("what changed", "after my assessment", "path change")):
        return "WHAT_CHANGED"
    if any(token in text for token in ("this week", "do next", "next best", "should i do")):
        return "NEXT_ACTION"
    if "coach" in text:
        return "COACH"
    if any(token in text for token in ("why am i learning", "why is", "important", "gap")):
        return "WHY_GAP"
    return "QUERY"


def build_context(
    session: Session,
    *,
    user_id: UUID,
    intent: Intent,
    skill_slug: str | None = None,
    resource_slug: str | None = None,
    query: str | None = None,
) -> AIContext:
    user = session.get(User, user_id)
    if user is None:
        raise KeyError("Learner not found")
    profile = session.scalar(select(Profile).where(Profile.user_id == user_id))
    path = session.scalars(
        select(LearningPath)
        .where(LearningPath.user_id == user_id, LearningPath.status == PathStatus.ACTIVE.value)
        .order_by(LearningPath.version.desc())
    ).first()
    role_slug = "ai-ml-engineer"
    role_name = "AI/ML Engineer"
    if path is not None:
        role = session.get(Role, path.role_id)
        if role is not None:
            role_slug = role.slug
            role_name = role.name
    elif profile is not None and profile.target_role_id is not None:
        role = session.get(Role, profile.target_role_id)
        if role is not None:
            role_slug = role.slug
            role_name = role.name

    gap_profile = profiling.compute_gap_profile(session, user_id=user_id, role_slug=role_slug)
    bundle = load_ontology()
    ontology_skills = {item.slug for item in bundle.skills}
    ontology_resources = {item.slug for item in bundle.resources}

    resolved_intent = intent
    if intent == "QUERY" and query:
        resolved_intent = classify_query(query)

    skill_slug = skill_slug or _skill_from_query(query, ontology_skills, gap_profile)
    resource_slug = resource_slug or _resource_from_query(query, bundle.resources)

    facts: list[Fact] = []
    allowed_skills: set[str] = set()
    allowed_resources: set[str] = set()
    allowed_titles: set[str] = {role_name}
    allowed_numbers: set[float] = set()

    weekly = float(profile.weekly_hours) if profile and profile.weekly_hours else 8.0
    style = (profile.learning_style if profile and profile.learning_style else "MIXED")
    _add(facts, "learner.weekly_hours", "Weekly hours", f"{weekly:g}", allowed_numbers, weekly)
    _add(facts, "learner.learning_style", "Learning style", style)
    _add(facts, "role.slug", "Role slug", role_slug)
    _add(facts, "role.name", "Target role", role_name)
    allowed_skills.update(item.ranked.gap.skill_slug for item in gap_profile.items)
    allowed_titles.update(item.ranked.gap.skill_name for item in gap_profile.items)

    gap_item = next((item for item in gap_profile.items if item.ranked.gap.skill_slug == skill_slug), None)
    skill_payload = None
    dependencies: list[dict] = []
    if skill_slug and gap_item is None:
        if skill_slug not in ontology_skills:
            raise KeyError(f"Unknown skill: {skill_slug}")
        spec = next(item for item in bundle.skills if item.slug == skill_slug)
        allowed_skills.add(skill_slug)
        allowed_titles.add(spec.canonical_name)
        skill_payload = {
            "slug": spec.slug,
            "name": spec.canonical_name,
            "proficiency": None,
            "confidence": None,
            "evidence_state": "UNKNOWN",
            "attainment": "UNKNOWN",
            "target": None,
            "action": "VERIFY",
            "gap_priority": 0.0,
            "action_priority": 0.0,
        }
        _add(facts, "skill.slug", "Skill", spec.slug)
        _add(facts, "skill.name", "Skill name", spec.canonical_name)
        _add(facts, "skill.proficiency", f"{spec.canonical_name} proficiency", "—")
        _add(facts, "skill.evidence_state", "Evidence state", "UNKNOWN")
        _add(facts, "skill.attainment", "Attainment", "UNKNOWN")
        _add(facts, "skill.action", "Action", "VERIFY")
    if gap_item is not None:
        gap = gap_item.ranked.gap
        allowed_skills.add(gap.skill_slug)
        allowed_titles.add(gap.skill_name)
        proficiency = gap.proficiency
        skill_payload = {
            "slug": gap.skill_slug,
            "name": gap.skill_name,
            "proficiency": proficiency,
            "confidence": gap.confidence,
            "evidence_state": gap.evidence_state.value,
            "attainment": gap.attainment.value,
            "target": gap.target_level,
            "action": gap_item.action.value,
            "gap_priority": gap_item.ranked.gap_priority,
            "action_priority": gap_item.action_priority,
        }
        _add(facts, "skill.slug", "Skill", gap.skill_slug)
        _add(facts, "skill.name", "Skill name", gap.skill_name)
        _add(
            facts,
            "skill.proficiency",
            f"{gap.skill_name} proficiency",
            "—" if proficiency is None else f"{proficiency:.2f}",
            allowed_numbers,
            proficiency,
        )
        _add(facts, "skill.target", f"{gap.skill_name} target", f"{gap.target_level:.2f}", allowed_numbers, gap.target_level)
        _add(facts, "skill.evidence_state", "Evidence state", gap.evidence_state.value)
        _add(facts, "skill.attainment", "Attainment", gap.attainment.value)
        _add(facts, "skill.action", "Action", gap_item.action.value)
        downstream = ", ".join(gap_item.ranked.impact.hard_role_descendants[:4]) or "—"
        _add(facts, "skill.downstream", "Downstream HARD dependencies", downstream)
        for slug in gap_item.ranked.impact.hard_role_descendants[:4]:
            allowed_skills.add(slug)
        for blocker in gap_item.gate.blockers:
            allowed_skills.add(blocker)
            dependencies.append({"skill": blocker, "relationship": "HARD_PREREQUISITE", "state": "BLOCKING"})
            _add(facts, f"dep.{blocker}", "Blocking prerequisite", blocker)

    path_meta = (path.extra_metadata or {}) if path else {}
    items = []
    if path is not None:
        from app.models import PathItem

        items = list(
            session.scalars(
                select(PathItem).where(PathItem.learning_path_id == path.id).order_by(PathItem.position)
            ).all()
        )
        _add(facts, "path.version", "Active path version", str(path.version), allowed_numbers, float(path.version))
        _add(facts, "path.status", "Active path status", path.status)

    resource_payload = None
    path_item_payload = None
    waiting_titles: list[str] = []
    matched_item = None
    for row in items:
        meta = row.explanation_metadata or {}
        slug = meta.get("resource_slug") or ""
        title = meta.get("title") or ""
        if slug:
            allowed_resources.add(slug)
        if title:
            allowed_titles.add(title)
        kind = str(meta.get("kind") or "")
        if kind.startswith("WAITING"):
            waiting_titles.append(title or slug)
        if resource_slug and slug == resource_slug:
            matched_item = row
        elif not resource_slug and skill_slug and meta.get("target_skill") == skill_slug and matched_item is None:
            matched_item = row

    if resource_slug and matched_item is None:
        catalog = next((item for item in bundle.resources if item.slug == resource_slug), None)
        if catalog is None:
            raise KeyError(f"Unknown resource: {resource_slug}")
        raise KeyError(f"Resource not on the active path: {resource_slug}")

    if matched_item is not None:
        meta = matched_item.explanation_metadata or {}
        causality = dict(meta.get("causality") or {})
        prereqs = list(meta.get("prerequisites") or [])
        resource_payload = {
            "slug": meta.get("resource_slug") or "",
            "title": meta.get("title") or "",
            "type": meta.get("type") or matched_item.item_type,
            "duration": meta.get("duration_hours"),
            "eligibility": meta.get("eligibility"),
            "intervention": meta.get("intervention"),
            "prerequisites": prereqs,
        }
        path_item_payload = {
            "week": matched_item.week_index,
            "position": matched_item.position,
            "status": matched_item.status,
            "executable": bool(meta.get("executable")),
            "eligibility": meta.get("eligibility"),
            "intervention": meta.get("intervention"),
            "causality": causality,
        }
        if resource_payload["slug"]:
            allowed_resources.add(resource_payload["slug"])
        if resource_payload["title"]:
            allowed_titles.add(resource_payload["title"])
        _add(facts, "resource.slug", "Resource", resource_payload["slug"] or "—")
        _add(facts, "resource.title", "Resource title", resource_payload["title"] or "—")
        _add(facts, "path_item.week", "Week", str(matched_item.week_index) if matched_item.week_index is not None else "—")
        if matched_item.week_index is not None:
            allowed_numbers.add(float(matched_item.week_index))
        _add(facts, "path_item.position", "Position", str(matched_item.position), allowed_numbers, float(matched_item.position))
        _add(facts, "path_item.status", "Item status", matched_item.status)
        _add(facts, "path_item.eligibility", "Eligibility", str(meta.get("eligibility") or "—"))
        _add(facts, "path_item.intervention", "Intervention", str(meta.get("intervention") or "—"))
        for key in (
            "why_this_skill",
            "why_this_resource",
            "why_this_intervention",
            "why_this_position",
            "why_not_earlier",
            "why_selected",
        ):
            if causality.get(key):
                _add(facts, f"causality.{key}", key.replace("_", " "), str(causality[key]))
        for prereq in prereqs[:4]:
            skill = str(prereq.get("skill") or "")
            if skill:
                allowed_skills.add(skill)
                _add(
                    facts,
                    f"prereq.{skill}",
                    "Prerequisite",
                    f"{skill} {prereq.get('state') or ''} {prereq.get('observed') if prereq.get('observed') is not None else 'UNKNOWN'}".strip(),
                )

    if waiting_titles:
        _add(facts, "waiting.resources", "Waiting resources", ", ".join(waiting_titles[:4]))

    next_payload = None
    next_row = next(
        (
            row
            for row in items
            if bool((row.explanation_metadata or {}).get("executable")) and row.status != "COMPLETED"
        ),
        None,
    )
    if next_row is not None:
        meta = next_row.explanation_metadata or {}
        next_payload = {
            "title": meta.get("title") or meta.get("resource_slug") or "",
            "skill": meta.get("target_skill") or "",
            "week": next_row.week_index,
            "action": meta.get("intervention") or "START",
            "resource": meta.get("resource_slug") or "",
        }
        if next_payload["resource"]:
            allowed_resources.add(next_payload["resource"])
        if next_payload["title"]:
            allowed_titles.add(next_payload["title"])
        if next_payload["skill"]:
            allowed_skills.add(next_payload["skill"])
        _add(facts, "next_action.title", "Next item", next_payload["title"] or "—")
        _add(facts, "next_action.skill", "Next skill", next_payload["skill"] or "—")
        _add(facts, "next_action.week", "Next week", str(next_payload["week"] if next_payload["week"] is not None else "—"))
        if next_payload["week"] is not None:
            allowed_numbers.add(float(next_payload["week"]))
        _add(facts, "next_action.action", "Next action", next_payload["action"])

    adaptation_payload = None
    if path is not None:
        event = session.scalars(
            select(AdaptationEvent)
            .where(AdaptationEvent.to_path_id == path.id)
            .order_by(AdaptationEvent.created_at.desc())
        ).first()
        if event is not None:
            changes = event.changes or {}
            added = ", ".join(item.get("title") or item.get("key") or "" for item in (changes.get("added") or [])[:3]) or "—"
            moved = ", ".join(item.get("title") or item.get("key") or "" for item in (changes.get("moved") or [])[:3]) or "—"
            details = event.details or {}
            observed = details.get("overall_score")
            before_state = "UNKNOWN"
            after_state = skill_payload["attainment"] if skill_payload else "—"
            if skill_payload and skill_payload.get("evidence_state") == "UNKNOWN":
                before_state = "UNKNOWN"
            elif skill_payload:
                before_state = "UNKNOWN" if skill_payload.get("evidence_state") == "KNOWN" and after_state != "UNKNOWN" else before_state
            # Prefer explicit before from gap if we only know current after.
            adaptation_payload = {
                "trigger": event.trigger_type,
                "changed_skills": list(event.changed_skills or []),
                "added": added,
                "moved": moved,
                "observed": observed,
            }
            _add(facts, "adaptation.trigger", "Adaptation trigger", event.trigger_type)
            _add(facts, "adaptation.added", "Added items", added)
            _add(facts, "adaptation.moved", "Moved items", moved)
            if observed is not None:
                _add(facts, "adaptation.observed", "Assessment observed", f"{float(observed):.2f}", allowed_numbers, float(observed))
            _add(facts, "adaptation.before_state", "Before", before_state)
            _add(facts, "adaptation.after_state", "After", after_state)
            for slug in event.changed_skills or []:
                allowed_skills.add(slug)

    fingerprint = _fingerprint(
        {
            "intent": resolved_intent,
            "user": str(user_id),
            "role": role_slug,
            "path": str(path.id) if path else None,
            "version": path.version if path else 0,
            "skill": skill_slug,
            "resource": resource_slug,
            "query": (query or "").strip().lower()[:200],
            "facts": [(item.id, item.value) for item in facts],
        }
    )
    return AIContext(
        intent=resolved_intent,
        fingerprint=fingerprint,
        learner={"weekly_hours": weekly, "learning_style": style},
        target_role={"slug": role_slug, "name": role_name},
        skill=skill_payload,
        dependencies=dependencies,
        resource=resource_payload,
        path_item=path_item_payload,
        next_action=next_payload,
        adaptation=adaptation_payload,
        facts=facts,
        allowed_skills=sorted(allowed_skills),
        allowed_resources=sorted(allowed_resources),
        allowed_roles=[role_slug],
        allowed_titles=sorted(allowed_titles),
        allowed_numbers=sorted(allowed_numbers),
    )


def _add(
    facts: list[Fact],
    fact_id: str,
    label: str,
    value: str,
    numbers: set[float] | None = None,
    number: float | None = None,
) -> None:
    facts.append(Fact(id=fact_id, label=label, value=value))
    if numbers is not None and number is not None:
        numbers.add(round(float(number), 4))


def _skill_from_query(query: str | None, ontology_skills: set[str], gap_profile) -> str | None:
    if not query:
        return None
    text = query.lower().replace("-", "_")
    for slug in ontology_skills:
        pretty = slug.replace("_", " ")
        if slug in text or pretty in text:
            return slug
    for item in gap_profile.items:
        name = item.ranked.gap.skill_name.lower()
        if name and name in query.lower():
            return item.ranked.gap.skill_slug
    return None


def _resource_from_query(query: str | None, resources) -> str | None:
    if not query:
        return None
    lowered = query.lower()
    for item in resources:
        if item.slug.lower() in lowered or item.title.lower() in lowered:
            return item.slug
    return None


def _fingerprint(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
