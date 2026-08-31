import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/session", () => ({
  useIntelligence: () => ({
    assessment: {
      slug: "model-evaluation-gate",
      title: "Model evaluation gate",
      description: "",
      primary_skill: "model_evaluation",
      question_count: 3,
      questions: [{ index: 0, prompt: "Q1", skill: "model_evaluation", difficulty: 2, choices: ["a", "b"] }],
    },
    submitAnswers: async () => undefined,
    updatingModel: true,
    error: null,
  }),
}));

import { AssessmentRun } from "@/components/assess/AssessmentRun";

describe("assessment submission state", () => {
  it("shows a real backend update transition, not a fake progress bar", () => {
    render(<AssessmentRun />);
    expect(screen.getByText("Updating your profile…")).toBeInTheDocument();
    expect(
      screen.getByText(/Scoring, fusion, and adaptation are running on the backend/),
    ).toBeInTheDocument();
  });
});
