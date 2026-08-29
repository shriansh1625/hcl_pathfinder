import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WhyDrawer } from "@/components/path/PathView";
import type { PathItem } from "@/lib/types";

vi.mock("@/lib/session", () => ({
  useIntelligence: () => ({}),
}));

const breakdown = {
  skill_gap_fit: 0.82,
  role_importance: 0.91,
  prerequisite_fit: 1,
  difficulty_fit: 0.75,
  duration_fit: 0.66,
  learning_style_fit: 0.8,
  semantic_similarity: 0.12,
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
  score_breakdown: breakdown,
  explanation: "Statistics is a diagnosed gap.",
  prerequisites: [{ skill: "python" }],
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

describe("path item causal explanation", () => {
  it("renders stored causality, not an AI recommendation slogan", () => {
    render(<WhyDrawer item={item} onClose={() => undefined} />);
    expect(screen.getByText("Why this is here")).toBeInTheDocument();
    expect(screen.getByTestId("why-primary-reason")).toBeInTheDocument();
    expect(screen.getByText("Nothing precedes the first executable week.")).toBeInTheDocument();
    expect(screen.getByText("Intervention is FOUNDATION.")).toBeInTheDocument();
    expect(screen.queryByText(/AI recommended this/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Because it scored highly/i)).not.toBeInTheDocument();
  });

  it("renders every backend score_breakdown field", () => {
    render(<WhyDrawer item={item} onClose={() => undefined} />);
    expect(screen.getByTestId("why-primary-reason")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByTestId("why-semantic-relevance")).toBeInTheDocument();
    expect(screen.getByText("Minimal")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Show all scoring factors/i }));
    expect(screen.getByTestId("why-score-breakdown")).toBeInTheDocument();
    for (const key of Object.keys(breakdown)) {
      expect(screen.getByTestId(`why-breakdown-${key}`)).toBeInTheDocument();
    }
    expect(screen.getByText("82%")).toBeInTheDocument();
    expect(screen.getByText("Role relevance")).toBeInTheDocument();
    expect(screen.getByText("Why now")).toBeInTheDocument();
  });
});
