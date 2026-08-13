import type { GapItem } from "./types";

export type VisualState =
  | "TARGET_MET"
  | "NEAR_TARGET"
  | "GAP"
  | "UNKNOWN"
  | "BLOCKED"
  | "VERIFY";

export function visualState(item: Pick<GapItem, "blocked" | "evidence_state" | "attainment" | "action">): VisualState {
  if (item.blocked) return "BLOCKED";
  if (item.evidence_state === "UNKNOWN" || item.attainment === "UNKNOWN") {
    return item.action === "VERIFY" ? "VERIFY" : "UNKNOWN";
  }
  if (item.attainment === "TARGET_MET") return "TARGET_MET";
  if (item.attainment === "NEAR_TARGET") return "NEAR_TARGET";
  return "GAP";
}

export function proficiencyLabel(
  item: Pick<GapItem, "evidence_state" | "proficiency">,
): string {
  if (item.evidence_state === "UNKNOWN" || item.proficiency === null || item.proficiency === undefined) {
    return "—";
  }
  return item.proficiency.toFixed(2);
}

export function isUnknown(item: Pick<GapItem, "evidence_state" | "proficiency">): boolean {
  return item.evidence_state === "UNKNOWN" || item.proficiency === null || item.proficiency === undefined;
}

export function stateCopy(state: VisualState): string {
  switch (state) {
    case "TARGET_MET":
      return "TARGET MET";
    case "NEAR_TARGET":
      return "NEAR TARGET";
    case "GAP":
      return "GAP";
    case "UNKNOWN":
      return "UNKNOWN";
    case "VERIFY":
      return "VERIFY";
    case "BLOCKED":
      return "BLOCKED";
  }
}

export function stateHint(state: VisualState): string {
  switch (state) {
    case "TARGET_MET":
      return "Evidence meets the role target";
    case "NEAR_TARGET":
      return "Evidence is close, not yet at target";
    case "GAP":
      return "Evidence is below the role target";
    case "UNKNOWN":
      return "Evidence required — not 0%";
    case "VERIFY":
      return "Unverified — prove this skill";
    case "BLOCKED":
      return "Cannot start until a prerequisite is addressed";
  }
}

export function prettySkill(slug: string): string {
  return slug.replaceAll("_", " ").replace(/\b\w/g, (ch) => ch.toUpperCase());
}

export const FOCUS_SKILLS = [
  "python",
  "statistics",
  "ml_fundamentals",
  "model_evaluation",
  "model_deployment",
] as const;

export const DEMO_EVIDENCE = [
  { skill: "python", observed_level: 0.9 },
  { skill: "statistics", observed_level: 0.35 },
  { skill: "ml_fundamentals", observed_level: 0.55 },
  { skill: "supervised_learning", observed_level: 0.85 },
] as const;
