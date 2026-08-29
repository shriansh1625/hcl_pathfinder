import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ErrorState } from "@/components/ui/States";

describe("status and error rendering", () => {
  it("renders GAP with a text label, not color alone", () => {
    render(<StatusBadge state="GAP" />);
    expect(screen.getByText("GAP")).toBeInTheDocument();
  });

  it("renders TARGET MET with a text label", () => {
    render(<StatusBadge state="TARGET_MET" />);
    expect(screen.getByText("TARGET MET")).toBeInTheDocument();
  });

  it("renders BLOCKED with a text label", () => {
    render(<StatusBadge state="BLOCKED" />);
    expect(screen.getByText("BLOCKED")).toBeInTheDocument();
  });

  it("renders UNKNOWN as no evidence, not 0%", () => {
    render(<StatusBadge state="UNKNOWN" />);
    expect(screen.getByText("NO EVIDENCE")).toBeInTheDocument();
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
    expect(screen.queryByText("0.00")).not.toBeInTheDocument();
  });

  it("renders API error state with the backend message", () => {
    render(<ErrorState message="Learner not found" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Request failed");
    expect(screen.getByRole("alert")).toHaveTextContent("Learner not found");
  });
});
