import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AskPathFinder } from "@/components/ai/AskPathFinder";
import { GroundedExplain } from "@/components/ai/GroundedExplain";
import { Overview } from "@/components/overview/Overview";
import { WhyDrawer } from "@/components/path/PathView";
import { WhyChanged } from "@/components/assess/WhyChanged";
import type { GapItem, PathItem } from "@/lib/types";

const explain = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    explain: (...args: unknown[]) => explain(...args),
    evidence: async () => [],
  },
}));

const gap = {
  skill: "statistics",
  name: "Statistics",
  target_level: 0.8,
  importance: 0.9,
  required_status: "CORE",
  proficiency: 0.35,
  confidence: 0.8,
  gap: 0.45,
  normalized_gap: 0.56,
  gap_status: "GAP",
  severity: "HIGH",
  priority: 0.9,
  is_blocking: true,
  hard_downstream: ["ml_fundamentals"],
  soft_downstream: [],
  prerequisite_criticality: 0.8,
  evidence_count: 1,
  conflict: false,
  dominant_source: "ASSESSMENT",
  explanation: "Below target",
  evidence_state: "KNOWN",
  attainment: "GAP",
  target_met: false,
  gap_priority: 0.9,
  verification_priority: 0,
  action: "REMEDIATE",
  action_priority: 0.9,
  blocked: false,
  blockers: [],
  preparation_needed: false,
  preparation_skills: [],
  downstream_impact: "Supports ML fundamentals",
} as GapItem;

const session = {
  learnerId: "learner-1",
  roleName: "AI/ML Engineer",
  weeklyHours: 8,
  learningStyle: "MIXED",
  loading: false,
  beforeGaps: [],
  skills: [],
  gaps: [gap],
  attempt: {
    skill_results: [{ skill: "model_evaluation", observed_level: 0 }],
    adaptation: "CREATED",
  },
    diff: { added: [], removed: [], moved: [], unchanged: [], blocked: [], changed_skills: ["model_evaluation"] },
    activePath: { version: 2, items: [{ position: 0, title: "Statistics Foundation", status: "COMPLETED", week: 1 }] },
    timeline: [
      { path_id: "p1", version: 1, status: "SUPERSEDED", parent_path_id: null, created_at: "2026-08-13T10:00:00Z" },
      { path_id: "p2", version: 2, status: "ACTIVE", parent_path_id: "p1", created_at: "2026-08-13T10:05:00Z" },
    ],
  beforeGapsForWhy: [
    { skill: "model_evaluation", evidence_state: "UNKNOWN", attainment: "UNKNOWN", proficiency: null, target_level: 0.8, action: "VERIFY", blocked: false, name: "Model Evaluation" },
  ],
};

vi.mock("@/lib/session", () => ({
  useIntelligence: () => ({
    ...session,
    beforeGaps: [
      {
        skill: "model_evaluation",
        evidence_state: "UNKNOWN",
        attainment: "UNKNOWN",
        proficiency: null,
        target_level: 0.8,
        action: "VERIFY",
        blocked: false,
        name: "Model Evaluation",
      },
    ],
    gaps: [
      gap,
      {
        ...gap,
        skill: "model_evaluation",
        name: "Model Evaluation",
        proficiency: 0,
        attainment: "GAP",
        evidence_state: "KNOWN",
        action: "REMEDIATE",
      },
    ],
  }),
}));

const grounded = {
  answer: "Your statistics evidence is 0.35 versus a 0.80 target for AI/ML Engineer.",
  claims: [{ text: "below target", fact_ids: ["skill.proficiency", "skill.target"] }],
  confidence: "grounded",
  source: "deterministic",
  facts: [
    { id: "skill.proficiency", label: "Statistics proficiency", value: "0.35" },
    { id: "skill.target", label: "Statistics target", value: "0.80" },
    { id: "skill.downstream", label: "Downstream HARD dependencies", value: "ml_fundamentals" },
  ],
  intent: "WHY_GAP",
};

