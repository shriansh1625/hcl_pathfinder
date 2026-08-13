"""Configurable gap-engine parameters loaded from YAML."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import yaml

from app.core.paths import DATA_DIR


@dataclass(frozen=True)
class EngineConfig:
    recency_half_life_days: float
    confidence_saturation: float
    conflict_spread: float
    satisfied_max_gap: float
    gap_min_delta: float
    no_target_strong_min: float
    hard_descendant_weight: float
    soft_descendant_weight: float
    unknown_importance_weight: float
    min_confidence_adjustment: float
    action_remediate_tier: float
    action_reinforce_tier: float
    action_verify_tier: float
    action_remediate_blocker_tier: float
    action_advance_tier: float


@lru_cache(maxsize=1)
def load_engine_config() -> EngineConfig:
    path = DATA_DIR / "ontology" / "gap_engine.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    fusion = payload["fusion"]
    classification = payload["classification"]
    priority = payload["priority"]
    action = payload.get("action") or {}
    return EngineConfig(
        recency_half_life_days=float(fusion["recency_half_life_days"]),
        confidence_saturation=float(fusion["confidence_saturation"]),
        conflict_spread=float(fusion["conflict_spread"]),
        satisfied_max_gap=float(classification["satisfied_max_gap"]),
        gap_min_delta=float(classification["gap_min_delta"]),
        no_target_strong_min=float(classification["no_target_strong_min"]),
        hard_descendant_weight=float(priority["hard_descendant_weight"]),
        soft_descendant_weight=float(priority["soft_descendant_weight"]),
        unknown_importance_weight=float(priority["unknown_importance_weight"]),
        min_confidence_adjustment=float(priority["min_confidence_adjustment"]),
        action_remediate_tier=float(action.get("remediate_tier", 3.0)),
        action_reinforce_tier=float(action.get("reinforce_tier", 2.0)),
        action_verify_tier=float(action.get("verify_tier", 1.0)),
        action_remediate_blocker_tier=float(action.get("remediate_blocker_tier", 0.5)),
        action_advance_tier=float(action.get("advance_tier", 0.0)),
    )
