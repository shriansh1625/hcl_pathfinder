import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AdaptationTrace, buildAdaptationTrace } from "@/components/ui/AdaptationTrace";

describe("causal adaptation trace", () => {
  it("builds trace only from backend fields", () => {
    const steps = buildAdaptationTrace({
      attempt: {
        attempt_id: "a",
        attempt_number: 1,
        assessment: "model-evaluation-gate",
        overall_score: 0,
        passed: false,
        skill_results: [
          {
            skill: "model_evaluation",
            question_count: 3,
            correct_count: 0,
            observed_level: 0,
            confidence: 0.7,
            difficulty_avg: 2,
            consistency: "LOW",
          },
        ],
        adaptation: "CREATED",
        path_id: "p2",
        diff: null,
      },
      before: {
        skill: "model_evaluation",
        name: "Model Evaluation",
        evidence_state: "UNKNOWN",
        attainment: "UNKNOWN",
        proficiency: null,
        target_level: 0.8,
        action: "VERIFY",
        blocked: false,
      },
      after: {
        skill: "model_evaluation",
        name: "Model Evaluation",
        target_level: 0.8,
        importance: 0.9,
        required_status: "CORE",
        proficiency: 0,
        confidence: 0.7,
        gap: 0.8,
        normalized_gap: 0.8,
        gap_status: "GAP",
        severity: "HIGH",
        priority: 0.9,
        is_blocking: true,
        hard_downstream: ["model_deployment"],
        soft_downstream: [],
        prerequisite_criticality: 0.8,
        evidence_count: 1,
        conflict: false,
        dominant_source: "ASSESSMENT",
        explanation: "Model evaluation is below target.",
        evidence_state: "KNOWN",
        attainment: "GAP",
        target_met: false,
        gap_priority: 0.8,
        verification_priority: 0,
        action: "REMEDIATE",
        action_priority: 0.9,
        blocked: false,
        blockers: [],
        preparation_needed: false,
        preparation_skills: [],
        downstream_impact: "Model evaluation must be addressed before deployment.",
      },
      diff: {
        added: [
          {
            key: "resource:eval",
            skill: "model_evaluation",
            title: "Model Evaluation Practice",
            reason: "Evidence moved model evaluation from UNKNOWN to GAP.",
          },
        ],
        moved: [
          {
            key: "resource:deploy",
            skill: "model_deployment",
            title: "Deployment",
            reason: "Downstream move.",
            from_week: 4,
            to_week: 6,
          },
        ],
        blocked: [],
        removed: [],
        unchanged: [],
        changed_skills: ["model_evaluation"],
      },
    });

    render(<AdaptationTrace steps={steps} />);
    expect(screen.getByTestId("adaptation-trace")).toBeInTheDocument();
    expect(screen.getByText(/UNKNOWN → GAP/)).toBeInTheDocument();
    expect(screen.getByText(/Target: 0.80/)).toBeInTheDocument();
    expect(screen.getByText(/Observed: 0.00/)).toBeInTheDocument();
    expect(screen.getByText("REMEDIATE")).toBeInTheDocument();
    expect(screen.getByText(/Model evaluation must be addressed before deployment/)).toBeInTheDocument();
    expect(screen.getByText(/\+ Model Evaluation Practice/)).toBeInTheDocument();
    expect(screen.getByText(/→ Deployment moved Week 4 → Week 6/)).toBeInTheDocument();
  });
});
