export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `Request failed (${status})`);
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
    let detail: unknown = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? body;
    } catch {
      detail = await response.text();
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
  createLearner: (display_name: string) =>
    request<import("./types").Learner>("/v1/learners", {
      method: "POST",
      body: JSON.stringify({ display_name }),
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
};
