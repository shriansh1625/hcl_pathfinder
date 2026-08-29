/** Read-only presentation of backend score_breakdown — no client-side scoring. */

export const BREAKDOWN_LABELS: Record<string, string> = {
  skill_gap_fit: "Diagnosed gap",
  role_importance: "Role relevance",
  prerequisite_fit: "Prerequisite fit",
  difficulty_fit: "Difficulty fit",
  duration_fit: "Duration fit",
  learning_style_fit: "Learning style fit",
  semantic_similarity: "Semantic relevance",
  final_score: "Composite score",
};

export const BREAKDOWN_ORDER = [
  "skill_gap_fit",
  "role_importance",
  "prerequisite_fit",
  "difficulty_fit",
  "duration_fit",
  "learning_style_fit",
  "semantic_similarity",
] as const;

export function formatBreakdownValue(key: string, value: unknown): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  if (key === "final_score") return value.toFixed(3);
  return `${Math.round(value * 100)}%`;
}

export function breakdownRows(
  breakdown: Record<string, unknown>,
): { key: string; label: string; value: string }[] {
  return BREAKDOWN_ORDER.filter((key) => key in breakdown).map((key) => ({
    key,
    label: BREAKDOWN_LABELS[key] ?? key,
    value: formatBreakdownValue(key, breakdown[key]),
  }));
}

export function primaryBreakdownReason(
  breakdown: Record<string, unknown>,
): { key: string; label: string; value: string } | null {
  const rows = breakdownRows(breakdown).filter((row) => row.key !== "final_score");
  if (!rows.length) return null;
  let best = rows[0];
  let bestScore = typeof breakdown[best.key] === "number" ? (breakdown[best.key] as number) : -1;
  for (const row of rows.slice(1)) {
    const raw = breakdown[row.key];
    if (typeof raw === "number" && raw > bestScore) {
      best = row;
      bestScore = raw;
    }
  }
  return best;
}

export function semanticRelevanceTier(breakdown: Record<string, unknown>): string | null {
  const raw = breakdown.semantic_similarity;
  if (typeof raw !== "number" || Number.isNaN(raw)) return null;
  if (raw >= 0.75) return "High";
  if (raw >= 0.5) return "Moderate";
  if (raw >= 0.25) return "Low";
  return "Minimal";
}