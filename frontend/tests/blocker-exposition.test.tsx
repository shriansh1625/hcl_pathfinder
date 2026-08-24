import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BlockerChain } from "@/components/ui/BlockerChain";
import { PathView, WhyDrawer } from "@/components/path/PathView";
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
  {
    skill: "python",
    name: "Python",
    target_level: 0.85,
    importance: 0.95,
    required_status: "CORE",
    proficiency: 0.3,
    confidence: 0.8,
    gap: 0.55,
    normalized_gap: 0.55,
    gap_status: "GAP",
    severity: "HIGH",
    priority: 0.9,
    is_blocking: true,
    hard_downstream: ["ml_fundamentals"],
    soft_downstream: [],
    prerequisite_criticality: 0.95,
    evidence_count: 1,
    conflict: false,
    dominant_source: "ASSESSMENT",
    explanation: "Python is below target.",
    evidence_state: "KNOWN",
    attainment: "GAP",
    target_met: false,
    gap_priority: 0.8,
    verification_priority: 0,
    action: "REMEDIATE",
    action_priority: 0.95,
    blocked: false,
    blockers: [],
    preparation_needed: false,
    preparation_skills: [],
    downstream_impact: "Blocks ML fundamentals.",
  },
];

const unknownWait: PathItem = {
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

const knownGapWait: PathItem = {
  ...unknownWait,
  position: 5,
  title: "Intro ML course",
  target_skill: "ml_fundamentals",
  eligibility: "BLOCKED_BY_KNOWN_GAP",
  kind: "WAITING_FOR_REMEDIATION",
  prerequisites: [{ skill: "python", min_level: 0.7, state: "UNSATISFIED", observed: 0.3 }],
};

vi.mock("@/lib/session", () => ({
  useIntelligence: () => ({
    activePath: {
      version: 1,
      status: "ACTIVE",
      total_estimated_hours: 38,
      items: [unknownWait, knownGapWait],
    },
    roleName: "AI/ML Engineer",
    gaps,
  }),
}));

describe("blocked resource exposition", () => {
  it("surfaces WAITING FOR VERIFICATION with docker UNKNOWN", () => {
    render(<PathView />);
    expect(screen.getAllByText("WAITING FOR VERIFICATION").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Docker").length).toBeGreaterThan(0);
    expect(screen.getAllByText("UNKNOWN").length).toBeGreaterThan(0);
    expect(screen.getByText("Evidence required before this resource can start.")).toBeInTheDocument();
  });

  it("surfaces WAITING FOR REMEDIATION with observed/target line", () => {
    render(<PathView />);
    expect(screen.getByText("WAITING FOR REMEDIATION")).toBeInTheDocument();
    expect(screen.getByText("0.30 / 0.85 target")).toBeInTheDocument();
    expect(screen.getByText("Prerequisite below target.")).toBeInTheDocument();
  });

  it("renders blocker chain diagnostic in drawer", () => {
    render(<WhyDrawer item={unknownWait} onClose={() => undefined} />);
    expect(screen.getByTestId("blocker-chain")).toBeInTheDocument();
    expect(screen.getByText("serve-sklearn-model-lab")).toBeInTheDocument();
    expect(screen.getByText("→ VERIFY")).toBeInTheDocument();
  });

  it("maps chain fields without inventing values", () => {
    render(<BlockerChain item={unknownWait} gaps={gaps} />);
    expect(screen.getByText("Docker")).toBeInTheDocument();
    expect(screen.getByText("UNKNOWN")).toBeInTheDocument();
  });
});
