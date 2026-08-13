"""Gap prioritization. Not resource recommendation. Not immediate-action ranking."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.engine_config import EngineConfig, load_engine_config
from app.core.enums import AttainmentStatus, GapSeverity, GapStatus
from app.services.gap_engine.calculator import SkillGap
from app.services.skill_graph.dependency import DownstreamImpact


@dataclass(frozen=True)
class PrioritizedGap:
    gap: SkillGap
    impact: DownstreamImpact
    prerequisite_criticality: float
    confidence_adjustment: float
    priority: float
    gap_priority: float
    verification_priority: float
    severity: GapSeverity
    is_blocking: bool


def _severity(gap: SkillGap, impact: DownstreamImpact, gap_priority: float) -> GapSeverity:
    if gap.gap_status is GapStatus.UNKNOWN:
        return GapSeverity.UNKNOWN
    if gap.attainment is AttainmentStatus.TARGET_MET:
        return GapSeverity.NONE
    if gap.attainment is AttainmentStatus.NEAR_TARGET:
        return GapSeverity.LOW
    if gap.gap_status is GapStatus.DEVELOPING:
        return GapSeverity.MODERATE
    if impact.is_blocking and gap.importance >= 0.75:
        return GapSeverity.CRITICAL
    if gap.importance >= 0.80 or gap_priority >= 0.35:
        return GapSeverity.HIGH
    return GapSeverity.HIGH if gap.gap_status is GapStatus.GAP else GapSeverity.LOW


def prioritize_gap(
    gap: SkillGap,
    impact: DownstreamImpact,
    *,
    config: EngineConfig | None = None,
) -> PrioritizedGap:
    cfg = config or load_engine_config()
    criticality = (
        1.0
        + cfg.hard_descendant_weight * len(impact.hard_role_descendants)
        + cfg.soft_descendant_weight * len(impact.soft_role_descendants)
    )

    if gap.attainment is AttainmentStatus.UNKNOWN:
        confidence_adjustment = 1.0
        gap_priority = 0.0
        verification_priority = gap.importance * criticality * cfg.unknown_importance_weight
    elif gap.attainment is AttainmentStatus.TARGET_MET:
        confidence_adjustment = 1.0
        gap_priority = 0.0
        verification_priority = 0.0
    else:
        confidence = gap.confidence if gap.confidence is not None else 0.0
        confidence_adjustment = cfg.min_confidence_adjustment + (
            1.0 - cfg.min_confidence_adjustment
        ) * confidence
        magnitude = gap.gap if gap.gap is not None else 0.0
        gap_priority = magnitude * gap.importance * criticality * confidence_adjustment
        verification_priority = 0.0

    return PrioritizedGap(
        gap=gap,
        impact=impact,
        prerequisite_criticality=criticality,
        confidence_adjustment=confidence_adjustment,
        priority=gap_priority,
        gap_priority=gap_priority,
        verification_priority=verification_priority,
        severity=_severity(gap, impact, gap_priority),
        is_blocking=impact.is_blocking and gap.attainment is not AttainmentStatus.TARGET_MET,
    )
