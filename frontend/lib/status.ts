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

export function isMissingEvidence(
  item: Pick<GapItem, "evidence_state" | "attainment"> | null | undefined,
): boolean {
  if (!item) return false;
  return item.evidence_state === "UNKNOWN" || item.attainment === "UNKNOWN";
}

/** Human label for attainment — never shows the raw UNKNOWN enum to users. */
export function displayAttainment(
  item: Pick<GapItem, "evidence_state" | "attainment"> | null | undefined,
): string {
  if (!item) return "—";
  if (isMissingEvidence(item)) return "No evidence";
  return item.attainment.replaceAll("_", " ");
}

/** Uppercase diagnosis line for forensic / mono displays. */
export function displayAttainmentCaps(
  item: Pick<GapItem, "evidence_state" | "attainment"> | null | undefined,
): string {
  const label = displayAttainment(item);
  return label === "—" ? label : label.toUpperCase();
}

export function displayDiagnosisTransition(
  before: Pick<GapItem, "evidence_state" | "attainment"> | null | undefined,
  after: Pick<GapItem, "evidence_state" | "attainment"> | null | undefined,
): string {
  return `${displayAttainmentCaps(before)} → ${displayAttainmentCaps(after)}`;
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
      return "NO EVIDENCE";
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
  if (!slug) return "";
  return slug.replaceAll("_", " ").replace(/\b\w/g, (ch) => ch.toUpperCase());
}

/** Backend enum language → learner-facing copy. Does not change stored state. */
export function humanizeEngineCopy(text: string): string {
  if (!text) return text;
  return text
    .replaceAll("BLOCKED_BY_UNKNOWN", "waiting for evidence")
    .replace(/\bis UNKNOWN\b/g, "has no evidence")
    .replace(/\bUNKNOWN is not\b/g, "Missing evidence is not")
    .replace(/\bUNKNOWN skills\b/gi, "unverified skills")
    .replace(/\bUNKNOWN\b/g, "no evidence");
}

/** Top priority gaps for competency focus — derived from live gap diagnosis, never hardcoded per role. */
export function focusGaps(gaps: GapItem[], limit = 5): GapItem[] {
  return [...gaps]
    .filter((item) => item.required_status === "CORE")
    .sort((a, b) => b.action_priority - a.action_priority)
    .slice(0, limit);
}
