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


@dataclass(frozen=True)
class PrerequisiteGate:
    skill_slug: str
    blocked: bool
    blockers: tuple[str, ...]
    preparation_needed: bool
    preparation_skills: tuple[str, ...]


def incoming(edges: list[SkillEdge], skill_slug: str, kind: RelationshipType) -> tuple[str, ...]:
    return tuple(
        sorted(
            edge.source
            for edge in edges
            if edge.target == skill_slug and edge.relationship_type == kind.value
        )
    )


def resolve_prerequisite_gate(
    *,
    skill_slug: str,
    edges: list[SkillEdge],
    prereq_met: dict[str, bool],
) -> PrerequisiteGate:
    """Direct incoming edges only. RELATED is ignored.

    A prerequisite is unmet unless prereq_met[slug] is True.
    Missing keys are treated as unmet (no invented sufficiency).
    """
    hard = incoming(edges, skill_slug, RelationshipType.HARD_PREREQUISITE)
    soft = incoming(edges, skill_slug, RelationshipType.SOFT_PREREQUISITE)
    blockers = tuple(slug for slug in hard if not prereq_met.get(slug, False))
    prep = tuple(slug for slug in soft if not prereq_met.get(slug, False))
    return PrerequisiteGate(
        skill_slug=skill_slug,
        blocked=len(blockers) > 0,
        blockers=blockers,
        preparation_needed=len(prep) > 0,
        preparation_skills=prep,
    )
