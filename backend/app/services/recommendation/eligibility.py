"""Resource prerequisite eligibility. UNKNOWN is not UNSATISFIED."""

from __future__ import annotations

from app.core.enums import EligibilityStatus, PrerequisiteEvidenceState
from app.ontology.load import ResourceSpec
from app.services.recommendation.models import Eligibility, PrerequisiteCheck


def check_prerequisite(min_level: float, observed: float | None) -> PrerequisiteEvidenceState:
    if observed is None:
        return PrerequisiteEvidenceState.UNKNOWN
    if observed + 1e-9 >= min_level:
        return PrerequisiteEvidenceState.SATISFIED
    return PrerequisiteEvidenceState.UNSATISFIED


def evaluate_resource(
    resource: ResourceSpec,
    proficiency: dict[str, float | None],
) -> Eligibility:
    checks: list[PrerequisiteCheck] = []
    for prereq in resource.prerequisites:
        observed = proficiency.get(prereq.slug)
        state = check_prerequisite(prereq.min_level, observed)
        checks.append(
            PrerequisiteCheck(
                skill_slug=prereq.slug,
                min_level=prereq.min_level,
                state=state,
                observed=observed,
            )
        )
    if any(item.state is PrerequisiteEvidenceState.UNSATISFIED for item in checks):
        status = EligibilityStatus.BLOCKED_BY_KNOWN_GAP
    elif any(item.state is PrerequisiteEvidenceState.UNKNOWN for item in checks):
        status = EligibilityStatus.BLOCKED_BY_UNKNOWN
    else:
        status = EligibilityStatus.ELIGIBLE
    return Eligibility(status=status, checks=tuple(checks))


def recompute_eligibility(
    resource: ResourceSpec,
    proficiency: dict[str, float | None],
) -> Eligibility:
    """Re-evaluate a resource after evidence changes. No assessment scoring."""
    return evaluate_resource(resource, proficiency)
