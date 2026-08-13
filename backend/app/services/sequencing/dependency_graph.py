"""Dependency graph among selected resources. Built from skill + resource prereqs."""

from __future__ import annotations

from collections import defaultdict

from app.core.enums import RelationshipType
from app.services.recommendation.models import ScoredCandidate
from app.services.skill_graph.dependency import SkillEdge


def _covers(candidate: ScoredCandidate, skill_slug: str, *, min_coverage: float = 0.55) -> bool:
    return any(
        skill.slug == skill_slug and (skill.is_primary or skill.coverage_strength >= min_coverage)
        for skill in candidate.resource.skills
    )


def hard_successors(
    selected: list[ScoredCandidate],
    edges: list[SkillEdge],
) -> dict[str, set[str]]:
    """slug -> resources that must come after it."""
    by_slug = {item.resource.slug: item for item in selected}
    graph: dict[str, set[str]] = defaultdict(set)
    hard = [
        edge for edge in edges if edge.relationship_type == RelationshipType.HARD_PREREQUISITE.value
    ]
    for left in selected:
        for right in selected:
            if left.resource.slug == right.resource.slug:
                continue
            if any(
                edge.source == left.primary_skill and edge.target == right.primary_skill
                for edge in hard
            ):
                graph[left.resource.slug].add(right.resource.slug)
            if any(
                _covers(left, prereq.slug) and not _covers(right, prereq.slug, min_coverage=0.85)
                for prereq in right.resource.prerequisites
            ):
                graph[left.resource.slug].add(right.resource.slug)
    for slug in by_slug:
        graph.setdefault(slug, set())
    return dict(graph)


def soft_successors(
    selected: list[ScoredCandidate],
    edges: list[SkillEdge],
) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = defaultdict(set)
    soft = [
        edge for edge in edges if edge.relationship_type == RelationshipType.SOFT_PREREQUISITE.value
    ]
    for left in selected:
        for right in selected:
            if left.resource.slug == right.resource.slug:
                continue
            if any(
                edge.source == left.primary_skill and edge.target == right.primary_skill
                for edge in soft
            ):
                graph[left.resource.slug].add(right.resource.slug)
    return dict(graph)
