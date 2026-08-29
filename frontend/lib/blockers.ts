import type { GapItem, PathItem, PrerequisiteRow } from "./types";
import { displayAttainment, prettySkill } from "./status";

export function parsePrerequisites(item: PathItem): PrerequisiteRow[] {
  return (item.prerequisites ?? [])
    .map((row) => ({
      skill: String(row.skill ?? ""),
      min_level: Number(row.min_level ?? 0),
      state: String(row.state ?? ""),
      observed: row.observed === null || row.observed === undefined ? null : Number(row.observed),
    }))
    .filter((row) => row.skill);
}

export function primaryBlocker(item: PathItem): PrerequisiteRow | null {
  const rows = parsePrerequisites(item);
  if (!rows.length) return null;
  const unknown = rows.find((row) => row.state === "UNKNOWN");
  if (unknown) return unknown;
  const unsatisfied = rows.find((row) => row.state === "UNSATISFIED");
  return unsatisfied ?? null;
}

export function waitKindLabel(item: PathItem): string | null {
  if (item.kind === "WAITING_FOR_VERIFICATION" || item.eligibility === "BLOCKED_BY_UNKNOWN") {
    return "WAITING FOR VERIFICATION";
  }
  if (item.kind === "WAITING_FOR_REMEDIATION" || item.eligibility === "BLOCKED_BY_KNOWN_GAP") {
    return "WAITING FOR REMEDIATION";
  }
  return null;
}

export function blockerStateLine(blocker: PrerequisiteRow, gap?: GapItem | null): string {
  if (blocker.state === "UNKNOWN" || blocker.observed === null) {
    return displayAttainment({ evidence_state: "UNKNOWN", attainment: "UNKNOWN" });
  }
  const target = gap?.target_level ?? blocker.min_level;
  return `${blocker.observed.toFixed(2)} / ${target.toFixed(2)} target`;
}

export function blockerDetail(item: PathItem, gap?: GapItem | null): string {
  const wait = waitKindLabel(item);
  const blocker = primaryBlocker(item);
  if (!wait || !blocker) return "";
  if (wait === "WAITING FOR VERIFICATION") {
    return "Evidence required before this resource can start.";
  }
  return "Prerequisite below target.";
}

export function requiredActionForBlocker(blocker: PrerequisiteRow, gaps: GapItem[]): string {
  const gap = gaps.find((row) => row.skill === blocker.skill);
  if (blocker.state === "UNKNOWN") return gap?.action === "VERIFY" ? "VERIFY" : "VERIFY";
  return gap?.action === "REMEDIATE_BLOCKER" ? "REMEDIATE BLOCKER" : gap?.action ?? "REMEDIATE";
}

export function resourceWaitingLabel(item: PathItem): string {
  if (item.status === "COMPLETED") return "COMPLETED";
  if (item.executable) return "EXECUTABLE";
  if (waitKindLabel(item)) return "RESOURCE WAITING";
  return "WAITING";
}

export function blockerSummary(item: PathItem, gaps: GapItem[]): string[] {
  const wait = waitKindLabel(item);
  const blocker = primaryBlocker(item);
  if (!wait || !blocker) return [];
  const gap = gaps.find((row) => row.skill === blocker.skill);
  return [
    wait,
    prettySkill(blocker.skill),
    blockerStateLine(blocker, gap),
    blockerDetail(item, gap),
  ];
}
