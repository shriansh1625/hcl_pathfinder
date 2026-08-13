"""Explainable resource scoring. Components are in [0, 1]."""

from __future__ import annotations

from app.core.enums import AttainmentStatus, EligibilityStatus, LearningStyle
from app.ontology.load import ResourceSpec
from app.services.gap_engine.profile import GapProfile
from app.services.recommendation.config import RecommendationConfig, load_recommendation_config
from app.services.recommendation.eligibility import evaluate_resource
from app.services.recommendation.models import (
    LearnerPreferences,
    ScoreBreakdown,
    ScoredCandidate,
    gap_index,
    proficiency_map,
)
from app.services.retrieval.semantic import SemanticRetriever
from app.services.recommendation.explanation import explain_recommendation
from app.services.recommendation.intervention import infer_intervention


def difficulty_fit(resource_difficulty: int, learner_level: float) -> float:
    """Map difficulty 1–5 and learner proficiency in [0, 1] onto the same axis.

    A beginner (0.2) vs difficulty 5 is a poor fit. A strong learner (0.85)
    vs difficulty 1 is also a poor fit.
    """
    resource_level = (resource_difficulty - 1) / 4.0
    return round(max(0.0, 1.0 - abs(resource_level - learner_level)), 6)


def duration_fit(duration_hours: float, weekly_hours: float) -> float:
    if weekly_hours <= 0:
        return 0.0
    if duration_hours <= weekly_hours:
        return 1.0
    if duration_hours <= 2 * weekly_hours:
        return 0.70
    if duration_hours <= 4 * weekly_hours:
        return 0.40
    return 0.20


def learning_style_fit(modes: list[str], style: str) -> float:
    normalized = {item.lower() for item in modes}
    preference = LearningStyle(style)
    if preference is LearningStyle.VIDEO:
        return 1.0 if "video" in normalized else 0.35
    if preference is LearningStyle.READING:
        return 1.0 if "reading" in normalized else 0.35
    if preference is LearningStyle.HANDS_ON:
        return 1.0 if normalized & {"lab", "project"} else 0.35
    if preference is LearningStyle.PROJECT:
        return 1.0 if "project" in normalized else 0.40
    return 0.90 if len(normalized) >= 2 else 0.75


def _learner_level(resource: ResourceSpec, profile: GapProfile) -> float:
    known: list[float] = []
    index = gap_index(profile)
    for skill in resource.skills:
        item = index.get(skill.slug)
        if item is not None and item.ranked.gap.proficiency is not None:
            known.append(item.ranked.gap.proficiency)
    if known:
        return sum(known) / len(known)
    return 0.40


def _skill_gap_fit(resource: ResourceSpec, profile: GapProfile) -> float:
    index = gap_index(profile)
    max_action = max((item.action_priority for item in profile.items), default=1.0) or 1.0
    best = 0.0
    for skill in resource.skills:
        item = index.get(skill.slug)
        if item is None:
            continue
        action_norm = item.action_priority / max_action
        gap_boost = 1.0
        if item.ranked.gap.attainment is AttainmentStatus.TARGET_MET:
            gap_boost = 0.15
        elif item.ranked.gap.attainment is AttainmentStatus.UNKNOWN:
            gap_boost = 0.55
        elif item.ranked.gap.attainment is AttainmentStatus.NEAR_TARGET:
            gap_boost = 0.70
        best = max(best, skill.coverage_strength * action_norm * gap_boost)
    return round(best, 6)


def _role_importance(resource: ResourceSpec, profile: GapProfile) -> float:
    index = gap_index(profile)
    best = 0.0
    for skill in resource.skills:
        item = index.get(skill.slug)
        if item is None:
            continue
        best = max(best, skill.coverage_strength * item.ranked.gap.importance)
    return round(best, 6)


def _prerequisite_fit(status: EligibilityStatus, cfg: RecommendationConfig) -> float:
    if status is EligibilityStatus.ELIGIBLE:
        return 1.0
    if status is EligibilityStatus.BLOCKED_BY_UNKNOWN:
        return cfg.unknown_prerequisite_fit
    return cfg.unsatisfied_prerequisite_fit


def _primary_skill(resource: ResourceSpec, profile: GapProfile) -> str:
    index = gap_index(profile)
    primary = [skill for skill in resource.skills if skill.is_primary and skill.slug in index]
    if primary:
        return max(primary, key=lambda skill: skill.coverage_strength).slug
    covered = [skill for skill in resource.skills if skill.slug in index]
    if covered:
        return max(covered, key=lambda skill: skill.coverage_strength).slug
    return resource.skills[0].slug if resource.skills else resource.slug


def score_resource(
    resource: ResourceSpec,
    profile: GapProfile,
    prefs: LearnerPreferences,
    *,
    semantic: SemanticRetriever | None = None,
    config: RecommendationConfig | None = None,
) -> ScoredCandidate:
    cfg = config or load_recommendation_config()
    retriever = semantic or SemanticRetriever()
    eligibility = evaluate_resource(resource, proficiency_map(profile))
    primary = _primary_skill(resource, profile)
    breakdown = ScoreBreakdown(
        skill_gap_fit=_skill_gap_fit(resource, profile),
        role_importance=_role_importance(resource, profile),
        prerequisite_fit=_prerequisite_fit(eligibility.status, cfg),
        difficulty_fit=difficulty_fit(resource.difficulty, _learner_level(resource, profile)),
        duration_fit=duration_fit(resource.duration_hours, prefs.weekly_hours),
        learning_style_fit=learning_style_fit(resource.learning_modes, prefs.learning_style),
        semantic_similarity=retriever.similarity(resource, profile),
        final_score=0.0,
    )
    total = cfg.weight_total() or 1.0
    final = (
        cfg.skill_gap_fit * breakdown.skill_gap_fit
        + cfg.role_importance * breakdown.role_importance
        + cfg.prerequisite_fit * breakdown.prerequisite_fit
        + cfg.difficulty_fit * breakdown.difficulty_fit
        + cfg.duration_fit * breakdown.duration_fit
        + cfg.learning_style_fit * breakdown.learning_style_fit
        + cfg.semantic_similarity * breakdown.semantic_similarity
    ) / total
    breakdown = ScoreBreakdown(
        skill_gap_fit=breakdown.skill_gap_fit,
        role_importance=breakdown.role_importance,
        prerequisite_fit=breakdown.prerequisite_fit,
        difficulty_fit=breakdown.difficulty_fit,
        duration_fit=breakdown.duration_fit,
        learning_style_fit=breakdown.learning_style_fit,
        semantic_similarity=breakdown.semantic_similarity,
        final_score=round(final, 6),
    )
    intervention = infer_intervention(resource, gap_index(profile).get(primary))
    return ScoredCandidate(
        resource=resource,
        primary_skill=primary,
        eligibility=eligibility,
        intervention=intervention,
        breakdown=breakdown,
        explanation=explain_recommendation(
            resource, breakdown, eligibility, prefs, primary, profile.role_name
        ),
    )


def score_candidates(
    resources: list[ResourceSpec],
    profile: GapProfile,
    prefs: LearnerPreferences,
) -> list[ScoredCandidate]:
    scored = [score_resource(item, profile, prefs) for item in resources]
    scored.sort(key=lambda item: (-item.breakdown.final_score, item.resource.slug))
    return scored
