export type Role = {
  id: string;
  slug: string;
  name: string;
  description: string;
};

export type Learner = {
  id: string;
  display_name: string;
  is_demo: boolean;
};

export type GapItem = {
  skill: string;
  name: string;
  target_level: number;
  importance: number;
  required_status: string;
  proficiency: number | null;
  confidence: number | null;
  gap: number | null;
  normalized_gap: number | null;
  gap_status: string;
  severity: string;
  priority: number;
  is_blocking: boolean;
  hard_downstream: string[];
  soft_downstream: string[];
  prerequisite_criticality: number;
  evidence_count: number;
  conflict: boolean;
  dominant_source: string | null;
  explanation: string;
  evidence_state: string;
  attainment: string;
  target_met: boolean | null;
  gap_priority: number;
  verification_priority: number;
  action: string;
  action_priority: number;
  blocked: boolean;
  blockers: string[];
  preparation_needed: boolean;
  preparation_skills: string[];
  downstream_impact: string;
};

export type GapProfile = {
  role: string;
  name: string;
  items: GapItem[];
};

export type PrerequisiteRow = {
  skill: string;
  min_level: number;
  state: string;
  observed: number | null;
};

export type PathItem = {
  position: number;
  week: number | null;
  status: string;
  resource: string;
  title: string;
  type: string;
  target_skill: string;
  intervention: string;
  eligibility: string;
  duration_hours: number;
  url: string | null;
  score_breakdown: Record<string, unknown>;
  explanation: string;
  prerequisites: PrerequisiteRow[];
  causality: Record<string, string>;
  kind: string;
  executable: boolean;
  gate: Record<string, unknown> | null;
};

export type PathRead = {
  id: string;
  role: string;
  version: number;
  status: string;
  weekly_hours: number;
  learning_style: string;
  total_estimated_hours: number | null;
  items: PathItem[];
  quality: Record<string, unknown> | null;
};

export type DiffEntry = {
  key: string;
  skill: string;
  title: string;
  reason: string;
  from_week?: number | null;
  to_week?: number | null;
};

export type PathDiff = {
  path_id?: string;
  from_path_id?: string | null;
  trigger_type?: string | null;
  changed_skills: string[];
  added: DiffEntry[];
  removed: DiffEntry[];
  moved: DiffEntry[];
  unchanged: DiffEntry[];
  blocked: DiffEntry[];
};

export type TimelineEntry = {
  path_id: string;
  version: number;
  status: string;
  parent_path_id: string | null;
  created_at: string;
};

export type SuggestedAssessment = {
  assessment: string | null;
  title: string | null;
  question_count: number | null;
  covers: string[];
  reason: string;
};

export type AssessmentQuestion = {
  index: number;
  prompt: string;
  skill: string;
  difficulty: number;
  choices: string[];
};

export type AssessmentPublic = {
  slug: string;
  title: string;
  description: string;
  primary_skill: string;
  question_count: number;
  questions: AssessmentQuestion[];
};

export type SkillResult = {
  skill: string;
  question_count: number;
  correct_count: number;
  observed_level: number;
  confidence: number;
  difficulty_avg: number;
  consistency: string;
};

export type AssessmentAttempt = {
  attempt_id: string;
  attempt_number: number;
  assessment: string;
  overall_score: number;
  passed: boolean;
  skill_results: SkillResult[];
  adaptation: string;
  path_id: string | null;
  diff: PathDiff | null;
};

export type GapSnapshot = {
  skill: string;
  name: string;
  evidence_state: string;
  attainment: string;
  proficiency: number | null;
  target_level: number;
  action: string;
  blocked: boolean;
};

export type FusedSkill = {
  skill: string;
  proficiency: number | null;
  confidence: number | null;
  status: string;
  evidence_count: number;
  conflict: boolean;
  conflict_spread: number | null;
  dominant_source: string | null;
  reason: string;
};

export type EvidenceRow = {
  id: string;
  skill: string;
  source: string;
  observed_level: number;
  reliability: number;
  confidence: number;
  created_at: string;
};

export type AIExplainIntent =
  | "WHY_GAP"
  | "WHY_RESOURCE"
  | "WHAT_CHANGED"
  | "NEXT_ACTION"
  | "COACH"
  | "QUERY";

export type AIFact = {
  id: string;
  label: string;
  value: string;
};

export type AIClaim = {
  text: string;
  fact_ids: string[];
};

export type AIExplain = {
  answer: string;
  claims: AIClaim[];
  confidence: string;
  source: "llm" | "deterministic";
  facts: AIFact[];
  intent: string;
};

export type ProgressOutcome = "COMPLETED" | "STRUGGLED" | "SKIPPED";

export type ProgressFeedback = {
  path_id: string;
  position: number;
  outcome: ProgressOutcome;
  item_status: string;
  target_skill: string;
  evidence_recorded: boolean;
  observed_level: number | null;
  adaptation: "CREATED" | "NO_ADAPTATION_REQUIRED" | "NO_ACTIVE_PATH";
  new_path_id: string | null;
  diff: PathDiff | null;
  summary: string;
};

export type ViewId =
  | "overview"
  | "blockers"
  | "path"
  | "prove"
  | "assess"
  | "result"
  | "changed"
  | "why"
  | "history"
  | "map";
