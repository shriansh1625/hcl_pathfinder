"""Deterministic recommendation explanations. No LLM."""

from __future__ import annotations

from app.core.enums import EligibilityStatus, PrerequisiteEvidenceState
from app.ontology.load import ResourceSpec
from app.services.recommendation.models import Eligibility, LearnerPreferences, ScoreBreakdown


def explain_recommendation(
    resource: ResourceSpec,
    breakdown: ScoreBreakdown,
    eligibility: Eligibility,
    prefs: LearnerPreferences,
    primary_skill: str,
    role_name: str,
) -> str:
    reasons: list[str] = [
        f"{resource.title} addresses {primary_skill.replace('_', ' ')} "
        f"(coverage fit {breakdown.skill_gap_fit:.0%}) for the {role_name} role."
    ]
    if breakdown.role_importance >= 0.5:
        reasons.append(f"Role importance for covered skills is {breakdown.role_importance:.0%}.")
    if breakdown.learning_style_fit >= 0.8:
        reasons.append(f"It matches a {prefs.learning_style.lower()} preference.")
    reasons.append(
        f"Duration {resource.duration_hours:g}h vs a {prefs.weekly_hours:g}h weekly budget "
        f"(fit {breakdown.duration_fit:.0%})."
    )
    unknown = [c.skill_slug for c in eligibility.checks if c.state is PrerequisiteEvidenceState.UNKNOWN]
    missing = [
        c.skill_slug for c in eligibility.checks if c.state is PrerequisiteEvidenceState.UNSATISFIED
    ]
    if eligibility.status is EligibilityStatus.BLOCKED_BY_KNOWN_GAP:
        reasons.append(
            "It is not immediately safe: the learner is below a required prerequisite "
            f"({', '.join(missing)}). Sequence it after remediating that gap."
        )
    elif eligibility.status is EligibilityStatus.BLOCKED_BY_UNKNOWN:
        reasons.append(
            "A required prerequisite is UNKNOWN, not failed "
            f"({', '.join(unknown)}). Do not treat it as mastered."
        )
    else:
        reasons.append("Resource prerequisites are currently satisfied or none are required.")
    return " ".join(reasons)
