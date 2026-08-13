"""AssessmentResult → normalized append-only evidence dicts.

One evidence row per assessed skill. Uses the existing ASSESSMENT source
(reliability 0.90 from data/ontology/reliability.yaml). Previous evidence
is never overwritten; fusion reconciles.
"""

from __future__ import annotations

import uuid

from app.core.enums import EvidenceSource
from app.services.assessment.scoring import AssessmentScore


def evidence_rows_from_score(
    score: AssessmentScore,
    *,
    attempt_id: uuid.UUID,
) -> list[dict]:
    rows: list[dict] = []
    for skill in score.skill_results:
        rows.append(
            {
                "skill": skill.skill_slug,
                "source": EvidenceSource.ASSESSMENT.value,
                "observed_level": skill.observed_level,
                "confidence": skill.confidence,
                "evidence_payload": {
                    "assessment": score.assessment_slug,
                    "attempt_id": str(attempt_id),
                    "question_count": skill.question_count,
                    "difficulty_avg": round(skill.difficulty_avg, 6),
                    "consistency": skill.consistency,
                },
            }
        )
    return rows
