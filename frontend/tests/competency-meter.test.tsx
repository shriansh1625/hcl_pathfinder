import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CompetencyRow } from "@/components/ui/CompetencyRow";
import type { GapItem } from "@/lib/types";

const unknown = {
  skill: "model_evaluation",
  name: "Model Evaluation",
  target_level: 0.8,
  importance: 0.9,
  required_status: "CORE",
  proficiency: null,
  confidence: null,
  gap: null,
  normalized_gap: null,
  gap_status: "UNKNOWN",
  severity: "unknown",
  priority: 1,
  is_blocking: false,
  hard_downstream: [],
  soft_downstream: [],
  prerequisite_criticality: 0,
  evidence_count: 0,
  conflict: false,
  dominant_source: null,
  explanation: "",
  evidence_state: "UNKNOWN",
  attainment: "UNKNOWN",
  target_met: null,
  gap_priority: 0,
  verification_priority: 1,
  action: "VERIFY",
  action_priority: 1,
  blocked: false,
  blockers: [],
  preparation_needed: false,
  preparation_skills: [],
  downstream_impact: "HIGH",
} as GapItem;

describe("competency meter", () => {
  it("does not render UNKNOWN as a 0% fill", () => {
    const { container } = render(<CompetencyRow item={unknown} />);
    expect(screen.getByTestId("proficiency-model_evaluation")).toHaveTextContent("—");
    expect(container.querySelector(".meter-unknown")).toBeTruthy();
    expect(container.querySelector(".meter-fill")).toBeNull();
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
    expect(screen.queryByText("0.00")).not.toBeInTheDocument();
  });
});
