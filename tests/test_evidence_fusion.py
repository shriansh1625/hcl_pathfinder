from datetime import datetime, timedelta, timezone

from app.core.enums import EvidenceSource, SkillStatus
from app.services.profiling.evidence_fusion import EvidenceRecord, fuse_skill_evidence


NOW = datetime(2026, 8, 13, tzinfo=timezone.utc)


def _record(source: str, level: float, *, days_ago: int = 0, confidence: float = 0.8, reliability: float) -> EvidenceRecord:
    return EvidenceRecord(
        skill_slug="python",
        source=source,
        observed_level=level,
        reliability=reliability,
        confidence=confidence,
        created_at=NOW - timedelta(days=days_ago),
    )


def test_no_evidence_is_unknown_not_zero():
    fused = fuse_skill_evidence([], skill_slug="python", now=NOW)
    assert fused.proficiency is None
    assert fused.confidence is None
    assert fused.status is SkillStatus.UNKNOWN
    assert fused.evidence_count == 0


def test_fusion_is_deterministic():
    records = [
        _record(EvidenceSource.SELF_REPORT.value, 0.7, reliability=0.35),
        _record(EvidenceSource.ASSESSMENT.value, 0.5, reliability=0.90),
    ]
    first = fuse_skill_evidence(records, now=NOW)
    second = fuse_skill_evidence(records, now=NOW)
    assert first.proficiency == second.proficiency
    assert first.confidence == second.confidence
    assert first.dominant_source == second.dominant_source


def test_assessment_outweighs_self_report_and_keeps_both():
    records = [
        _record(EvidenceSource.SELF_REPORT.value, 0.90, reliability=0.35),
        _record(EvidenceSource.ASSESSMENT.value, 0.55, reliability=0.90),
    ]
    fused = fuse_skill_evidence(records, now=NOW)
    assert fused.proficiency is not None
    assert 0.55 < fused.proficiency < 0.90
    assert fused.proficiency < 0.70
    assert fused.dominant_source == EvidenceSource.ASSESSMENT.value
    assert fused.conflict is True
    assert fused.evidence_count == 2
    assert len(fused.weights) == 2


def test_recency_downweights_old_evidence():
    fresh = _record(EvidenceSource.SELF_REPORT.value, 0.90, days_ago=0, reliability=0.35)
    stale = _record(EvidenceSource.SELF_REPORT.value, 0.10, days_ago=720, reliability=0.35)
    fused = fuse_skill_evidence([fresh, stale], now=NOW)
    assert fused.proficiency is not None
    assert fused.proficiency > 0.70
