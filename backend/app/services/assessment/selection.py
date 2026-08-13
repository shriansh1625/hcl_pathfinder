"""Smallest-useful-assessment selection.

Goal: the compact assessment that reduces the most uncertainty for the
target role — not a 100-question quiz. UNKNOWN role skills are ranked by
the existing verification_priority (importance × criticality × weight).
"""

from __future__ import annotations

from app.core.enums import ActionClass, EvidenceState
from app.ontology.load import AssessmentSpec
from app.services.gap_engine.profile import GapProfile

MAX_QUESTIONS = 10


def select_assessment(
    profile: GapProfile,
    assessments: list[AssessmentSpec],
    *,
    max_questions: int = MAX_QUESTIONS,
) -> AssessmentSpec | None:
    unknown_priority = {
        item.ranked.gap.skill_slug: item.ranked.verification_priority
        for item in profile.items
        if item.action is ActionClass.VERIFY
        and item.ranked.gap.evidence_state is EvidenceState.UNKNOWN
    }
    if not unknown_priority:
        return None

    best: AssessmentSpec | None = None
    best_key: tuple[float, int, int, str] | None = None
    for spec in sorted(assessments, key=lambda item: item.slug):
        if len(spec.questions) > max_questions:
            continue
        if spec.target_role is not None and spec.target_role != profile.role_slug:
            continue
        covered = set(spec.target_skills) & set(unknown_priority)
        if not covered:
            continue
        value = sum(unknown_priority[slug] for slug in covered)
        key = (value, len(covered), -len(spec.questions), spec.slug)
        if best_key is None or key > best_key:
            best = spec
            best_key = key
    return best
