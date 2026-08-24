import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/session", () => ({
  useIntelligence: () => ({
    timeline: [
      {
        path_id: "p1",
        version: 1,
        status: "SUPERSEDED",
        parent_path_id: null,
        created_at: "2026-08-13T10:00:00Z",
      },
      {
        path_id: "p2",
        version: 2,
        status: "ACTIVE",
        parent_path_id: "p1",
        created_at: "2026-08-13T10:05:00Z",
      },
    ],
  }),
}));

import { TimelineView } from "@/components/history/TimelineView";

describe("timeline rendering", () => {
  it("renders the V1 → V2 chain from the timeline API", () => {
    render(<TimelineView />);
    expect(screen.getByTestId("path-timeline")).toHaveTextContent("V1");
    expect(screen.getByTestId("path-timeline")).toHaveTextContent("V2");
    expect(screen.getByText("V1 SUPERSEDED")).toBeInTheDocument();
    expect(screen.getByText("V2 ACTIVE")).toBeInTheDocument();
    expect(screen.getByText(/Initial path generated/i)).toBeInTheDocument();
    expect(screen.getByText(/Current active path after the latest adaptation/i)).toBeInTheDocument();
  });
});
