from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: str
    service: str
    slice: str


class ReadyResponse(BaseModel):
    status: str
    database: str


class SkillRead(ORMModel):
    id: UUID
    slug: str
    canonical_name: str
    description: str
    category: str


class RoleRead(ORMModel):
    id: UUID
    slug: str
    name: str
    description: str


class RoleSkillRead(ORMModel):
    skill_id: UUID
    target_level: float
    importance: float
    required_status: str


class SkillRelationshipRead(ORMModel):
    source_skill_id: UUID
    target_skill_id: UUID
    relationship_type: str
    strength: float
    rationale: str


class ResourceRead(ORMModel):
    id: UUID
    slug: str
    title: str
    type: str
    difficulty: int
    duration_hours: float
    url: str | None
    url_status: str
    learning_modes: list
    is_active: bool


class ScoreBreakdown(BaseModel):
    """Stored on path_items for later explainability. Not computed in Slice 0."""

    skill_gap: float | None = None
    role_importance: float | None = None
    prerequisite_fit: float | None = None
    difficulty_fit: float | None = None
    duration_fit: float | None = None
    style_fit: float | None = None
    semantic_similarity: float | None = None
    final_score: float | None = None


class UserSkillRead(ORMModel):
    skill_id: UUID
    proficiency: float | None
    confidence: float | None
    status: str
    last_updated: datetime


class LearningPathRead(ORMModel):
    id: UUID
    user_id: UUID
    role_id: UUID
    version: int
    status: str
    parent_path_id: UUID | None
    generated_at: datetime
    total_estimated_hours: float | None


class AdaptationEventRead(ORMModel):
    id: UUID
    user_id: UUID
    from_path_id: UUID
    to_path_id: UUID
    event_type: str
    summary: str
    created_at: datetime


class OntologyStats(BaseModel):
    skills: int
    roles: int
    skill_relationships: int
    hard_prerequisites: int
    soft_prerequisites: int
    related: int
    resources: int
    assessments: int
    questions: int
