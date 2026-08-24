import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/session", () => ({
  useIntelligence: () => ({
    previousPath: {
      version: 1,
      items: [
        { position: 0, target_skill: "statistics", title: "Statistics Foundation", executable: true },
      ],
    },
    activePath: {
      version: 2,
      items: [
        {
          position: 0,
          week: 1,
          title: "Statistics Foundation",
          status: "COMPLETED",
        },
      ],
    },
    diff: {
      changed_skills: ["model_evaluation"],
      added: [
        {
          key: "resource:sklearn-eval",
          skill: "model_evaluation",
          title: "scikit-learn model evaluation",
          reason: "Evidence moved model evaluation from UNKNOWN to GAP.",
        },
      ],
      removed: [],
      moved: [],
      unchanged: [],
      blocked: [
        {
          key: "resource:deploy",
          skill: "model_deployment",
          title: "Model deployment",
          reason: "Waiting: prerequisite evidence or remediation is still required.",
        },
      ],
    },
    attempt: { adaptation: "CREATED", skill_results: [{ skill: "model_evaluation", observed_level: 0 }] },
    beforeGaps: [{ skill: "model_evaluation", evidence_state: "UNKNOWN", attainment: "UNKNOWN", proficiency: null, target_level: 0.8, action: "VERIFY", blocked: false, name: "Model Evaluation" }],
    gaps: [{ skill: "model_evaluation", attainment: "GAP", target_level: 0.8, action: "REMEDIATE", downstream_impact: "Blocks deployment.", explanation: "Gap", evidence_state: "KNOWN", proficiency: 0, blocked: false, name: "Model Evaluation", importance: 0.9, required_status: "CORE", confidence: 0.7, gap: 0.8, normalized_gap: 0.8, gap_status: "GAP", severity: "HIGH", priority: 0.9, is_blocking: true, hard_downstream: [], soft_downstream: [], prerequisite_criticality: 0.8, evidence_count: 1, conflict: false, dominant_source: "ASSESSMENT", gap_priority: 0.8, verification_priority: 0, action_priority: 0.9, blockers: [], preparation_needed: false, preparation_skills: [], target_met: false }],
    setView: () => undefined,
  }),
}));

import { PathChanged } from "@/components/path/PathChanged";

describe("V1/V2 adaptation display", () => {
  it("renders backend PathDiff change kinds", () => {
    render(<PathChanged />);
    expect(screen.getByText("PATH CHANGED")).toBeInTheDocument();
    expect(screen.getByText("ADDED")).toBeInTheDocument();
    expect(screen.getByText("BLOCKED")).toBeInTheDocument();
    expect(screen.getByText("scikit-learn model evaluation")).toBeInTheDocument();
    expect(screen.getByText("Evidence moved model evaluation from UNKNOWN to GAP.")).toBeInTheDocument();
  });

  it("highlights completed work preservation from the active path", () => {
    render(<PathChanged />);
    expect(screen.getByTestId("frozen-work")).toHaveTextContent("Statistics Foundation");
    expect(screen.getByTestId("frozen-work")).toHaveTextContent("COMPLETED");
    expect(screen.getByText("Completed work preserved")).toBeInTheDocument();
  });
});
