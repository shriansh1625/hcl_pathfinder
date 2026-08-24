"use client";

import { isUnknown, prettySkill, proficiencyLabel, visualState, type VisualState } from "@/lib/status";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Waypoint } from "@/components/ui/Mark";
import type { GapItem } from "@/lib/types";

export function CompetencyRow({
  item,
  transitioning = false,
  onInspectEvidence,
  inspecting = false,
}: {
  item: GapItem;
  transitioning?: boolean;
  onInspectEvidence?: () => void;
  inspecting?: boolean;
}) {
  const state = visualState(item);
  const unknown = isUnknown(item);
  const ratio =
    !unknown && item.target_level > 0 ? Math.min(1, Math.max(0, (item.proficiency ?? 0) / item.target_level)) : null;

  const proficiencyDisplay = unknown
    ? "—"
    : item.conflict && item.proficiency !== null
      ? item.proficiency.toFixed(2)
      : `${proficiencyLabel(item)} / ${item.target_level.toFixed(2)}`;

  return (
    <div
      className={`competency-row grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 py-4 md:grid-cols-[minmax(0,1.4fr)_minmax(7rem,auto)_auto] ${transitioning ? "state-shift" : ""} ${item.conflict ? "has-conflict" : ""}`}
    >
      <div>
        <p className="flex items-center gap-2 text-sm text-paper">
          <Waypoint
            kind={state === "TARGET_MET" ? "filled" : state === "UNKNOWN" || state === "VERIFY" ? "open" : state === "BLOCKED" ? "blocked" : "path"}
            className={`shrink-0 text-paper/55 ${state === "GAP" || state === "NEAR_TARGET" ? "h-2.5 w-4" : "h-2.5 w-2.5"}`}
          />
          {item.name || prettySkill(item.skill)}
        </p>
        <p className="mt-1 text-xs text-mist">
          {unknown ? "Evidence required" : `Target ${item.target_level.toFixed(2)} · ${item.action}`}
        </p>
        {item.conflict || (item.evidence_count > 0 && onInspectEvidence) ? (
          <button
            type="button"
            className="mt-2 text-[11px] uppercase tracking-[0.12em] text-mist underline-offset-2 hover:underline"
            onClick={onInspectEvidence}
            data-testid={`conflict-toggle-${item.skill}`}
          >
            {inspecting ? "Hide evidence" : "Inspect evidence →"}
          </button>
        ) : null}
        <Meter state={state} ratio={ratio} />
      </div>
      <div className="flex flex-col items-end gap-1">
        <p className="font-mono text-[17px] tabular-nums text-paper" data-testid={`proficiency-${item.skill}`}>
          {proficiencyDisplay}
        </p>
        {item.conflict ? (
          <span className="conflict-pill" data-testid={`conflict-pill-${item.skill}`}>
            CONFLICT
          </span>
        ) : null}
      </div>
      <StatusBadge state={state} />
    </div>
  );
}

function Meter({ state, ratio }: { state: VisualState; ratio: number | null }) {
  if (ratio === null) {
    return (
      <div className="meter meter-unknown mt-3" aria-hidden>
        <span className="meter-unknown-mark" />
      </div>
    );
  }
  return (
    <div className={`meter mt-3 meter-${state.toLowerCase()}`} aria-hidden>
      <span className="meter-fill" style={{ width: `${Math.round(ratio * 100)}%` }} />
    </div>
  );
}
