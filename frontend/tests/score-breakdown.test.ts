import { describe, expect, it } from "vitest";
import { BREAKDOWN_LABELS, BREAKDOWN_ORDER, breakdownRows, formatBreakdownValue } from "@/lib/score-breakdown";

describe("score breakdown presentation", () => {
  const sample = {
    skill_gap_fit: 0.82,
    role_importance: 0.91,
    prerequisite_fit: 1,
    difficulty_fit: 0.75,
    duration_fit: 0.66,
    learning_style_fit: 0.8,
    semantic_similarity: 0.12,
  };

  it("formats percentage and composite values from backend numbers", () => {
    expect(formatBreakdownValue("skill_gap_fit", 0.82)).toBe("82%");
    expect(formatBreakdownValue("final_score", 0.847)).toBe("0.847");
    expect(formatBreakdownValue("skill_gap_fit", "bad")).toBe("—");
  });

  it("renders every visible breakdown field in canonical order", () => {
    const rows = breakdownRows(sample);
    expect(rows.map((row) => row.key)).toEqual([...BREAKDOWN_ORDER]);
    for (const row of rows) {
      expect(row.label).toBe(BREAKDOWN_LABELS[row.key]);
      expect(row.value).not.toBe("—");
    }
  });
});