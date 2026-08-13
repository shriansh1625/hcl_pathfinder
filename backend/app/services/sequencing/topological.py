"""Deterministic topological order. Ranking is not the path order."""

from __future__ import annotations

from collections import deque

from app.services.recommendation.models import ScoredCandidate
from app.services.sequencing.dependency_graph import hard_successors, soft_successors
from app.services.skill_graph.dependency import SkillEdge


def sequence_resources(
    selected: list[ScoredCandidate],
    edges: list[SkillEdge],
) -> list[ScoredCandidate]:
    if not selected:
        return []
    by_slug = {item.resource.slug: item for item in selected}
    hard = hard_successors(selected, edges)
    soft = soft_successors(selected, edges)
    incoming: dict[str, int] = {slug: 0 for slug in by_slug}
    for src, dests in hard.items():
        for dest in dests:
            if dest in incoming and src in incoming:
                incoming[dest] += 1
    ready = deque(
        sorted(
            (slug for slug, count in incoming.items() if count == 0),
            key=lambda slug: _ready_key(by_slug[slug], soft),
        )
    )
    ordered: list[ScoredCandidate] = []
    remaining = set(by_slug)
    while ready:
        slug = ready.popleft()
        if slug not in remaining:
            continue
        remaining.remove(slug)
        ordered.append(by_slug[slug])
        for dest in sorted(hard.get(slug, ()), key=lambda item: _ready_key(by_slug[item], soft)):
            incoming[dest] -= 1
            if incoming[dest] == 0:
                ready.append(dest)
        ready = deque(sorted(ready, key=lambda item: _ready_key(by_slug[item], soft)))
    if remaining:
        leftover = sorted(remaining, key=lambda slug: (-by_slug[slug].breakdown.final_score, slug))
        ordered.extend(by_slug[slug] for slug in leftover)
    return ordered


def _ready_key(candidate: ScoredCandidate, soft: dict[str, set[str]]) -> tuple:
    soft_pref = 0 if any(candidate.resource.slug in dests for dests in soft.values()) else 1
    return (candidate.resource.difficulty, -soft_pref, -candidate.breakdown.final_score, candidate.resource.slug)
