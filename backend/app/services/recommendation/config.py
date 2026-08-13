"""Recommendation configuration loaded from YAML."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import yaml

from app.core.paths import DATA_DIR


@dataclass(frozen=True)
class RecommendationConfig:
    skill_gap_fit: float
    role_importance: float
    prerequisite_fit: float
    difficulty_fit: float
    duration_fit: float
    learning_style_fit: float
    semantic_similarity: float
    default_weekly_hours: float
    default_learning_style: str
    horizon_weeks: int
    max_items: int
    min_coverage: float
    unknown_prerequisite_fit: float
    unsatisfied_prerequisite_fit: float
    fallback_similarity: float

    def weight_total(self) -> float:
        return (
            self.skill_gap_fit
            + self.role_importance
            + self.prerequisite_fit
            + self.difficulty_fit
            + self.duration_fit
            + self.learning_style_fit
            + self.semantic_similarity
        )


@lru_cache(maxsize=1)
def load_recommendation_config() -> RecommendationConfig:
    path = DATA_DIR / "ontology" / "recommendation.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    weights = payload["weights"]
    selection = payload["selection"]
    eligibility = payload["eligibility"]
    semantic = payload["semantic"]
    return RecommendationConfig(
        skill_gap_fit=float(weights["skill_gap_fit"]),
        role_importance=float(weights["role_importance"]),
        prerequisite_fit=float(weights["prerequisite_fit"]),
        difficulty_fit=float(weights["difficulty_fit"]),
        duration_fit=float(weights["duration_fit"]),
        learning_style_fit=float(weights["learning_style_fit"]),
        semantic_similarity=float(weights["semantic_similarity"]),
        default_weekly_hours=float(selection["default_weekly_hours"]),
        default_learning_style=str(selection["default_learning_style"]),
        horizon_weeks=int(selection["horizon_weeks"]),
        max_items=int(selection["max_items"]),
        min_coverage=float(selection["min_coverage"]),
        unknown_prerequisite_fit=float(eligibility["unknown_prerequisite_fit"]),
        unsatisfied_prerequisite_fit=float(eligibility["unsatisfied_prerequisite_fit"]),
        fallback_similarity=float(semantic["fallback_similarity"]),
    )
