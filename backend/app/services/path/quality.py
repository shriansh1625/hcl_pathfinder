"""Categorical path-quality checks. Not a presentation score."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import AttainmentStatus, EligibilityStatus
from app.ontology.load import ResourceSpec
from app.services.gap_engine.profile import GapProfile
from app.services.recommendation.causality import is_known_focal
from app.services.recommendation.models import PlannedItem, gap_index
from app.services.skill_graph.dependency import SkillEdge


@dataclass(frozen=True)
class PathQualityReport:
    PREREQUISITES_VALID: bool
    ROLE_RELEVANCE_VALID: bool
    GAP_COVERAGE_VALID: bool
    TIME_BUDGET_VALID: bool
    RESOURCE_VALID: bool
    SEQUENCE_VALID: bool
    EXPLANATION_GROUNDED: bool
    findings: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "PREREQUISITES_VALID": self.PREREQUISITES_VALID,
            "ROLE_RELEVANCE_VALID": self.ROLE_RELEVANCE_VALID,
            "GAP_COVERAGE_VALID": self.GAP_COVERAGE_VALID,
            "TIME_BUDGET_VALID": self.TIME_BUDGET_VALID,
            "RESOURCE_VALID": self.RESOURCE_VALID,
            "SEQUENCE_VALID": self.SEQUENCE_VALID,
            "EXPLANATION_GROUNDED": self.EXPLANATION_GROUNDED,
            "findings": list(self.findings),
        }


def validate_path(
    items: list[PlannedItem],
    profile: GapProfile,
    catalog: list[ResourceSpec],
    edges: list[SkillEdge],
    *,
    weekly_hours: float,
) -> PathQualityReport:
    _ = edges
    catalog_slugs = {item.slug for item in catalog}
    index = gap_index(profile)
    findings: list[str] = []

    prereq_ok = True
    role_ok = True
    resource_ok = True
    sequence_ok = True
    grounded = True
    seen_positions: set[int] = set()

    for item in items:
        slug = item.candidate.resource.slug
        if slug not in catalog_slugs:
            resource_ok = False
            findings.append(f"non_catalog_resource:{slug}")
        if item.candidate.breakdown.role_importance <= 0:
            role_ok = False
            findings.append(f"zero_role_relevance:{slug}")
        if item.position in seen_positions:
            sequence_ok = False
            findings.append(f"duplicate_position:{item.position}")
        seen_positions.add(item.position)
        if item.candidate.eligibility.status is EligibilityStatus.ELIGIBLE:
            unknown = [
                check.skill_slug
                for check in item.candidate.eligibility.checks
                if check.state.value == "UNKNOWN"
            ]
            if unknown:
                prereq_ok = False
                findings.append(f"unknown_treated_as_safe:{slug}")
        if item.candidate.eligibility.status is EligibilityStatus.BLOCKED_BY_UNKNOWN:
            text = (item.cause.why_not_earlier if item.cause else "") + item.candidate.explanation
            if "UNKNOWN" not in text:
                grounded = False
                findings.append(f"unknown_unexplained:{slug}")
        gap = index.get(item.candidate.primary_skill)
        if gap is not None and gap.ranked.gap.attainment is AttainmentStatus.TARGET_MET:
            findings.append(f"target_met_consumes_budget:{slug}")
        if item.cause is None:
            grounded = False
            findings.append(f"missing_cause:{slug}")
        else:
            if "scored highly" in item.cause.why_selected.lower():
                grounded = False
                findings.append(f"score_only_reason:{slug}")

    types = [item.candidate.resource.type for item in items]
    if len(items) >= 4 and len(set(types)) == 1 and types[0] == "course":
        findings.append("uniform_course_sequence")

    hours = sum(item.candidate.resource.duration_hours for item in items)
    time_ok = weekly_hours <= 0 or hours <= weekly_hours * 12 + 1e-9
    if not time_ok:
        findings.append("budget_horizon_exceeded")

    focal = [item for item in profile.items if is_known_focal(item)]
    covered_focal = set()
    for item in items:
        for skill in item.candidate.resource.skills:
            if skill.coverage_strength >= 0.35:
                covered_focal.add(skill.slug)
    gap_ok = True
    if focal and not any(row.ranked.gap.skill_slug in covered_focal for row in focal):
        gap_ok = False
        findings.append("no_focal_gap_covered")

    return PathQualityReport(
        PREREQUISITES_VALID=prereq_ok,
        ROLE_RELEVANCE_VALID=role_ok,
        GAP_COVERAGE_VALID=gap_ok,
        TIME_BUDGET_VALID=time_ok,
        RESOURCE_VALID=resource_ok,
        SEQUENCE_VALID=sequence_ok,
        EXPLANATION_GROUNDED=grounded,
        findings=tuple(findings),
    )
