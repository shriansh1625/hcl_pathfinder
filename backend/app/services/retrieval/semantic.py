"""Optional semantic retrieval. Deterministic fallback; no network, no pgvector."""

from __future__ import annotations

from app.ontology.load import ResourceSpec
from app.services.recommendation.config import load_recommendation_config


class SemanticRetriever:
    """Interface for a future embedding backend.

    Slice 2 returns a configured constant so missing embeddings cannot
    break recommendation or change relative ranking.
    """

    def similarity(self, resource: ResourceSpec, query_skills: tuple[str, ...]) -> float:
        if not query_skills:
            return 0.0
        _ = resource.slug
        return load_recommendation_config().fallback_similarity
