"""Deterministic gap explanations. No LLM."""

from __future__ import annotations

from app.core.enums import GapStatus
from app.services.gap_engine.prioritizer import PrioritizedGap


def explain_gap(item: PrioritizedGap, *, role_name: str) -> str:
    gap = item.gap
    name = gap.skill_name
    if gap.gap_status is GapStatus.UNKNOWN:
        blocking = (
            f" It is a blocking gap: {len(item.impact.hard_role_descendants)} downstream "
            f"{role_name} competencies depend on it via HARD prerequisites."
            if item.impact.hard_role_descendants
            else " It does not currently block other role competencies via HARD prerequisites."
        )
        return (
            f"{name} is UNKNOWN for the {role_name} role. The target level is "
            f"{gap.target_level:.0%}, but there is no evidence yet. "
            f"UNKNOWN is not a beginner score.{blocking}"
        )

    assert gap.proficiency is not None and gap.gap is not None
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
    return (
        f"{name} is a {item.severity.value} {gap.gap_status.value.lower()} for the "
        f"{role_name} role. Current evidence estimates proficiency at "
        f"{gap.proficiency:.0%}, while the target is {gap.target_level:.0%} "
        f"(gap {gap.gap:.0%}, importance {gap.importance:.0%})."
        f"{downstream}{conflict}"
    )
