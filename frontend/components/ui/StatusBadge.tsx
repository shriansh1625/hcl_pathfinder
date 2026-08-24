import type { VisualState } from "@/lib/status";
import { stateCopy, stateHint } from "@/lib/status";
import { Waypoint } from "@/components/ui/Mark";

const STYLES: Record<VisualState, string> = {
  TARGET_MET: "text-emerald-200/90",
  NEAR_TARGET: "text-sky-200/80",
  GAP: "text-amber-200/90",
  UNKNOWN: "text-slate-300/80",
  VERIFY: "text-paper/80",
  BLOCKED: "text-rose-200/80",
};

function markKind(state: VisualState): "filled" | "open" | "blocked" | "path" {
  if (state === "TARGET_MET") return "filled";
  if (state === "BLOCKED") return "blocked";
  if (state === "UNKNOWN" || state === "VERIFY") return "open";
  return "path";
}

export function StatusBadge({ state }: { state: VisualState }) {
  const kind = markKind(state);
  return (
    <span
      title={stateHint(state)}
      className={`inline-flex items-center gap-1.5 text-[11px] font-medium tracking-[0.12em] ${STYLES[state]}`}
    >
      <span aria-hidden className={`status-mark ${state === "TARGET_MET" ? "status-mark-in" : ""}`}>
        <Waypoint kind={kind} className={kind === "path" ? "h-2.5 w-4" : "h-2.5 w-2.5"} />
      </span>
      {stateCopy(state)}
    </span>
  );
}
