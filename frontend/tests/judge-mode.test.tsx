import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { JudgeGuide } from "@/components/judge/JudgeGuide";

vi.mock("@/lib/session", () => ({
  useIntelligence: () => ({
    judgeMode: true,
    view: "overview",
    setView: vi.fn(),
    roleName: "AI/ML Engineer",
    attempt: null,
    suggested: { covers: ["model_evaluation"], reason: "UNKNOWN skills need verification." },
    gaps: [],
  }),
}));

describe("judge mode", () => {
  it("renders state-aware context instead of a step tour only", () => {
    render(<JudgeGuide />);
    expect(screen.getByTestId("judge-guide")).toBeInTheDocument();
    expect(screen.getByText(/What PathFinder learned/i)).toBeInTheDocument();
    expect(screen.getByText(/Diagnosed competency vs AI\/ML Engineer/i)).toBeInTheDocument();
    expect(screen.getByText(/Look next/i)).toBeInTheDocument();
  });
});
