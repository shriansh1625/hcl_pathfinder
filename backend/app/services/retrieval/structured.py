"""Structured candidate retrieval. No embeddings required."""

from __future__ import annotations

from app.ontology.load import ResourceSpec
from app.services.gap_engine.profile import GapProfile
from app.services.recommendation.config import load_recommendation_config
from app.services.recommendation.models import gap_index


def retrieve_candidates(
    profile: GapProfile,
    catalog: list[ResourceSpec],
    *,
    min_coverage: float | None = None,
) -> list[ResourceSpec]:
    """Return active resources that cover at least one role skill."""
    cfg = load_recommendation_config()
    threshold = cfg.min_coverage if min_coverage is None else min_coverage
    role_skills = gap_index(profile)
    selected: list[ResourceSpec] = []
    for resource in catalog:
        if not resource.is_active:
            continue
        covers = any(
            skill.slug in role_skills and skill.coverage_strength >= threshold
            for skill in resource.skills
        )
        if covers:
            selected.append(resource)
    selected.sort(key=lambda item: item.slug)
    return selected
