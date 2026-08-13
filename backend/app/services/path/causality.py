"""Deterministic path-item reasons. Not ranking copy. No LLM."""

from __future__ import annotations

from app.core.enums import EligibilityStatus, PathItemKind, RelationshipType
from app.services.gap_engine.profile import GapProfile
from app.services.recommendation.causality import is_known_focal, unblocks_focal
from app.services.recommendation.models import PathCause, PlannedItem, gap_index
from app.services.skill_graph.dependency import SkillEdge


def _coverage(item: PlannedItem, skill: str) -> float:
    if item.candidate is None:
        return 0.0
    for row in item.candidate.resource.skills:
        if row.slug == skill:
            return row.coverage_strength
    return 0.0


def _hard_predecessors(
    item: PlannedItem,
    packed: list[PlannedItem],
    edges: list[SkillEdge],
) -> list[PlannedItem]:
    if item.candidate is None:
        return []
    skill = item.candidate.primary_skill
    hard_sources = {
        edge.source
        for edge in edges
        if edge.target == skill and edge.relationship_type == RelationshipType.HARD_PREREQUISITE.value
    }
    prereq_skills = {check.skill_slug for check in item.candidate.eligibility.checks}
    needed = hard_sources | prereq_skills
    earlier = []
    for other in packed:
        if other.position >= item.position:
            continue
        if other.gate is not None and other.gate.skill_slug in needed:
            earlier.append(other)
            continue
        if other.candidate is None:
            continue
        covered = {
            skill_row.slug
            for skill_row in other.candidate.resource.skills
            if skill_row.coverage_strength >= 0.35 or skill_row.is_primary
        }
        if covered & needed or other.candidate.primary_skill in needed:
            earlier.append(other)
    return earlier


def _explain_gate(item: PlannedItem) -> PathCause:
    gate = item.gate
    assert gate is not None
    return PathCause(
        why_selected=gate.reason,
        why_this_skill=(
            f"{gate.skill_slug.replace('_', ' ')} is UNKNOWN. The system needs evidence; "
            f"it does not assign proficiency 0 or treat the skill as a numeric gap."
        ),
        why_this_position=(
            f"Verification gate at position {item.position} before downstream learning "
            f"that depends on this skill."
        ),
        why_this_intervention=(
            "Intervention is VERIFY. This is a verification gate, not a learning resource."
        ),
        why_this_resource=(
            "No catalog course is assigned. A future assessment can attach to this gate."
        ),
        why_not_earlier=(
            "Evidence is missing, so the system cannot recommend downstream resources yet."
        ),
    )


