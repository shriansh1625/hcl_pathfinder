"""Learner skill status semantics.

NO EVIDENCE ≠ ZERO.
Missing evidence means UNKNOWN. Proficiency is null until evidence exists.
Thresholds are loaded from data/ontology/gap_engine.yaml.
"""

from __future__ import annotations

from app.core.engine_config import load_engine_config
from app.core.enums import GapStatus, SkillStatus

# Defaults match Slice 0 tests if config cannot be read.
DEFAULT_SATISFIED_MAX_GAP = 0.15
DEFAULT_GAP_MIN_DELTA = 0.40
DEFAULT_NO_TARGET_STRONG_MIN = 0.75


def _thresholds() -> tuple[float, float, float]:
    try:
        cfg = load_engine_config()
        return cfg.satisfied_max_gap, cfg.gap_min_delta, cfg.no_target_strong_min
    except OSError:
        return (
            DEFAULT_SATISFIED_MAX_GAP,
            DEFAULT_GAP_MIN_DELTA,
            DEFAULT_NO_TARGET_STRONG_MIN,
        )


def resolve_skill_status(
    *,
    has_evidence: bool,
    proficiency: float | None,
    target_level: float | None = None,
) -> SkillStatus:
    if not has_evidence or proficiency is None:
        return SkillStatus.UNKNOWN

    satisfied_max_gap, gap_min_delta, no_target_strong_min = _thresholds()

    if target_level is None:
        if proficiency >= no_target_strong_min:
            return SkillStatus.STRONG
        return SkillStatus.DEVELOPING

    gap = max(0.0, target_level - proficiency)
    # Thresholds are YAML floats; treat exact boundary hits as inclusive.
    if gap <= satisfied_max_gap + 1e-9:
        return SkillStatus.STRONG
    if gap >= gap_min_delta - 1e-9:
        return SkillStatus.GAP
    return SkillStatus.DEVELOPING


def skill_status_to_gap_status(status: SkillStatus) -> GapStatus:
    if status is SkillStatus.UNKNOWN:
        return GapStatus.UNKNOWN
    if status is SkillStatus.STRONG:
        return GapStatus.SATISFIED
    if status is SkillStatus.DEVELOPING:
        return GapStatus.DEVELOPING
    return GapStatus.GAP
