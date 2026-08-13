import { describe, expect, it } from "vitest";
import { isUnknown, proficiencyLabel, visualState } from "@/lib/status";

const unknown = {
  blocked: false,
  evidence_state: "UNKNOWN",
  attainment: "UNKNOWN",
  action: "VERIFY",
  proficiency: null,
};

const gap = {
  blocked: false,
  evidence_state: "KNOWN",
  attainment: "GAP",
  action: "REMEDIATE",
  proficiency: 0.35,
};

const met = {
  blocked: false,
  evidence_state: "KNOWN",
  attainment: "TARGET_MET",
  action: "ADVANCE",
  proficiency: 0.9,
};

const blocked = {
  blocked: true,
  evidence_state: "UNKNOWN",
  attainment: "UNKNOWN",
  action: "VERIFY",
  proficiency: null,
};

describe("competency presentation", () => {
  it("never renders UNKNOWN as 0", () => {
    expect(isUnknown(unknown)).toBe(true);
    expect(proficiencyLabel(unknown)).toBe("—");
    expect(proficiencyLabel(unknown)).not.toBe("0.00");
    expect(proficiencyLabel(unknown)).not.toBe("0%");
  });

  it("maps GAP, TARGET MET, and BLOCKED from backend fields", () => {
    expect(visualState(gap)).toBe("GAP");
    expect(visualState(met)).toBe("TARGET_MET");
    expect(visualState(blocked)).toBe("BLOCKED");
    expect(visualState(unknown)).toBe("VERIFY");
  });
});
