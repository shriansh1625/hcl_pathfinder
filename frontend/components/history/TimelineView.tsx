"use client";

import { EmptyState } from "@/components/ui/States";
import { Mark, ScreenKicker } from "@/components/ui/Mark";
import { useIntelligence } from "@/lib/session";

function statusLabel(status: string, version: number): string {
  if (status === "ACTIVE") return `V${version} ACTIVE`;
  if (status === "SUPERSEDED") return `V${version} SUPERSEDED`;
  return `V${version} ${status}`;
}

function versionReason(entry: { version: number; status: string; parent_path_id: string | null }): string {
  if (entry.version === 1 && !entry.parent_path_id) return "Initial path generated from diagnosis and learner profile.";
  if (entry.status === "ACTIVE") return "Current active path after the latest adaptation.";
  return "Superseded when new evidence triggered a backend adaptation.";
}

export function TimelineView() {
  const { timeline } = useIntelligence();
  if (!timeline.length) {
    return (
      <EmptyState
        title="No path history"
        body="Each path version is recorded here as an immutable sequence — V1, V2, and beyond."
      />
    );
  }

  return (
    <div className="space-y-10">
      <div>
        <ScreenKicker verb="ADAPT">History</ScreenKicker>
        <h1 className="type-headline mt-3 text-4xl font-medium text-paper">Path history</h1>
        <p className="mt-2 text-sm text-mist">An archival record of how your path evolved as evidence changed.</p>
      </div>
      <ol className="timeline-route space-y-0" data-testid="path-timeline">
        {timeline.map((entry, index) => {
          const isActive = entry.status === "ACTIVE";
          const isLast = index === timeline.length - 1;
          return (
            <li
              key={entry.path_id}
              className={`timeline-milestone flex gap-4 ${isActive ? "is-active" : "is-archived"} ${isLast ? "is-current" : ""}`}
              tabIndex={0}
            >
              <div className="flex flex-col items-center pt-1">
                <span className="flex h-8 w-8 items-center justify-center text-paper">
                  <Mark className="h-3 w-[18px]" />
                </span>
                <span className="type-meta mt-1">V{entry.version}</span>
              </div>
              <div className="pb-8 pt-1">
                <p className="timeline-status font-mono text-[11px] tracking-[0.14em] text-paper">{statusLabel(entry.status, entry.version)}</p>
                <p className="type-data mt-1 text-xs text-mist">{new Date(entry.created_at).toLocaleString()}</p>
                <p className="timeline-reason mt-2 text-xs text-mist">{versionReason(entry)}</p>
              </div>
            </li>
          );
        })}
      </ol>
      <p className="type-data text-xs text-mist" aria-hidden>
        {timeline.map((entry) => statusLabel(entry.status, entry.version)).join(" → ")}
      </p>
    </div>
  );
}