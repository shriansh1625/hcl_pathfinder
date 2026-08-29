import { describe, expect, it } from "vitest";
import { continueLabel, nextFlowView } from "@/lib/flow";

describe("workspace flow navigation", () => {
  it("advances history to skill map instead of staying on history", () => {
    expect(nextFlowView("history")).toBe("map");
    expect(continueLabel("history")).toBe("Explore skill map");
  });

  it("ends the guided flow on skill map", () => {
    expect(nextFlowView("map")).toBeNull();
  });
});
