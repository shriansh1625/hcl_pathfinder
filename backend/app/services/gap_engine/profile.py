"""Assemble a career gap profile from fused skills + role graph."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import ActionClass
from app.core.skill_state import resolve_target_met
from app.services.gap_engine.actions import action_priority, classify_action, downstream_impact_label
from app.services.gap_engine.calculator import SkillGap, calculate_gap
from app.services.gap_engine.explainer import explain_gap
from app.services.gap_engine.prioritizer import PrioritizedGap, prioritize_gap
from app.services.profiling.evidence_fusion import FusedSkill
from app.services.skill_graph.competency import RoleCompetencySet
from app.services.skill_graph.dependency import (
    PrerequisiteGate,
    SkillEdge,
    downstream_impact,
    resolve_prerequisite_gate,
)


@dataclass(frozen=True)
class ExplainedGap:
    ranked: PrioritizedGap
    gate: PrerequisiteGate
    action: ActionClass
    action_priority: float
    downstream_impact: str
    explanation: str


@dataclass(frozen=True)
class GapProfile:
    role_slug: str
    role_name: str
    items: tuple[ExplainedGap, ...]


def _prereq_met_map(
    gaps: list[SkillGap],
    fused_by_slug: dict[str, FusedSkill],
    role: RoleCompetencySet,
) -> dict[str, bool]:
    met: dict[str, bool] = {item.skill_slug: item.target_met is True for item in gaps}
    role_targets = {item.skill_slug: item.target_level for item in role.competencies}
    for slug, fused in fused_by_slug.items():
        if slug in met:
            continue
        met[slug] = (
            resolve_target_met(proficiency=fused.proficiency, target_level=role_targets.get(slug))
            is True
        )
    return met


def build_gap_profile(
    *,
    fused_by_slug: dict[str, FusedSkill],
    role: RoleCompetencySet,
    edges: list[SkillEdge],
) -> GapProfile:
    role_slugs = role.slugs()
    gaps = [
        calculate_gap(fused_by_slug.get(competency.skill_slug), competency)
        for competency in role.competencies
    ]
    prereq_met = _prereq_met_map(gaps, fused_by_slug, role)
    items: list[ExplainedGap] = []
    for competency, gap in zip(role.competencies, gaps, strict=True):
        impact = downstream_impact(
            skill_slug=competency.skill_slug,
            edges=edges,
            role_slugs=role_slugs,
        )
        ranked = prioritize_gap(gap, impact)
        gate = resolve_prerequisite_gate(
            skill_slug=competency.skill_slug,
            edges=edges,
            prereq_met=prereq_met,
        )
        action = classify_action(gap, gate)
        items.append(
            ExplainedGap(
                ranked=ranked,
                gate=gate,
                action=action,
                action_priority=action_priority(
                    action,
                    gap_priority=ranked.gap_priority,
                    verification_priority=ranked.verification_priority,
                ),
                downstream_impact=downstream_impact_label(
                    hard_count=len(impact.hard_role_descendants),
                    soft_count=len(impact.soft_role_descendants),
                ),
                explanation=explain_gap(ranked, gate=gate, action=action, role_name=role.role_name),
            )
        )
    items.sort(
        key=lambda item: (
            -item.ranked.gap_priority,
            -item.action_priority,
            item.ranked.gap.skill_slug,
        )
    )
    return GapProfile(role_slug=role.role_slug, role_name=role.role_name, items=tuple(items))
