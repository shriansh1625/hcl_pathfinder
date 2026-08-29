import type { ViewId } from "./types";

export const FLOW: ViewId[] = ["overview", "blockers", "path", "prove", "result", "changed", "why", "history"];

export function nextFlowView(view: ViewId): ViewId | null {
  if (view === "result") return "changed";
  if (view === "history") return "map";
  const idx = FLOW.indexOf(view);
  if (idx < 0) return view === "map" ? null : "overview";
  if (idx < FLOW.length - 1) return FLOW[idx + 1];
  return null;
}

export function continueLabel(view: ViewId): string {
  if (view === "result") return "See what changed";
  if (view === "history") return "Explore skill map";
  return "Continue";
}
