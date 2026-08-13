"""Shared Slice 2 types. No ranking math here."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import EligibilityStatus, InterventionType, PrerequisiteEvidenceState
from app.ontology.load import ResourceSpec
from app.services.gap_engine.profile import ExplainedGap, GapProfile


@dataclass(frozen=True)
class LearnerPreferences:
    weekly_hours: float
    learning_style: str


@dataclass(frozen=True)
class PrerequisiteCheck:
    skill_slug: str
    min_level: float
    state: PrerequisiteEvidenceState
    observed: float | None


@dataclass(frozen=True)
class Eligibility:
    status: EligibilityStatus
    checks: tuple[PrerequisiteCheck, ...]


@dataclass(frozen=True)
class ScoreBreakdown:
    skill_gap_fit: float
    role_importance: float
    prerequisite_fit: float
    difficulty_fit: float
    duration_fit: float
    learning_style_fit: float
    semantic_similarity: float
    final_score: float

    def as_dict(self) -> dict[str, float]:
        return {
            "skill_gap_fit": self.skill_gap_fit,
            "role_importance": self.role_importance,
            "prerequisite_fit": self.prerequisite_fit,
            "difficulty_fit": self.difficulty_fit,
            "duration_fit": self.duration_fit,
            "learning_style_fit": self.learning_style_fit,
            "semantic_similarity": self.semantic_similarity,
            "final_score": self.final_score,
        }


@dataclass(frozen=True)
class ScoredCandidate:
    resource: ResourceSpec
    primary_skill: str
    eligibility: Eligibility
    intervention: InterventionType
    breakdown: ScoreBreakdown
    explanation: str


@dataclass(frozen=True)
class PlannedItem:
    candidate: ScoredCandidate
    position: int
    week_index: int


@dataclass(frozen=True)
class PlannedPath:
    role_slug: str
    role_name: str
    weekly_hours: float
    learning_style: str
    items: tuple[PlannedItem, ...]
    total_estimated_hours: float


def gap_index(profile: GapProfile) -> dict[str, ExplainedGap]:
    return {item.ranked.gap.skill_slug: item for item in profile.items}


def proficiency_map(profile: GapProfile) -> dict[str, float | None]:
    return {item.ranked.gap.skill_slug: item.ranked.gap.proficiency for item in profile.items}
