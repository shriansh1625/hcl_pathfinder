"""Gap magnitude vs a role competency. Does not rank resources."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import GapStatus, SkillStatus
from app.core.skill_state import resolve_skill_status, skill_status_to_gap_status
from app.services.profiling.evidence_fusion import FusedSkill
from app.services.skill_graph.competency import RoleCompetency


@dataclass(frozen=True)
class SkillGap:
    skill_slug: str
    skill_name: str
    target_level: float
    importance: float
    required_status: str
    proficiency: float | None
    confidence: float | None
    learner_status: SkillStatus
    gap: float | None
    normalized_gap: float | None
    gap_status: GapStatus
    evidence_count: int
    conflict: bool
    dominant_source: str | None
    fusion_reason: str


def calculate_gap(fused: FusedSkill | None, competency: RoleCompetency) -> SkillGap:
    if fused is None or fused.proficiency is None:
        return SkillGap(
            skill_slug=competency.skill_slug,
            skill_name=competency.skill_name,
            target_level=competency.target_level,
            importance=competency.importance,
            required_status=competency.required_status.value,
            proficiency=None,
            confidence=None,
            learner_status=SkillStatus.UNKNOWN,
            gap=None,
            normalized_gap=None,
            gap_status=GapStatus.UNKNOWN,
            evidence_count=0 if fused is None else fused.evidence_count,
            conflict=False,
            dominant_source=None,
            fusion_reason="No evidence. UNKNOWN is not a score of zero.",
        )

    gap = round(max(0.0, competency.target_level - fused.proficiency), 6)
    normalized = round(gap / competency.target_level, 6) if competency.target_level > 0 else 0.0
    learner_status = resolve_skill_status(
        has_evidence=True,
        proficiency=fused.proficiency,
        target_level=competency.target_level,
    )
    return SkillGap(
        skill_slug=competency.skill_slug,
        skill_name=competency.skill_name,
        target_level=competency.target_level,
        importance=competency.importance,
        required_status=competency.required_status.value,
        proficiency=fused.proficiency,
        confidence=fused.confidence,
        learner_status=learner_status,
        gap=gap,
        normalized_gap=normalized,
        gap_status=skill_status_to_gap_status(learner_status),
        evidence_count=fused.evidence_count,
        conflict=fused.conflict,
        dominant_source=fused.dominant_source,
        fusion_reason=fused.reason,
    )
