"""Assemble a career gap profile from fused skills + role graph."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.gap_engine.calculator import calculate_gap
from app.services.gap_engine.explainer import explain_gap
from app.services.gap_engine.prioritizer import PrioritizedGap, prioritize_gap
from app.services.profiling.evidence_fusion import FusedSkill
from app.services.skill_graph.competency import RoleCompetencySet
from app.services.skill_graph.dependency import SkillEdge, downstream_impact


@dataclass(frozen=True)
class ExplainedGap:
    ranked: PrioritizedGap
    explanation: str


@dataclass(frozen=True)
class GapProfile:
    role_slug: str
    role_name: str
    items: tuple[ExplainedGap, ...]


def build_gap_profile(
    *,
    fused_by_slug: dict[str, FusedSkill],
    role: RoleCompetencySet,
    edges: list[SkillEdge],
) -> GapProfile:
    role_slugs = role.slugs()
    items: list[ExplainedGap] = []
    for competency in role.competencies:
        fused = fused_by_slug.get(competency.skill_slug)
        gap = calculate_gap(fused, competency)
        impact = downstream_impact(
            skill_slug=competency.skill_slug,
            edges=edges,
            role_slugs=role_slugs,
        )
        ranked = prioritize_gap(gap, impact)
        items.append(
            ExplainedGap(
                ranked=ranked,
                explanation=explain_gap(ranked, role_name=role.role_name),
            )
        )
    items.sort(key=lambda item: item.ranked.priority, reverse=True)
    return GapProfile(role_slug=role.role_slug, role_name=role.role_name, items=tuple(items))
