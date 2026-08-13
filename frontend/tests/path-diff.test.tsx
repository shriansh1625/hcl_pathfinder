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
    attempt: { adaptation: "CREATED" },
    setView: () => undefined,
  }),
}));

import { PathChanged } from "@/components/path/PathChanged";

describe("V1/V2 adaptation display", () => {
  it("renders backend PathDiff change kinds", () => {
    render(<PathChanged />);
    expect(screen.getByText("Your path changed.")).toBeInTheDocument();
    expect(screen.getByText("ADDED")).toBeInTheDocument();
    expect(screen.getByText("BLOCKED")).toBeInTheDocument();
    expect(screen.getByText("scikit-learn model evaluation")).toBeInTheDocument();
    expect(screen.getByText("Evidence moved model evaluation from UNKNOWN to GAP.")).toBeInTheDocument();
  });

  it("highlights completed work preservation from the active path", () => {
    render(<PathChanged />);
    expect(screen.getByTestId("frozen-work")).toHaveTextContent("Statistics Foundation");
    expect(screen.getByTestId("frozen-work")).toHaveTextContent("COMPLETED");
    expect(screen.getByText("PathFinder never rewrites completed work.")).toBeInTheDocument();
  });
});
