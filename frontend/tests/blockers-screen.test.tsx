import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Blockers } from "@/components/overview/Blockers";
import type { GapItem, PathItem } from "@/lib/types";

const gaps: GapItem[] = [
  {
    skill: "docker",
    name: "Docker",
    target_level: 0.7,
    importance: 0.8,
    required_status: "CORE",
    proficiency: null,
    confidence: null,
    gap: null,
    normalized_gap: null,
    gap_status: "UNKNOWN",
    severity: "LOW",
    priority: 0.4,
    is_blocking: true,
    hard_downstream: ["model_deployment"],
    soft_downstream: [],
    prerequisite_criticality: 0.8,
    evidence_count: 0,
    conflict: false,
    dominant_source: null,
    explanation: "Docker evidence is missing.",
    evidence_state: "UNKNOWN",
    attainment: "UNKNOWN",
    target_met: null,
    gap_priority: 0,
    verification_priority: 0.9,
    action: "VERIFY",
    action_priority: 0.9,
    blocked: false,
    blockers: [],
    preparation_needed: false,
    preparation_skills: [],
    downstream_impact: "Blocks deployment resources.",
  },
];

const waiting: PathItem = {
  position: 4,
  week: null,
  status: "WAITING_FOR_VERIFICATION",
  resource: "serve-sklearn-model-lab",
  title: "Serve sklearn model lab",
  type: "RESOURCE",
  target_skill: "model_deployment",
  intervention: "REMEDIATE",
  eligibility: "BLOCKED_BY_UNKNOWN",
  duration_hours: 6,
  url: null,
  score_breakdown: {},
  explanation: "Waiting on docker verification.",
  prerequisites: [{ skill: "docker", min_level: 0.6, state: "UNKNOWN", observed: null }],
  causality: {},
  kind: "WAITING_FOR_VERIFICATION",
  executable: false,
  gate: null,
};

vi.mock("@/lib/session", () => ({
  useIntelligence: () => ({
    gaps,
    activePath: { items: [waiting] },
  }),
}));

describe("blockers screen", () => {
  it("shows resource-level causal blocker cards from backend path items", () => {
    render(<Blockers />);
    expect(screen.getByText("What is blocking your path")).toBeInTheDocument();
    expect(screen.getByText("What is blocked?")).toBeInTheDocument();
    expect(screen.getByText("Serve sklearn model lab")).toBeInTheDocument();
    expect(screen.getByText("Requires Docker")).toBeInTheDocument();
    expect(screen.getByText(/Docker\s+No evidence/)).toBeInTheDocument();
    expect(screen.getByText("VERIFY Docker")).toBeInTheDocument();
    expect(screen.getByText("WAITING FOR VERIFICATION")).toBeInTheDocument();
  });
});
