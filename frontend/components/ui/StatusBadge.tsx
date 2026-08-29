import type { VisualState } from "@/lib/status";
import { stateCopy, stateHint } from "@/lib/status";
import { Waypoint } from "@/components/ui/Mark";

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
      className={`status-badge status-badge-${state.toLowerCase()}`}
    >
      <span aria-hidden className={`status-mark ${state === "TARGET_MET" ? "status-mark-in" : ""}`}>
        <Waypoint kind={kind} className={kind === "path" ? "h-2.5 w-4" : "h-2.5 w-2.5"} />
      </span>
      {stateCopy(state)}
    </span>
  );
}
