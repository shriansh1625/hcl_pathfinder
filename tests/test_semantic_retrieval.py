"""Semantic relevance retrieval tests. No live model downloads."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.enums import AttainmentStatus, EligibilityStatus, RequiredStatus
from app.core.skill_state import resolve_skill_status
from app.ontology.load import ResourcePrereqSpec, ResourceSkillSpec, ResourceSpec, load_ontology
from app.services.gap_engine.profile import build_gap_profile
from app.services.path.generator import generate_path, select_for_path
from app.services.profiling.evidence_fusion import FusedSkill
from app.services.recommendation.config import load_recommendation_config
from app.services.recommendation.models import LearnerPreferences, ScoreBreakdown, ScoredCandidate
from app.services.recommendation.scorer import score_candidates, score_resource
from app.services.retrieval.embeddings import (
    EmbeddingArtifact,
    EmbeddingStore,
    build_query_document,
    build_resource_document,
    cosine_similarity,
    load_embedding_artifact,
    semantic_similarity,
)
from app.services.retrieval.semantic import SemanticRetriever
from app.services.skill_graph.competency import RoleCompetency, RoleCompetencySet
from app.services.skill_graph.dependency import SkillEdge


def _fused(slug: str, proficiency: float | None) -> FusedSkill:
    return FusedSkill(
        skill_slug=slug,
        proficiency=proficiency,
        confidence=None if proficiency is None else 0.8,
        status=resolve_skill_status(
            has_evidence=proficiency is not None,
            proficiency=proficiency,
            target_level=0.8,
        ),
        evidence_count=0 if proficiency is None else 1,
        conflict=False,
        conflict_spread=0.0,
        dominant_source=None if proficiency is None else "ASSESSMENT",
        weights=(),
        reason="fixture",
    )


def _resource(
    slug: str,
    skill: str,
    *,
    coverage: float = 0.85,
    duration: float = 4,
    difficulty: int = 2,
    modes=None,
    prereqs=None,
    title: str | None = None,
    description: str | None = None,
):
    return ResourceSpec(
        slug=slug,
        title=title or slug,
        description=description or slug,
        type="course",
        difficulty=difficulty,
        duration_hours=duration,
        source="test",
        url=None,
        url_status="unavailable",
        learning_modes=list(modes or ["reading"]),
        is_active=True,
        skills=[ResourceSkillSpec(skill, coverage, 0.2, True)],
        prerequisites=[ResourcePrereqSpec(p[0], p[1]) for p in (prereqs or [])],
    )


def _profile(skills: dict[str, float | None]):
    bundle = load_ontology()
    role = next(item for item in bundle.roles if item.slug == "ai-ml-engineer")
    competencies = tuple(
        RoleCompetency(
            row.slug,
            row.slug,
            row.target_level,
            row.importance,
            RequiredStatus(row.required_status),
        )
        for row in role.skills
    )
    edges = []
    fused = {slug: _fused(slug, value) for slug, value in skills.items()}
    return build_gap_profile(
        fused_by_slug=fused,
        role=RoleCompetencySet(role.slug, role.name, competencies),
        edges=edges,
    )


def _fixed_store() -> EmbeddingStore:
    artifact = EmbeddingArtifact(
        model="test-fixed",
        dimensions=3,
        resources={
            "ml-focused": (1.0, 0.0, 0.0),
            "unrelated": (0.0, 1.0, 0.0),
        },
    )

    def embed_query(_text: str) -> list[float]:
        return [1.0, 0.0, 0.0]

    return EmbeddingStore(artifact, query_embedder=embed_query)


def test_embedding_artifact_loads_from_repo_file():
    artifact = load_embedding_artifact()
    assert artifact is not None
    assert artifact.model == "BAAI/bge-small-en-v1.5"
    assert artifact.dimensions > 0
    assert len(artifact.resources) >= 50


def test_similarity_is_within_unit_interval():
    store = _fixed_store()
    profile = _profile({"ml_fundamentals": 0.3})
    ml = _resource("ml-focused", "ml_fundamentals")
    other = _resource("unrelated", "javascript")
    ml_score = semantic_similarity(ml, profile, store=store, enabled=True)
    other_score = semantic_similarity(other, profile, store=store, enabled=True)
    assert 0.0 <= ml_score <= 1.0
    assert 0.0 <= other_score <= 1.0
    assert ml_score > other_score


def test_fallback_when_vectors_or_model_unavailable():
    cfg = load_recommendation_config()
    profile = _profile({"ml_fundamentals": 0.3})
    resource = _resource("missing", "ml_fundamentals")
    store = EmbeddingStore(None)
    assert semantic_similarity(resource, profile, store=store, enabled=True) == cfg.fallback_similarity
    assert semantic_similarity(resource, profile, store=store, enabled=False) == cfg.fallback_similarity


def test_semantically_relevant_resource_scores_higher_with_fixed_vectors():
    store = _fixed_store()
    profile = _profile({"ml_fundamentals": 0.3})
    relevant = _resource("ml-focused", "ml_fundamentals")
    unrelated = _resource("unrelated", "javascript")
    assert semantic_similarity(relevant, profile, store=store, enabled=True) > semantic_similarity(
        unrelated, profile, store=store, enabled=True
    )


def test_semantic_similarity_can_change_ranking_when_other_factors_match():
    from app.core import config

    config.settings.semantic_enabled = True
    store = _fixed_store()
    stats = RoleCompetency("statistics", "Statistics", 0.8, 0.9, RequiredStatus.CORE)
    profile = build_gap_profile(
        fused_by_slug={"statistics": _fused("statistics", 0.3)},
        role=RoleCompetencySet("aiml", "AI/ML", (stats,)),
        edges=[],
    )
    relevant = _resource(
        "ml-focused",
        "statistics",
        title="Statistics for Machine Learning",
        description="statistics machine learning foundations",
    )
    other = _resource(
        "unrelated",
        "statistics",
        title="Unrelated Topic",
        description="unrelated content",
    )
    prefs = LearnerPreferences(8, "MIXED")
    retriever = SemanticRetriever(store=store)
    scored = [
        score_resource(item, profile, prefs, semantic=retriever)
        for item in [other, relevant]
    ]
    by_slug = {item.resource.slug: item for item in scored}
    assert by_slug["ml-focused"].breakdown.final_score > by_slug["unrelated"].breakdown.final_score


def test_semantic_similarity_cannot_bypass_zero_role_importance_selection():
    store = _fixed_store()
    stats = RoleCompetency("statistics", "Statistics", 0.8, 0.9, RequiredStatus.CORE)
    profile = build_gap_profile(
        fused_by_slug={"statistics": _fused("statistics", 0.3)},
        role=RoleCompetencySet("aiml", "AI/ML", (stats,)),
        edges=[],
    )
    relevant = _resource("stats-course", "statistics", coverage=0.85)
    impostor = _resource("impostor", "statistics", coverage=0.99)
    prefs = LearnerPreferences(8, "HANDS_ON")
    retriever = SemanticRetriever(store=store)
    scored = score_candidates([relevant, impostor], profile, prefs)
    impostor_scored = next(item for item in scored if item.resource.slug == "impostor")
    fake_high = ScoredCandidate(
        resource=impostor_scored.resource,
        primary_skill=impostor_scored.primary_skill,
        eligibility=impostor_scored.eligibility,
        intervention=impostor_scored.intervention,
        breakdown=ScoreBreakdown(
            skill_gap_fit=0.99,
            role_importance=0.0,
            prerequisite_fit=1.0,
            difficulty_fit=1.0,
            duration_fit=1.0,
            learning_style_fit=1.0,
            semantic_similarity=0.99,
            final_score=0.92,
        ),
        explanation=impostor_scored.explanation,
    )
    cfg = load_recommendation_config()
    selected = select_for_path(
        [fake_high, *[item for item in scored if item.resource.slug == "stats-course"]],
        profile,
        weekly_hours=8,
        max_items=cfg.max_items,
        horizon_weeks=cfg.horizon_weeks,
    )
    slugs = [item.resource.slug for item in selected]
    assert "impostor" not in slugs
    assert "stats-course" in slugs


def test_semantic_similarity_cannot_bypass_prerequisite_eligibility():
    from app.core import config

    config.settings.semantic_enabled = True
    store = _fixed_store()
    profile = _profile({"python": None, "ml_fundamentals": 0.2})
    blocked = _resource(
        "ml-focused",
        "ml_fundamentals",
        prereqs=[("python", 0.5)],
        title="ML course",
        description="machine learning",
    )
    retriever = SemanticRetriever(store=store)
    scored = score_resource(blocked, profile, LearnerPreferences(8, "MIXED"), semantic=retriever)
    assert scored.eligibility.status is EligibilityStatus.BLOCKED_BY_UNKNOWN
    assert scored.breakdown.semantic_similarity > 0.9


def test_query_document_uses_deterministic_gap_context_only():
    profile = _profile({"ml_fundamentals": 0.3, "python": 0.4})
    query = build_query_document(profile)
    assert "Career target:" in query
    assert "Priority gap:" in query
    assert "TARGET_MET" not in query


def test_cosine_similarity_mapping():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.5


def test_path_generation_remains_functional_with_semantic_enabled(monkeypatch):
    monkeypatch.setattr(
        "app.services.retrieval.embeddings.default_store",
        lambda: _fixed_store(),
    )
    bundle = load_ontology()
    profile = _profile({"python": 0.45, "statistics": 0.90, "ml_fundamentals": 0.30})
    path = generate_path(profile, bundle.resources, [], LearnerPreferences(8, "READING"))
    assert path.items


def test_adaptation_engine_still_uses_generate_path_without_llm():
    import inspect

    from app.services.adaptation import engine

    source = inspect.getsource(engine)
    assert "explain" not in source
    assert "OpenAI" not in source
    assert "generate_path" in source


def test_resource_document_contains_catalog_fields_only():
    resource = _resource(
        "ml-focused",
        "ml_fundamentals",
        title="ML Basics",
        description="Foundational machine learning concepts.",
        modes=["video"],
    )
    text = build_resource_document(resource)
    assert "ML Basics" in text
    assert "Foundational machine learning" in text
    assert "video" in text


@pytest.fixture
def tmp_artifact(tmp_path: Path):
    payload = {
        "model": "test",
        "dimensions": 2,
        "resources": {"a": [1.0, 0.0]},
    }
    path = tmp_path / "resource_embeddings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_fallback_semantic_disabled_uses_constant_similarity():
    cfg = load_recommendation_config()
    profile = _profile({"ml_fundamentals": 0.3})
    resources = [
        _resource("ml-focused", "ml_fundamentals"),
        _resource("unrelated", "javascript"),
    ]
    prefs = LearnerPreferences(8, "MIXED")
    from app.core import config

    config.settings.semantic_enabled = False
    scored = score_candidates(resources, profile, prefs)
    assert all(item.breakdown.semantic_similarity == cfg.fallback_similarity for item in scored)


def test_fallback_malformed_artifact(tmp_path: Path):
    cfg = load_recommendation_config()
    bad = tmp_path / "resource_embeddings.json"
    bad.write_text("{not-json", encoding="utf-8")
    assert load_embedding_artifact(bad) is None
    profile = _profile({"ml_fundamentals": 0.3})
    resource = _resource("ml-focused", "ml_fundamentals")
    store = EmbeddingStore(load_embedding_artifact(bad))
    assert semantic_similarity(resource, profile, store=store, enabled=True) == cfg.fallback_similarity


def test_fallback_embedding_failure_returns_constant():
    cfg = load_recommendation_config()
    artifact = EmbeddingArtifact(
        model="test",
        dimensions=2,
        resources={"ml-focused": (1.0, 0.0)},
    )

    def fail_embed(_text: str) -> None:
        return None

    store = EmbeddingStore(artifact, query_embedder=fail_embed)
    profile = _profile({"ml_fundamentals": 0.3})
    resource = _resource("ml-focused", "ml_fundamentals")
    assert semantic_similarity(resource, profile, store=store, enabled=True) == cfg.fallback_similarity


def test_runtime_uses_bge_artifact_and_setting():
    from app.core import config

    artifact = load_embedding_artifact()
    assert artifact is not None
    assert artifact.model == "BAAI/bge-small-en-v1.5"
    assert config.settings.embedding_model == "BAAI/bge-small-en-v1.5"
    assert artifact.dimensions == 384


def test_semantic_on_reorders_tied_eligible_candidates():
    """Controlled forensic case: identical deterministic components, semantic breaks tie."""
    from app.core import config

    stats = RoleCompetency("sql", "SQL", 0.8, 0.6, RequiredStatus.CORE)
    profile = build_gap_profile(
        fused_by_slug={"sql": _fused("sql", 0.35)},
        role=RoleCompetencySet("data", "Data", (stats,)),
        edges=[],
    )
    tied_a = _resource(
        "sqlbolt",
        "sql",
        title="SQLBolt",
        description="Interactive SQL lessons",
        duration=6,
        difficulty=2,
        modes=["reading", "project"],
    )
    tied_b = _resource(
        "mdn-http",
        "sql",
        title="HTTP overview",
        description="HTTP protocol documentation",
        duration=6,
        difficulty=2,
        modes=["reading"],
    )
    prefs = LearnerPreferences(8, "READING")

    config.settings.semantic_enabled = False
    off = score_candidates([tied_a, tied_b], profile, prefs)
    off_order = [item.resource.slug for item in off]

    config.settings.semantic_enabled = True
    on = score_candidates([tied_a, tied_b], profile, prefs)
    on_order = [item.resource.slug for item in on]

    off_scores = {item.resource.slug: item.breakdown.semantic_similarity for item in off}
    on_scores = {item.resource.slug: item.breakdown.semantic_similarity for item in on}
    assert off_scores["sqlbolt"] == off_scores["mdn-http"] == 0.5
    assert on_scores["sqlbolt"] != on_scores["mdn-http"]
    assert on_order != off_order
    assert {item.breakdown.skill_gap_fit for item in on} == {item.breakdown.skill_gap_fit for item in off}
    assert {item.breakdown.role_importance for item in on} == {item.breakdown.role_importance for item in off}


def test_unknown_profile_emits_verification_gates_not_learning_courses():
    bundle = load_ontology()
    role = next(item for item in bundle.roles if item.slug == "ai-ml-engineer")
    competencies = tuple(
        RoleCompetency(
            row.slug,
            row.slug,
            row.target_level,
            row.importance,
            RequiredStatus(row.required_status),
        )
        for row in role.skills
    )
    fused = {row.slug: _fused(row.slug, None) for row in role.skills}
    edges = [
        SkillEdge(rel.source, rel.target, rel.type, rel.strength)
        for rel in bundle.relationships
    ]
    profile = build_gap_profile(
        fused_by_slug=fused,
        role=RoleCompetencySet(role.slug, role.name, competencies),
        edges=edges,
    )
    from app.core import config

    config.settings.semantic_enabled = True
    path = generate_path(profile, bundle.resources, edges, LearnerPreferences(8, "READING"))
    assert path.items
    assert not any(
        item.kind == "EXECUTABLE" and item.executable and item.candidate is not None
        for item in path.items
    )
    assert any(item.kind == "VERIFICATION_GATE" for item in path.items)


def test_semantic_cannot_bypass_blocked_by_known_gap():
    store = _fixed_store()
    profile = _profile({"python": 0.2, "ml_fundamentals": 0.55})
    blocked = _resource(
        "ml-focused",
        "ml_fundamentals",
        prereqs=[("python", 0.5)],
        title="ML course",
        description="machine learning",
    )
    retriever = SemanticRetriever(store=store)
    scored = score_resource(blocked, profile, LearnerPreferences(8, "MIXED"), semantic=retriever)
    assert scored.eligibility.status is EligibilityStatus.BLOCKED_BY_KNOWN_GAP
    assert scored.breakdown.semantic_similarity > 0.9


def test_high_semantic_impostor_not_selected_for_executable_path():
    store = _fixed_store()
    stats = RoleCompetency("statistics", "Statistics", 0.8, 0.9, RequiredStatus.CORE)
    profile = build_gap_profile(
        fused_by_slug={"statistics": _fused("statistics", 0.3)},
        role=RoleCompetencySet("aiml", "AI/ML", (stats,)),
        edges=[],
    )
    relevant = _resource("stats-course", "statistics", coverage=0.85)
    impostor = _resource("impostor", "statistics", coverage=0.99)
    prefs = LearnerPreferences(8, "HANDS_ON")
    scored = score_candidates([relevant, impostor], profile, prefs)
    impostor_scored = next(item for item in scored if item.resource.slug == "impostor")
    fake_high = ScoredCandidate(
        resource=impostor_scored.resource,
        primary_skill=impostor_scored.primary_skill,
        eligibility=impostor_scored.eligibility,
        intervention=impostor_scored.intervention,
        breakdown=ScoreBreakdown(
            skill_gap_fit=0.99,
            role_importance=0.0,
            prerequisite_fit=1.0,
            difficulty_fit=1.0,
            duration_fit=1.0,
            learning_style_fit=1.0,
            semantic_similarity=0.99,
            final_score=0.92,
        ),
        explanation=impostor_scored.explanation,
    )
    cfg = load_recommendation_config()
    selected = select_for_path(
        [fake_high, *[item for item in scored if item.resource.slug == "stats-course"]],
        profile,
        weekly_hours=8,
        max_items=cfg.max_items,
        horizon_weeks=cfg.horizon_weeks,
    )
    executable = [item for item in selected if item.resource.slug == "impostor"]
    assert executable == []