const item: PathItem = {
  position: 0,
  week: 1,
  status: "PENDING",
  resource: "khan-statistics-probability",
  title: "Khan Academy Statistics and Probability",
  type: "RESOURCE",
  target_skill: "statistics",
  intervention: "FOUNDATION",
  eligibility: "ELIGIBLE",
  duration_hours: 18,
  url: "https://example.com",
  score_breakdown: {},
  explanation: "Statistics is a diagnosed gap.",
  prerequisites: [{ skill: "python", min_level: 0.5, state: "SATISFIED", observed: 0.9 }],
  causality: {
    why_selected: "Statistics is a diagnosed gap for AI/ML Engineer.",
    why_this_skill: "Evidence places statistics below the role target.",
    why_this_position: "Foundation work belongs in week 1.",
    why_this_intervention: "Intervention is FOUNDATION.",
    why_this_resource: "Khan Academy covers the diagnosed statistics gap.",
    why_not_earlier: "Nothing precedes the first executable week.",
  },
  kind: "EXECUTABLE",
  executable: true,
  gate: null,
};

beforeEach(() => {
  explain.mockReset();
  explain.mockResolvedValue(grounded);
});

describe("contextual grounded explanations", () => {
  it("opens Why this gap from competency and shows GROUNDED IN facts", async () => {
    render(<Overview />);
    fireEvent.click(screen.getByTestId("why-gap-statistics").querySelector("button") as HTMLButtonElement);
    expect(await screen.findByText(/0.35 versus a 0.80 target/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Why?" }));
    expect(screen.getByTestId("grounded-in")).toHaveTextContent("0.35");
    expect(screen.getByTestId("grounded-in")).toHaveTextContent("ml_fundamentals");
    expect(explain).toHaveBeenCalledWith("learner-1", { intent: "WHY_GAP", skill: "statistics" });
    expect(screen.queryByText(/AI failed/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Chat with AI/i)).not.toBeInTheDocument();
  });

  it("opens Why this resource from the path drawer", async () => {
    render(<WhyDrawer item={item} onClose={() => undefined} />);
    fireEvent.click(screen.getByRole("button", { name: "Why this resource?" }));
    await waitFor(() => expect(explain).toHaveBeenCalled());
    expect(explain).toHaveBeenCalledWith(
      "learner-1",
      expect.objectContaining({ intent: "WHY_RESOURCE", resource: "khan-statistics-probability" }),
    );
    expect(await screen.findByText(/0.35 versus a 0.80 target/i)).toBeInTheDocument();
  });

  it("opens What changed from the causality view", async () => {
    render(<WhyChanged />);
    fireEvent.click(screen.getByRole("button", { name: "What changed?" }));
    await waitFor(() =>
      expect(explain).toHaveBeenCalledWith(
        "learner-1",
        expect.objectContaining({ intent: "WHAT_CHANGED", skill: "model_evaluation" }),
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "What should I do next?" }));
    await waitFor(() =>
      expect(explain).toHaveBeenCalledWith("learner-1", expect.objectContaining({ intent: "NEXT_ACTION" })),
    );
  });

  it("answers Ask PathFinder from verified state, not a chatbot transcript", async () => {
    render(<AskPathFinder />);
    expect(screen.getByText(/Asking about your path/i)).toBeInTheDocument();
    expect(screen.queryByText(/Chat with AI/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Why am I learning statistics?" }));
    await waitFor(() =>
      expect(explain).toHaveBeenCalledWith(
        "learner-1",
        expect.objectContaining({ intent: "QUERY", query: "Why am I learning statistics?" }),
      ),
    );
    expect(await screen.findByText(/0.35 versus a 0.80 target/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Why?" }));
    expect(screen.getByTestId("ask-grounded-in")).toHaveTextContent("Statistics proficiency");
  });

  it("shows deterministic copy when the explanation request fails", async () => {
    explain.mockRejectedValueOnce(new Error("network"));
    render(<GroundedExplain intent="WHY_GAP" skill="statistics" triggerLabel="Why this gap?" testId="fail-gap" />);
    fireEvent.click(screen.getByRole("button", { name: "Why this gap?" }));
    expect(await screen.findByText(/Explanation is unavailable/i)).toBeInTheDocument();
    expect(screen.queryByText(/AI failed/i)).not.toBeInTheDocument();
  });
});
