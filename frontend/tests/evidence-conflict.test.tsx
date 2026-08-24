import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EvidencePanel } from "@/components/ui/EvidencePanel";

vi.mock("@/lib/api", () => ({
  api: {
    evidence: vi.fn().mockResolvedValue([
      {
        id: "1",
        skill: "python",
        source: "SELF_REPORT",
        observed_level: 0.9,
        reliability: 0.35,
        confidence: 0.8,
        created_at: "2026-01-01T00:00:00Z",
      },
      {
        id: "2",
        skill: "python",
        source: "ASSESSMENT",
        observed_level: 0.5,
        reliability: 0.9,
        confidence: 0.85,
        created_at: "2026-01-02T00:00:00Z",
      },
    ]),
  },
}));

describe("evidence conflict display", () => {
  it("renders fused value and both evidence rows", async () => {
    render(
      <EvidencePanel
        skill="python"
        learnerId="learner-1"
        fused={{
          skill: "python",
          proficiency: 0.63,
          confidence: 0.72,
          status: "DEVELOPING",
          evidence_count: 2,
          conflict: true,
          conflict_spread: 0.4,
          dominant_source: "ASSESSMENT",
          reason: "Fused from 2 evidence record(s).",
        }}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("0.63")).toBeInTheDocument();
    });
    expect(screen.getByText("SELF REPORT")).toBeInTheDocument();
    expect(screen.getByText("0.90")).toBeInTheDocument();
    expect(screen.getByText("Dominant source")).toBeInTheDocument();
    expect(screen.getAllByText("ASSESSMENT").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByTestId("evidence-conflict")).toHaveTextContent("CONFLICT DETECTED");
  });
});
