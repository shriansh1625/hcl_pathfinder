type ValidationIssue = { msg?: string; type?: string; loc?: unknown[] };

function formatApiError(status: number, detail: unknown): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const first = detail[0] as ValidationIssue | undefined;
    if (first?.type === "string_too_short") {
      return "Please enter a longer goal (at least 3 characters).";
    }
    if (first?.type === "json_invalid") {
      return "The request could not be read. Refresh and try again.";
    }
    if (first?.msg) return first.msg;
  }
  return `Request failed (${status})`;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(formatApiError(status, detail));
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const text = await response.text();
    let detail: unknown = text || response.statusText;
    if (text) {
      try {
        const body = JSON.parse(text) as { detail?: unknown };
        detail = body.detail ?? body;
      } catch {
        /* keep raw text */
      }
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  roles: () => request<import("./types").Role[]>("/v1/roles"),
  roleDetail: (slug: string) => request<import("./types").RoleDetail>(`/v1/roles/${slug}/detail`),
  roleCompetencies: (slug: string) =>
    request<import("./types").RoleCompetencyProfile>(`/v1/roles/${slug}/competencies`),
  demoEvidence: (slug: string) =>
    request<import("./types").DemoEvidence[]>(`/v1/roles/${slug}/demo-evidence`),
  interpretGoal: (goal: string) =>
    request<import("./types").GoalIntake>("/v1/intake/goal", {
      method: "POST",
      body: JSON.stringify({ goal }),
    }),
  createLearner: (payload: {
    display_name: string;
    experience_level?: string;
    weekly_hours?: number;
    learning_style?: string;
    timeline_weeks?: number;
    interests?: string[];
    goal_text?: string;
    target_role?: string;
  }) =>
    request<import("./types").Learner>("/v1/learners", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  addEvidence: (
    learnerId: string,
    payload: { skill: string; source: string; observed_level: number; confidence: number },
  ) =>
    request(`/v1/learners/${learnerId}/evidence`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  gaps: (learnerId: string, role: string) =>
    request<import("./types").GapProfile>(`/v1/learners/${learnerId}/roles/${role}/gaps`),
  dashboard: (learnerId: string, role: string) =>
    request<import("./types").Dashboard>(`/v1/learners/${learnerId}/roles/${role}/dashboard`),
  skills: (learnerId: string) =>
    request<import("./types").FusedSkill[]>(`/v1/learners/${learnerId}/skills`),
  evidence: (learnerId: string, skill: string) =>
    request<import("./types").EvidenceRow[]>(
      `/v1/learners/${learnerId}/evidence?skill=${encodeURIComponent(skill)}`,
    ),
  createPath: (
    learnerId: string,
    payload: { role: string; weekly_hours: number; learning_style: string },
  ) =>
    request<import("./types").PathRead>(`/v1/learners/${learnerId}/paths`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  paths: (learnerId: string) =>
    request<import("./types").PathRead[]>(`/v1/learners/${learnerId}/paths`),
  path: (learnerId: string, pathId: string) =>
    request<import("./types").PathRead>(`/v1/learners/${learnerId}/paths/${pathId}`),
  timeline: (learnerId: string, role: string) =>
    request<import("./types").TimelineEntry[]>(
      `/v1/learners/${learnerId}/roles/${role}/path-timeline`,
    ),
  suggested: (learnerId: string, role: string) =>
    request<import("./types").SuggestedAssessment>(
      `/v1/learners/${learnerId}/roles/${role}/assessments/suggested`,
    ),
  assessment: (slug: string) =>
    request<import("./types").AssessmentPublic>(`/v1/assessments/${slug}`),
  submitAttempt: (learnerId: string, slug: string, answers: number[]) =>
    request<import("./types").AssessmentAttempt>(
      `/v1/learners/${learnerId}/assessments/${slug}/attempts`,
      { method: "POST", body: JSON.stringify({ answers }) },
    ),
  pathDiff: (learnerId: string, pathId: string) =>
    request<import("./types").PathDiff>(`/v1/learners/${learnerId}/paths/${pathId}/diff`),
  completeItem: (learnerId: string, pathId: string, position: number) =>
    request(`/v1/learners/${learnerId}/paths/${pathId}/complete-item`, {
      method: "POST",
      body: JSON.stringify({ position }),
    }),
  explain: (
    learnerId: string,
    payload: {
      intent: import("./types").AIExplainIntent;
      skill?: string;
      resource?: string;
      query?: string;
    },
  ) =>
    request<import("./types").AIExplain>(`/v1/learners/${learnerId}/ai/explain`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  progress: (
    learnerId: string,
    payload: {
      path_id: string;
      position: number;
      outcome: import("./types").ProgressOutcome;
      self_reported_level?: number;
    },
  ) =>
    request<import("./types").ProgressFeedback>(`/v1/learners/${learnerId}/progress`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
