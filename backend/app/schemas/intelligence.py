from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LearnerCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)


class LearnerRead(BaseModel):
    id: UUID
    display_name: str
    is_demo: bool


class EvidenceCreate(BaseModel):
    skill: str = Field(min_length=1, max_length=80)
    source: str
    observed_level: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1, default=0.8)


class EvidenceRead(BaseModel):
    id: UUID
    skill: str
    source: str
    observed_level: float
    reliability: float
    confidence: float
    created_at: datetime


class FusedSkillRead(BaseModel):
    skill: str
    proficiency: float | None
    confidence: float | None
    status: str
    evidence_count: int
    conflict: bool
    conflict_spread: float | None
    dominant_source: str | None
    reason: str


class CompetencyRead(BaseModel):
    skill: str
    name: str
    target_level: float
    importance: float
    required_status: str


class RoleCompetencyRead(BaseModel):
    role: str
    name: str
    competencies: list[CompetencyRead]


class GapItemRead(BaseModel):
    skill: str
    name: str
    target_level: float
    importance: float
    required_status: str
    proficiency: float | None
    confidence: float | None
    gap: float | None
    normalized_gap: float | None
    gap_status: str
    severity: str
    priority: float
    is_blocking: bool
    hard_downstream: list[str]
    soft_downstream: list[str]
    prerequisite_criticality: float
    evidence_count: int
    conflict: bool
    dominant_source: str | None
    explanation: str
    evidence_state: str
    attainment: str
    target_met: bool | None
    gap_priority: float
    verification_priority: float
    action: str
    action_priority: float
    blocked: bool
    blockers: list[str]
    preparation_needed: bool
    preparation_skills: list[str]
    downstream_impact: str


class GapProfileRead(BaseModel):
    role: str
    name: str
    items: list[GapItemRead]


class LearnerPreferencesUpdate(BaseModel):
    weekly_hours: float = Field(gt=0, le=80, default=8)
    learning_style: str = "MIXED"


class PathCreate(BaseModel):
    role: str
    weekly_hours: float = Field(gt=0, le=80, default=8)
    learning_style: str = "MIXED"


class PathItemRead(BaseModel):
    position: int
    week: int | None
    resource: str
    title: str
    type: str
    target_skill: str
    intervention: str
    eligibility: str
    duration_hours: float
    url: str | None
    score_breakdown: dict
    explanation: str
    prerequisites: list[dict]
    causality: dict = Field(default_factory=dict)


class PathRead(BaseModel):
    id: UUID
    role: str
    version: int
    status: str
    weekly_hours: float
    learning_style: str
    total_estimated_hours: float | None
    items: list[PathItemRead]
    quality: dict | None = None


class RecommendationRead(BaseModel):
    resource: str
    title: str
    primary_skill: str
    intervention: str
    eligibility: str
    final_score: float
    score_breakdown: dict
    explanation: str

