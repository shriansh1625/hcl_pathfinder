"""Gap prioritization. Not resource recommendation."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.engine_config import EngineConfig, load_engine_config
from app.core.enums import GapSeverity, GapStatus
from app.services.gap_engine.calculator import SkillGap
from app.services.skill_graph.dependency import DownstreamImpact


@dataclass(frozen=True)
class PrioritizedGap:
    gap: SkillGap
    impact: DownstreamImpact
    prerequisite_criticality: float
    confidence_adjustment: float
    priority: float
    severity: GapSeverity
    is_blocking: bool


def _severity(gap: SkillGap, impact: DownstreamImpact, priority: float) -> GapSeverity:
    if gap.gap_status is GapStatus.UNKNOWN:
        return GapSeverity.UNKNOWN
    if gap.gap_status is GapStatus.SATISFIED:
        return GapSeverity.NONE
    if gap.gap_status is GapStatus.DEVELOPING:
        return GapSeverity.MODERATE
    if impact.is_blocking and gap.importance >= 0.75:
        return GapSeverity.CRITICAL
    if gap.importance >= 0.80 or priority >= 0.35:
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
    if gap.gap_status is GapStatus.SATISFIED:
        confidence_adjustment = 1.0
        priority = 0.0
    elif gap.gap_status is GapStatus.UNKNOWN:
        confidence_adjustment = 1.0
        priority = gap.importance * criticality * cfg.unknown_importance_weight
    else:
        confidence = gap.confidence if gap.confidence is not None else 0.0
        confidence_adjustment = cfg.min_confidence_adjustment + (
            1.0 - cfg.min_confidence_adjustment
        ) * confidence
        magnitude = gap.gap if gap.gap is not None else 0.0
        priority = magnitude * gap.importance * criticality * confidence_adjustment

    return PrioritizedGap(
        gap=gap,
        impact=impact,
        prerequisite_criticality=criticality,
        confidence_adjustment=confidence_adjustment,
        priority=priority,
        severity=_severity(gap, impact, priority),
        is_blocking=impact.is_blocking and gap.gap_status is not GapStatus.SATISFIED,
    )
