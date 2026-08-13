import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WhyDrawer } from "@/components/path/PathView";
import type { PathItem } from "@/lib/types";

vi.mock("@/lib/session", () => ({
  useIntelligence: () => ({}),
}));

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
    expect(screen.getByText("Evidence places statistics below the role target.")).toBeInTheDocument();
    expect(screen.getByText("Intervention is FOUNDATION.")).toBeInTheDocument();
    expect(screen.queryByText(/AI recommended this/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Because it scored highly/i)).not.toBeInTheDocument();
  });
});
