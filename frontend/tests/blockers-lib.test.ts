import { describe, expect, it } from "vitest";
import { blockerStateLine, waitKindLabel } from "@/lib/blockers";
import type { PathItem } from "@/lib/types";

const item: PathItem = {
  position: 0,
  week: null,
  status: "WAITING_FOR_VERIFICATION",
  resource: "lab",
  title: "Lab",
  type: "RESOURCE",
  target_skill: "deployment",
  intervention: "REMEDIATE",
  eligibility: "BLOCKED_BY_UNKNOWN",
  duration_hours: 4,
  url: null,
  score_breakdown: {},
  explanation: "",
  prerequisites: [{ skill: "docker", min_level: 0.6, state: "UNKNOWN", observed: null }],
  causality: {},
  kind: "WAITING_FOR_VERIFICATION",
  executable: false,
  gate: null,
};

describe("unknown proficiency display", () => {
  it("never formats UNKNOWN as 0%", () => {
    expect(blockerStateLine({ skill: "docker", min_level: 0.6, state: "UNKNOWN", observed: null })).toBe("UNKNOWN");
    expect(waitKindLabel(item)).toBe("WAITING FOR VERIFICATION");
  });
});
