import { describe, expect, it } from "vitest";
import { primaryBreakdownReason, semanticRelevanceTier } from "@/lib/score-breakdown";

describe("score breakdown presentation", () => {
  it("picks the highest numeric factor as the primary reason", () => {
    const primary = primaryBreakdownReason({
      skill_gap_fit: 0.82,
      role_importance: 0.91,
      semantic_similarity: 0.12,
    });
    expect(primary?.key).toBe("role_importance");
    expect(primary?.value).toBe("91%");
  });

  it("maps semantic similarity to a bounded tier", () => {
    expect(semanticRelevanceTier({ semantic_similarity: 0.8 })).toBe("High");
    expect(semanticRelevanceTier({ semantic_similarity: 0.55 })).toBe("Moderate");
    expect(semanticRelevanceTier({ semantic_similarity: 0.12 })).toBe("Minimal");
    expect(semanticRelevanceTier({})).toBeNull();
  });
});