def explain_item(
    item: PlannedItem,
    packed: list[PlannedItem],
    profile: GapProfile,
    edges: list[SkillEdge],
) -> PathCause:
    if item.gate is not None or item.kind == PathItemKind.VERIFICATION_GATE.value:
        return _explain_gate(item)

    assert item.candidate is not None
    index = gap_index(profile)
    skill = item.candidate.primary_skill
    gap = index.get(skill)
    coverage = _coverage(item, skill)
    action = gap.action.value if gap is not None else "NONE"
    importance = gap.ranked.gap.importance if gap is not None else 0.0
    predecessors = _hard_predecessors(item, packed, edges)
    blocked = unblocks_focal(skill, profile)

    if not item.executable and item.candidate.eligibility.status is EligibilityStatus.BLOCKED_BY_UNKNOWN:
        unknown = [
            check.skill_slug
            for check in item.candidate.eligibility.checks
            if check.state.value == "UNKNOWN"
        ]
        names = ", ".join(s.replace("_", " ") for s in unknown) or "a prerequisite"
        return PathCause(
            why_selected=(
                f"{item.candidate.resource.title} covers {skill.replace('_', ' ')} but is not "
                f"executable until {names} is verified."
            ),
            why_this_skill=f"Primary covered skill is {skill.replace('_', ' ')}.",
            why_this_position=(
                f"WAITING_FOR_VERIFICATION at position {item.position}; not a ready-to-start course."
            ),
            why_this_intervention=(
                f"Intervention {item.candidate.intervention.value} is deferred behind a verification gate."
            ),
            why_this_resource=(
                f"{item.candidate.resource.title} maps to {skill.replace('_', ' ')} "
                f"with structured coverage {coverage:.0%}, type {item.candidate.resource.type}, "
                f"not from title similarity."
            ),
            why_not_earlier=f"Not treated as mastered: {names} is UNKNOWN.",
        )

    if not item.executable and item.candidate.eligibility.status is EligibilityStatus.BLOCKED_BY_KNOWN_GAP:
        missing = [
            check.skill_slug
            for check in item.candidate.eligibility.checks
            if check.state.value == "UNSATISFIED"
        ]
        names = ", ".join(s.replace("_", " ") for s in missing) or "a prerequisite"
        return PathCause(
            why_selected=(
                f"{item.candidate.resource.title} covers {skill.replace('_', ' ')} but is blocked "
                f"by a known gap on {names}."
            ),
            why_this_skill=(
                f"Learner evidence on {skill.replace('_', ' ')} is "
                f"{gap.ranked.gap.attainment.value if gap else 'unknown'} versus target."
            ),
            why_this_position=(
                f"WAITING_FOR_REMEDIATION at position {item.position}; blocker remediation comes first."
            ),
            why_this_intervention=(
                f"Intervention {item.candidate.intervention.value} waits until {names} is remediated."
            ),
            why_this_resource=(
                f"{item.candidate.resource.title} maps to {skill.replace('_', ' ')} "
                f"with structured coverage {coverage:.0%}, type {item.candidate.resource.type}, "
                f"not from title similarity."
            ),
            why_not_earlier=f"Not immediately safe: known gap on {names}.",
        )

    if gap is not None and is_known_focal(gap):
        why_selected = (
            f"Selected because it covers {skill.replace('_', ' ')} "
            f"(coverage {coverage:.0%}), a diagnosed {action} gap for "
            f"{profile.role_name} (role importance {importance:.0%})."
        )
        why_skill = (
            f"Learner evidence on {skill.replace('_', ' ')} is "
            f"{gap.ranked.gap.attainment.value} versus target "
            f"{gap.ranked.gap.target_level:.0%}."
        )
    elif blocked:
        why_selected = (
            f"Selected as an unblock intervention: {skill.replace('_', ' ')} is a HARD "
            f"blocker for {', '.join(s.replace('_', ' ') for s in blocked)}."
        )
        why_skill = (
            f"{skill.replace('_', ' ')} is UNKNOWN or unmet, so it must be addressed "
            f"before the blocked target skill."
        )
    else:
        why_selected = (
            f"Selected because it covers role skill {skill.replace('_', ' ')} "
            f"for {profile.role_name}."
        )
        why_skill = f"Primary covered skill is {skill.replace('_', ' ')}."

    why_resource = (
        f"{item.candidate.resource.title} maps to {skill.replace('_', ' ')} "
        f"with structured coverage {coverage:.0%}, type {item.candidate.resource.type}, "
        f"not from title similarity."
    )
    why_intervention = (
        f"Intervention is {item.candidate.intervention.value} from gap action {action} "
        f"and resource type {item.candidate.resource.type}."
    )

    if predecessors:
        names = ", ".join(
            row.gate.skill_slug if row.gate else row.candidate.resource.slug
            for row in predecessors[:3]
            if row.gate or row.candidate
        )
        why_position = (
            f"Position {item.position} follows {names} because of HARD skill edges "
            f"or resource prerequisites."
        )
        why_not_earlier = f"Not earlier: depends on {names}."
    elif item.position == 0:
        why_position = "Position 0: no unmet HARD predecessor among selected items."
        why_not_earlier = "Nothing in this path is required before it."
    else:
        why_position = (
            f"Position {item.position} after higher-priority diagnosed gaps in wave order."
        )
        why_not_earlier = "Earlier slots were used for higher-priority diagnosed gaps or unblockers."

    return PathCause(
        why_selected=why_selected,
        why_this_skill=why_skill,
        why_this_position=why_position,
        why_this_intervention=why_intervention,
        why_this_resource=why_resource,
        why_not_earlier=why_not_earlier,
    )


def attach_causes(
    packed: list[PlannedItem],
    profile: GapProfile,
    edges: list[SkillEdge],
) -> list[PlannedItem]:
    return [
        PlannedItem(
            candidate=item.candidate,
            position=item.position,
            week_index=item.week_index,
            cause=explain_item(item, packed, profile, edges),
            kind=item.kind,
            executable=item.executable,
            gate=item.gate,
        )
        for item in packed
    ]
