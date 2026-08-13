"""Deterministic skill-graph traversal.

HARD edges contribute blocking descendants.
SOFT edges contribute preparation descendants.
RELATED never blocks and is ignored for impact.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from app.core.enums import RelationshipType


@dataclass(frozen=True)
class SkillEdge:
    source: str
    target: str
    relationship_type: str
    strength: float


def _adjacency(edges: list[SkillEdge], kind: RelationshipType) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.relationship_type == kind.value:
            graph[edge.source].append(edge.target)
    return graph


def descendants(graph: dict[str, list[str]], start: str) -> set[str]:
    seen: set[str] = set()
    queue: deque[str] = deque(graph.get(start, []))
    while queue:
        node = queue.popleft()
        if node in seen:
            continue
        seen.add(node)
        queue.extend(graph.get(node, []))
    return seen


@dataclass(frozen=True)
class DownstreamImpact:
    skill_slug: str
    hard_descendants: tuple[str, ...]
    soft_descendants: tuple[str, ...]
    hard_role_descendants: tuple[str, ...]
    soft_role_descendants: tuple[str, ...]
    is_blocking: bool


def downstream_impact(
    *,
    skill_slug: str,
    edges: list[SkillEdge],
    role_slugs: set[str],
) -> DownstreamImpact:
    hard_graph = _adjacency(edges, RelationshipType.HARD_PREREQUISITE)
    soft_graph = _adjacency(edges, RelationshipType.SOFT_PREREQUISITE)
    hard = descendants(hard_graph, skill_slug)
    soft = descendants(soft_graph, skill_slug) - hard
    hard_role = tuple(sorted(hard & role_slugs))
    soft_role = tuple(sorted(soft & role_slugs))
    return DownstreamImpact(
        skill_slug=skill_slug,
        hard_descendants=tuple(sorted(hard)),
        soft_descendants=tuple(sorted(soft)),
        hard_role_descendants=hard_role,
        soft_role_descendants=soft_role,
        is_blocking=len(hard_role) > 0,
    )
