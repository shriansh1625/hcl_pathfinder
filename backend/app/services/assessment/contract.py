"""Future assessment integration contract. Slice 2.2 does not score questions."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import EvidenceSource


@dataclass(frozen=True)
class AssessmentResult:
    """Normalized outcome a future runtime would emit. Not computed here."""

    assessment_slug: str
    skill_slug: str
    observed_level: float
    confidence: float
    passed: bool | None = None


def evidence_from_assessment(result: AssessmentResult) -> dict:
    """Map an assessment result onto skill_evidence fields.

    Callers persist this as evidence, then recompute fusion, gaps, and
    resource eligibility. This function does not grade items.
    """
    return {
        "skill": result.skill_slug,
        "source": EvidenceSource.ASSESSMENT.value,
        "observed_level": result.observed_level,
        "confidence": result.confidence,
        "evidence_payload": {
            "assessment": result.assessment_slug,
            "passed": result.passed,
        },
    }
