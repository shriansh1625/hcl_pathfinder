"""Learner skill status semantics.

NO EVIDENCE ≠ ZERO.
Missing evidence means UNKNOWN. Proficiency is null until evidence exists.
This is a domain contract, not the gap/recommendation engine.
"""

from __future__ import annotations

from app.core.enums import SkillStatus

STRONG_MAX_GAP = 0.15
GAP_MIN_DELTA = 0.40


def resolve_skill_status(
    *,
    has_evidence: bool,
    proficiency: float | None,
    target_level: float | None = None,
) -> SkillStatus:
    if not has_evidence or proficiency is None:
        return SkillStatus.UNKNOWN

    if target_level is None:
        if proficiency >= 0.75:
            return SkillStatus.STRONG
        return SkillStatus.DEVELOPING

    gap = max(0.0, target_level - proficiency)
    if gap <= STRONG_MAX_GAP:
        return SkillStatus.STRONG
    if gap >= GAP_MIN_DELTA:
        return SkillStatus.GAP
    return SkillStatus.DEVELOPING
