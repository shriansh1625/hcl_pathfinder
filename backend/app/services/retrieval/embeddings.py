"""Offline resource embeddings + deterministic query text for semantic similarity."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

from app.core.config import settings
from app.core.enums import AttainmentStatus
from app.core.paths import DATA_DIR
from app.ontology.load import OntologyBundle, ResourceSpec, load_ontology
from app.services.gap_engine.profile import GapProfile
from app.services.recommendation.config import load_recommendation_config

logger = logging.getLogger(__name__)

EMBEDDING_ARTIFACT_PATH = DATA_DIR / "catalog" / "resource_embeddings.json"
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
MAX_QUERY_GAPS = 5

QueryEmbedder = Callable[[str], list[float] | None]


@dataclass(frozen=True)
class EmbeddingArtifact:
    model: str
    dimensions: int
    resources: dict[str, tuple[float, ...]]


def skill_name_map(bundle: OntologyBundle | None = None) -> dict[str, str]:
    ontology = bundle or load_ontology()
    return {skill.slug: skill.canonical_name for skill in ontology.skills}


def skill_description_map(bundle: OntologyBundle | None = None) -> dict[str, str]:
    ontology = bundle or load_ontology()
    return {skill.slug: skill.description for skill in ontology.skills}


def build_resource_document(
    resource: ResourceSpec,
    *,
    skill_names: dict[str, str] | None = None,
) -> str:
    names = skill_names or skill_name_map()
    taught = ", ".join(names.get(item.slug, item.slug) for item in resource.skills)
    modes = ", ".join(resource.learning_modes)
    return (
        f"{resource.title}. {resource.description} "
        f"Teaches: {taught}. Type: {resource.type}. Modes: {modes}."
    )


def build_query_document(profile: GapProfile, bundle: OntologyBundle | None = None) -> str:
    ontology = bundle or load_ontology()
    role = next((item for item in ontology.roles if item.slug == profile.role_slug), None)
    role_description = role.description if role is not None else ""
    descriptions = skill_description_map(ontology)
    names = skill_name_map(ontology)

    parts = [f"Career target: {profile.role_name}. {role_description}".strip()]
    gaps = [
        item
        for item in profile.items
        if item.ranked.gap.attainment is not AttainmentStatus.TARGET_MET
    ]
    gaps.sort(key=lambda item: (-item.action_priority, item.ranked.gap.skill_slug))
    for item in gaps[:MAX_QUERY_GAPS]:
        slug = item.ranked.gap.skill_slug
        name = names.get(slug, item.ranked.gap.skill_name)
        description = descriptions.get(slug, "")
        severity = item.ranked.severity.value
        parts.append(
            f"Priority gap: {name} ({item.action.value}, severity {severity}, "
            f"priority {item.action_priority:.2f}). {description} {item.explanation}"
        )
    return " ".join(part for part in parts if part)


def cosine_similarity(left: list[float] | tuple[float, ...], right: list[float] | tuple[float, ...]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_left = sum(a * a for a in left) ** 0.5
    norm_right = sum(b * b for b in right) ** 0.5
    if norm_left == 0.0 or norm_right == 0.0:
        return 0.0
    raw = dot / (norm_left * norm_right)
    return max(0.0, min(1.0, (raw + 1.0) / 2.0))


def load_embedding_artifact(path: Path | None = None) -> EmbeddingArtifact | None:
    artifact_path = path or EMBEDDING_ARTIFACT_PATH
    if not artifact_path.exists():
        return None
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        resources = {
            slug: tuple(float(value) for value in vector)
            for slug, vector in payload["resources"].items()
        }
        return EmbeddingArtifact(
            model=str(payload["model"]),
            dimensions=int(payload["dimensions"]),
            resources=resources,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Could not load embedding artifact: %s", exc)
        return None


class EmbeddingStore:
    """Loads precomputed resource vectors and embeds deterministic query text."""

    def __init__(
        self,
        artifact: EmbeddingArtifact | None,
        *,
        query_embedder: QueryEmbedder | None = None,
    ) -> None:
        self._artifact = artifact
        self._query_embedder = query_embedder
        self._query_cache: dict[str, list[float]] = {}

    @classmethod
    def from_default(cls) -> EmbeddingStore:
        return cls(load_embedding_artifact())

    def resource_vector(self, slug: str) -> tuple[float, ...] | None:
        if self._artifact is None:
            return None
        return self._artifact.resources.get(slug)

    def embed_query(self, text: str) -> list[float] | None:
        if not text.strip():
            return None
        cached = self._query_cache.get(text)
        if cached is not None:
            return cached
        if self._query_embedder is not None:
            vector = self._query_embedder(text)
            if vector is not None:
                self._query_cache[text] = vector
            return vector
        try:
            model = _runtime_embedder()
            vectors = list(model.embed([text]))
            if not vectors:
                return None
            vector = [float(value) for value in vectors[0]]
            self._query_cache[text] = vector
            return vector
        except Exception as exc:  # noqa: BLE001 - provider failures must fall back safely
            logger.warning("Query embedding failed: %s", exc)
            return None

    def similarity(self, resource_slug: str, query_text: str) -> float | None:
        resource_vector = self.resource_vector(resource_slug)
        query_vector = self.embed_query(query_text)
        if resource_vector is None or query_vector is None:
            return None
        if len(resource_vector) != len(query_vector):
            return None
        return cosine_similarity(resource_vector, query_vector)


@lru_cache(maxsize=1)
def _runtime_embedder():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=settings.embedding_model)


@lru_cache(maxsize=1)
def default_store() -> EmbeddingStore:
    return EmbeddingStore.from_default()


def semantic_similarity(
    resource: ResourceSpec,
    profile: GapProfile,
    *,
    store: EmbeddingStore | None = None,
    enabled: bool | None = None,
) -> float:
    cfg = load_recommendation_config()
    if enabled is None:
        enabled = settings.semantic_enabled
    if not enabled:
        return cfg.fallback_similarity

    active_store = store if store is not None else default_store()
    if active_store._artifact is None:
        return cfg.fallback_similarity

    query = build_query_document(profile)
    score = active_store.similarity(resource.slug, query)
    if score is None:
        return cfg.fallback_similarity
    return round(score, 6)
