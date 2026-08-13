"""Causal gates for path selection. A high score is not sufficient."""

from __future__ import annotations

from app.core.enums import ActionClass, AttainmentStatus, EvidenceState
from app.services.gap_engine.profile import ExplainedGap, GapProfile
from app.services.recommendation.models import ScoredCandidate, gap_index


FOCAL_ACTIONS = {
    ActionClass.REMEDIATE,
    ActionClass.REINFORCE,
    ActionClass.REMEDIATE_BLOCKER,
}


def is_known_focal(item: ExplainedGap) -> bool:
    """A diagnosed gap with evidence. UNKNOWN role skills are not focal."""
    if item.action is ActionClass.ADVANCE:
        return False
    if item.ranked.gap.attainment is AttainmentStatus.TARGET_MET:
        return False
    if item.ranked.gap.evidence_state is not EvidenceState.KNOWN:
        return False
    return item.action in FOCAL_ACTIONS


def unblocks_focal(skill_slug: str, profile: GapProfile) -> tuple[str, ...]:
    """Focal skills that list this skill as an unmet HARD blocker."""
    return tuple(
        item.ranked.gap.skill_slug
        for item in profile.items
        if is_known_focal(item) and skill_slug in item.gate.blockers
    )


def is_selectable_skill(skill_slug: str, profile: GapProfile) -> bool:
    item = gap_index(profile).get(skill_slug)
    if item is None:
        return False
    if is_known_focal(item):
        return True
    return False


def has_role_relevance(candidate: ScoredCandidate, *, min_importance: float = 0.01) -> bool:
    return candidate.breakdown.role_importance >= min_importance
