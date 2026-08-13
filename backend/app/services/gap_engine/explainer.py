"""Deterministic gap explanations. No LLM."""

from __future__ import annotations

from app.core.enums import ActionClass, AttainmentStatus, GapStatus
from app.services.gap_engine.prioritizer import PrioritizedGap
from app.services.skill_graph.dependency import PrerequisiteGate


def explain_gap(
    item: PrioritizedGap,
    *,
    role_name: str,
    gate: PrerequisiteGate | None = None,
    action: ActionClass | None = None,
) -> str:
    gap = item.gap
    name = gap.skill_name
    action_text = f" Immediate action: {action.value}." if action is not None else ""

    if gap.gap_status is GapStatus.UNKNOWN:
        blocking = (
            f" It would HARD-gate {len(item.impact.hard_role_descendants)} downstream "
            f"{role_name} competencies if it remains unverified."
            if item.impact.hard_role_descendants
            else " It does not currently HARD-gate other role competencies."
        )
        blocked = ""
        if gate is not None and gate.blocked:
            blocked = f" It is blocked by unmet HARD prerequisites: {', '.join(gate.blockers)}."
        return (
            f"{name} is UNKNOWN for the {role_name} role. The target level is "
            f"{gap.target_level:.0%}, but there is no evidence yet. "
            f"UNKNOWN is not a beginner score.{blocking}{blocked}{action_text}"
        )

    assert gap.proficiency is not None and gap.gap is not None
    if gap.attainment is AttainmentStatus.TARGET_MET:
        attainment_text = "the target is met"
    elif gap.attainment is AttainmentStatus.NEAR_TARGET:
        attainment_text = "the learner is near target but has not met it"
    else:
        attainment_text = "the target is not met"

    downstream = (
        f" It supports {len(item.impact.hard_role_descendants)} downstream role "
        f"competencies as a HARD prerequisite, so closing it unblocks later work."
        if item.impact.hard_role_descendants
        else " It has little HARD downstream impact on other role competencies."
    )
    conflict = (
        f" Evidence sources disagree; the estimate is weighted toward {gap.dominant_source}."
        if gap.conflict and gap.dominant_source
        else ""
    )
    blocked = ""
    if gate is not None and gate.blocked:
        blocked = f" Progress here is blocked until HARD prerequisites are met: {', '.join(gate.blockers)}."
    elif gate is not None and gate.preparation_needed:
        blocked = (
            f" SOFT preparation would help first: {', '.join(gate.preparation_skills)}."
        )
    return (
        f"{name} is a {item.severity.value} {gap.gap_status.value.lower()} for the "
        f"{role_name} role ({attainment_text}). Current evidence estimates proficiency at "
        f"{gap.proficiency:.0%}, while the target is {gap.target_level:.0%} "
        f"(gap {gap.gap:.0%}, importance {gap.importance:.0%})."
        f"{downstream}{conflict}{blocked}{action_text}"
    )
