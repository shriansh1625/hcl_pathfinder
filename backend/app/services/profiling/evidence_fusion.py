"""Deterministic evidence fusion.

weight_i = reliability_i × confidence_i × recency_i
recency_i = 0.5 ** (age_days / half_life_days)
proficiency = Σ(observed_i × weight_i) / Σ(weight_i)
confidence = 1 − exp(−k × Σ weight_i)

No evidence → proficiency and confidence are None (UNKNOWN, not zero).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp

from app.core.engine_config import EngineConfig, load_engine_config
from app.core.enums import SkillStatus
from app.core.skill_state import resolve_skill_status


@dataclass(frozen=True)
class EvidenceRecord:
    skill_slug: str
    source: str
    observed_level: float
    reliability: float
    confidence: float
    created_at: datetime


@dataclass(frozen=True)
class EvidenceWeight:
    source: str
    observed_level: float
    reliability: float
    confidence: float
    recency: float
    weight: float
    created_at: datetime


@dataclass(frozen=True)
class FusedSkill:
    skill_slug: str
    proficiency: float | None
    confidence: float | None
    status: SkillStatus
    evidence_count: int
    conflict: bool
    conflict_spread: float | None
    dominant_source: str | None
    weights: tuple[EvidenceWeight, ...]
    reason: str


def recency_weight(created_at: datetime, *, now: datetime, half_life_days: float) -> float:
    if half_life_days <= 0:
        return 1.0
    point = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    as_of = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (as_of - point).total_seconds() / 86400.0)
    return 0.5 ** (age_days / half_life_days)


def fuse_skill_evidence(
    records: list[EvidenceRecord],
    *,
    skill_slug: str | None = None,
    now: datetime | None = None,
    config: EngineConfig | None = None,
    target_level: float | None = None,
) -> FusedSkill:
    cfg = config or load_engine_config()
    as_of = now or datetime.now(timezone.utc)
    slug = skill_slug or (records[0].skill_slug if records else "")
    if not records:
        return FusedSkill(
            skill_slug=slug,
            proficiency=None,
            confidence=None,
            status=SkillStatus.UNKNOWN,
            evidence_count=0,
            conflict=False,
            conflict_spread=None,
            dominant_source=None,
            weights=(),
            reason="No evidence. Status is UNKNOWN, not beginner and not zero.",
        )

    slug = records[0].skill_slug
    weights: list[EvidenceWeight] = []
    for record in records:
        recency = recency_weight(
            record.created_at, now=as_of, half_life_days=cfg.recency_half_life_days
        )
        weight = record.reliability * record.confidence * recency
        weights.append(
            EvidenceWeight(
                source=record.source,
                observed_level=record.observed_level,
                reliability=record.reliability,
                confidence=record.confidence,
                recency=recency,
                weight=weight,
                created_at=record.created_at,
            )
        )

    total = sum(item.weight for item in weights)
    if total <= 0:
        return FusedSkill(
            skill_slug=slug,
            proficiency=None,
            confidence=None,
            status=SkillStatus.UNKNOWN,
            evidence_count=len(records),
            conflict=False,
            conflict_spread=None,
            dominant_source=None,
            weights=tuple(weights),
            reason="Evidence exists but all weights were zero.",
        )

    proficiency = sum(item.observed_level * item.weight for item in weights) / total
    confidence = 1.0 - exp(-cfg.confidence_saturation * total)
    confidence = min(1.0, max(0.0, confidence))

    observed = [item.observed_level for item in weights]
    spread = max(observed) - min(observed)
    conflict = spread >= cfg.conflict_spread
    dominant = max(weights, key=lambda item: item.weight)

    status = resolve_skill_status(
        has_evidence=True, proficiency=proficiency, target_level=target_level
    )

    if conflict:
        reason = (
            f"Conflicting evidence (spread {spread:.2f}). "
            f"The fused estimate {proficiency:.2f} is weighted toward {dominant.source} "
            f"(weight {dominant.weight:.2f}) over weaker sources."
        )
    else:
        reason = (
            f"Fused from {len(weights)} evidence record(s). "
            f"Dominant source {dominant.source}."
        )

    return FusedSkill(
        skill_slug=slug,
        proficiency=proficiency,
        confidence=confidence,
        status=status,
        evidence_count=len(records),
        conflict=conflict,
        conflict_spread=spread if conflict else spread,
        dominant_source=dominant.source,
        weights=tuple(weights),
        reason=reason,
    )
