from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LearnerCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    experience_level: str | None = Field(default=None, max_length=40)
    weekly_hours: float | None = Field(default=None, gt=0, le=80)
    learning_style: str | None = Field(default=None, max_length=40)
    timeline_weeks: int | None = Field(default=None, gt=0, le=520)
    interests: list[str] | None = None
    goal_text: str | None = Field(default=None, max_length=2000)
    target_role: str | None = Field(default=None, max_length=80)


class LearnerRead(BaseModel):
    id: UUID
    display_name: str
    is_demo: bool
    experience_level: str | None = None
    weekly_hours: float | None = None
    learning_style: str | None = None
    timeline_weeks: int | None = None
    interests: list[str] | None = None
    goal_text: str | None = None
    target_role: str | None = None


class GoalIntakeCreate(BaseModel):
    goal: str = Field(min_length=3, max_length=2000)


class ResolvedEntityRead(BaseModel):
    slug: str
    name: str
    mention: str
    how: str


class SkillClaimRead(BaseModel):
    skill: str
    name: str
    observed_level: float
    mention: str
    level_phrase: str
    how: str


class GoalIntakeRead(BaseModel):
    goal_text: str
    role: ResolvedEntityRead | None
    role_alternatives: list[ResolvedEntityRead]
    skills: list[SkillClaimRead]
    ungraded: list[SkillClaimRead]
    weekly_hours: float | None
    timeframe_weeks: int | None
    learning_style: str | None
    unresolved: list[str]
    source: str
    provider: str
    model: str


class DemoEvidenceRead(BaseModel):
    skill: str
    observed_level: float
    source: str = "ASSESSMENT"
    confidence: float = 0.85


class RoleDetailRead(BaseModel):
    slug: str
    name: str
    description: str
    competency_count: int
    core_skills: list[str]
    focus_areas: list[str]


class MilestoneRead(BaseModel):
    id: str
    label: str
    category: str
    status: str
    completed_items: int
    total_items: int
    skills: list[str]


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
    status: str = "PENDING"
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
    kind: str = "EXECUTABLE"
    executable: bool = True
    gate: dict | None = None


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


class AssessmentAttemptCreate(BaseModel):
    answers: list[int]
    attempt_id: UUID | None = None


class SkillResultRead(BaseModel):
    skill: str
    question_count: int
    correct_count: int
    observed_level: float
    confidence: float
    difficulty_avg: float
    consistency: str


class AssessmentAttemptRead(BaseModel):
    attempt_id: UUID
    attempt_number: int
    assessment: str
    overall_score: float
    passed: bool
    skill_results: list[SkillResultRead]
    adaptation: str
    path_id: UUID | None
    diff: dict | None


class CompleteItemCreate(BaseModel):
    position: int


class PathItemCompleteRead(BaseModel):
    path_id: UUID
    position: int
    status: str
    item_type: str


class PathDiffRead(BaseModel):
    path_id: UUID
    from_path_id: UUID | None
    trigger_type: str | None
    changed_skills: list[str]
    added: list[dict]
    removed: list[dict]
    moved: list[dict]
    unchanged: list[dict]
    blocked: list[dict]


class SuggestedAssessmentRead(BaseModel):
    assessment: str | None
    title: str | None
    question_count: int | None
    covers: list[str]
    reason: str


class PathTimelineEntry(BaseModel):
    path_id: UUID
    version: int
    status: str
    parent_path_id: UUID | None
    created_at: datetime


class AssessmentQuestionPublic(BaseModel):
    index: int
    prompt: str
    skill: str
    difficulty: int
    choices: list[str]


class AssessmentPublicRead(BaseModel):
    slug: str
    title: str
    description: str
    primary_skill: str
    question_count: int
    questions: list[AssessmentQuestionPublic]


class AIExplainRequest(BaseModel):
    intent: str = Field(default="QUERY")
    skill: str | None = None
    resource: str | None = None
    query: str | None = Field(default=None, max_length=500)


class AIClaimRead(BaseModel):
    text: str
    fact_ids: list[str]


class AIFactRead(BaseModel):
    id: str
    label: str
    value: str


class AIExplainRead(BaseModel):
    answer: str
    claims: list[AIClaimRead]
    confidence: str
    source: str
    facts: list[AIFactRead]
    intent: str


class ProgressFeedbackCreate(BaseModel):
    """How a path step actually went.

    `self_reported_level` is optional and supplied by the learner. Without it,
    no evidence is recorded and the path item status still updates.
    """

    path_id: UUID
    position: int = Field(ge=0)
    outcome: str = Field(pattern="^(COMPLETED|STRUGGLED|SKIPPED)$")
    self_reported_level: float | None = Field(default=None, ge=0, le=1)


class ProgressFeedbackRead(BaseModel):
    path_id: UUID
    position: int
    outcome: str
    item_status: str
    target_skill: str
    evidence_recorded: bool
    observed_level: float | None
    adaptation: str
    new_path_id: UUID | None
    diff: dict | None
    summary: str


class DashboardRead(BaseModel):
    role: str
    role_name: str
    goal_text: str | None
    experience_level: str | None
    weekly_hours: float | None
    learning_style: str | None
    interests: list[str] | None
    path_version: int | None
    path_status: str | None
    overall_progress: dict
    competency_snapshot: list[dict]
    top_gaps: list[GapItemRead]
    blockers: list[GapItemRead]
    current_milestone: MilestoneRead | None
    this_week: list[dict]
    next_action: dict | None
    recent_evidence: list[dict]
    recent_adaptation: dict | None
    upcoming_assessment: SuggestedAssessmentRead | None
    milestones: list[MilestoneRead]
    why_this_matters: str | None

