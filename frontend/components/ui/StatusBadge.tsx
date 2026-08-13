import type { VisualState } from "@/lib/status";
import { stateCopy, stateHint } from "@/lib/status";

const STYLES: Record<VisualState, string> = {
  TARGET_MET: "border-emerald-400/40 bg-emerald-400/10 text-emerald-200",
  NEAR_TARGET: "border-sky-400/40 bg-sky-400/10 text-sky-200",
  GAP: "border-amber-400/40 bg-amber-400/10 text-amber-200",
  UNKNOWN: "border-dashed border-slate-400/50 bg-transparent text-slate-200",
  VERIFY: "border-dashed border-cyan-300/50 bg-cyan-300/5 text-cyan-100",
  BLOCKED: "border-rose-400/40 bg-rose-400/10 text-rose-200",
};

export function StatusBadge({ state }: { state: VisualState }) {
  return (
    <span
      title={stateHint(state)}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-wide ${STYLES[state]}`}
    >
      <span aria-hidden className="font-mono text-[10px]">
        {state === "UNKNOWN" || state === "VERIFY" ? "○" : state === "TARGET_MET" ? "●" : "▸"}
      </span>
      {stateCopy(state)}
    </span>
  );
}
