"""Immediate action classification. Not resource recommendation."""

from __future__ import annotations

from app.core.engine_config import EngineConfig, load_engine_config
from app.core.enums import ActionClass, AttainmentStatus
from app.services.gap_engine.calculator import SkillGap
from app.services.skill_graph.dependency import PrerequisiteGate


def classify_action(gap: SkillGap, gate: PrerequisiteGate) -> ActionClass:
    """Semantic next-step class. Blocked skills are not 'learn this now'."""
    if gate.blocked:
        return ActionClass.REMEDIATE_BLOCKER
    if gap.attainment is AttainmentStatus.UNKNOWN:
        return ActionClass.VERIFY
    if gap.attainment is AttainmentStatus.TARGET_MET:
        return ActionClass.ADVANCE
    if gap.attainment is AttainmentStatus.NEAR_TARGET:
        return ActionClass.REINFORCE
    return ActionClass.REMEDIATE


def action_priority(
    action: ActionClass,
    *,
    gap_priority: float,
    verification_priority: float,
    config: EngineConfig | None = None,
) -> float:
    """Lexicographic class tiers plus a small within-tier component.

    Tiers never cross: REMEDIATE > REINFORCE > VERIFY > REMEDIATE_BLOCKER > ADVANCE.
    This is not a resource score.
    """
    cfg = config or load_engine_config()
    tiers = {
        ActionClass.REMEDIATE: cfg.action_remediate_tier,
        ActionClass.REINFORCE: cfg.action_reinforce_tier,
        ActionClass.VERIFY: cfg.action_verify_tier,
        ActionClass.REMEDIATE_BLOCKER: cfg.action_remediate_blocker_tier,
        ActionClass.ADVANCE: cfg.action_advance_tier,
    }
    within = verification_priority if action is ActionClass.VERIFY else gap_priority
    return round(tiers[action] + 0.05 * within, 6)


def downstream_impact_label(*, hard_count: int, soft_count: int) -> str:
    if hard_count >= 3:
        return "HIGH"
    if hard_count >= 1:
        return "MODERATE"
    if soft_count >= 1:
        return "LOW"
    return "NONE"
