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