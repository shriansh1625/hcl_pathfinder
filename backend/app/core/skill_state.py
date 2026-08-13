"""Learner skill status semantics.

NO EVIDENCE ≠ ZERO.
Missing evidence means UNKNOWN. Proficiency is null until evidence exists.
Thresholds are loaded from data/ontology/gap_engine.yaml.

Slice 1.1 separates:
- evidence state (do we have a measurement?)
- skill status (legacy UNKNOWN / DEVELOPING / STRONG / GAP)
- target attainment (UNKNOWN / GAP / NEAR_TARGET / TARGET_MET)
"""

from __future__ import annotations

from app.core.engine_config import load_engine_config
from app.core.enums import AttainmentStatus, EvidenceState, GapStatus, SkillStatus

# Defaults match Slice 0 tests if config cannot be read.
DEFAULT_SATISFIED_MAX_GAP = 0.15  # near-target band; does NOT mean target_met
DEFAULT_GAP_MIN_DELTA = 0.40
DEFAULT_NO_TARGET_STRONG_MIN = 0.75
EPS = 1e-9


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


def resolve_evidence_state(*, has_evidence: bool, proficiency: float | None) -> EvidenceState:
    if not has_evidence or proficiency is None:
        return EvidenceState.UNKNOWN
    return EvidenceState.KNOWN


def resolve_target_met(*, proficiency: float | None, target_level: float | None) -> bool | None:
    """True only when proficiency exists and is at or above the target.

    Below-target, even by 0.01, is not target_met. UNKNOWN is null.
    """
    if proficiency is None or target_level is None:
        return None
    return proficiency + EPS >= target_level


def resolve_attainment(
    *,
    has_evidence: bool,
    proficiency: float | None,
    target_level: float | None,
) -> AttainmentStatus:
    if not has_evidence or proficiency is None or target_level is None:
        return AttainmentStatus.UNKNOWN

    near_target_max, _, _ = _thresholds()
    gap = max(0.0, target_level - proficiency)
    if gap <= EPS:
        return AttainmentStatus.TARGET_MET
    if gap <= near_target_max + EPS:
        return AttainmentStatus.NEAR_TARGET
    return AttainmentStatus.GAP


def resolve_skill_status(
    *,
    has_evidence: bool,
    proficiency: float | None,
    target_level: float | None = None,
) -> SkillStatus:
    if not has_evidence or proficiency is None:
        return SkillStatus.UNKNOWN

    _, gap_min_delta, no_target_strong_min = _thresholds()

    if target_level is None:
        if proficiency >= no_target_strong_min:
            return SkillStatus.STRONG
        return SkillStatus.DEVELOPING

    gap = max(0.0, target_level - proficiency)
    # STRONG / SATISFIED only when the target is actually met — not "close enough".
    if gap <= EPS:
        return SkillStatus.STRONG
    if gap >= gap_min_delta - EPS:
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
