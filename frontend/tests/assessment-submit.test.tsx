import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/session", () => ({
  useIntelligence: () => ({
    assessment: {
      slug: "docker-gate",
      title: "Docker gate",
      description: "",
      primary_skill: "docker",
      question_count: 1,
      questions: [{ index: 0, prompt: "Q?", skill: "docker", difficulty: 1, choices: ["a", "b"] }],
    },
    submitAnswers: vi.fn(),
    updatingModel: false,
    error: null,
  }),
}));

import { AssessmentRun } from "@/components/assess/AssessmentRun";

describe("assessment submit control", () => {
  it("exposes a dedicated submit test id that cannot collide with judge rail copy", () => {
    render(<AssessmentRun />);
    fireEvent.click(screen.getByRole("radio", { name: "a" }));
    const btn = screen.getByTestId("assessment-submit");
    expect(btn).toHaveTextContent("Submit");
    expect(btn).not.toHaveTextContent(/update diagnosis/i);
  });
});
