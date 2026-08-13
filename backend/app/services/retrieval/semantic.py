"""Optional semantic retrieval. Embedding-based catalog relevance with safe fallback."""

from __future__ import annotations

from app.ontology.load import ResourceSpec
from app.services.gap_engine.profile import GapProfile
from app.services.retrieval.embeddings import EmbeddingStore, default_store, semantic_similarity


class SemanticRetriever:
    """Catalog-only semantic relevance signal.

    Contributes the configured semantic_similarity weight in scoring.
    Never selects resources, never overrides eligibility, and never writes state.
    """

    def __init__(self, store: EmbeddingStore | None = None) -> None:
        self._store = store if store is not None else default_store()

    def similarity(self, resource: ResourceSpec, profile: GapProfile) -> float:
        return semantic_similarity(resource, profile, store=self._store)
