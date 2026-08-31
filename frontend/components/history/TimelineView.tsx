"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/States";
import { ScreenKicker, Waypoint } from "@/components/ui/Mark";
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

function inspectWhy(entry: { version: number; status: string; parent_path_id: string | null }): string {
  if (entry.version === 1 && !entry.parent_path_id) {
    return "No prior path existed. Diagnosis and profile produced the first route.";
  }
  if (entry.status === "ACTIVE") {
    return "New evidence triggered a backend adaptation. This version remains ACTIVE.";
  }
  return "A later evidence event replaced this version. The record itself is immutable.";
}

function whatChanged(entry: { version: number; status: string; parent_path_id: string | null }): string {
  if (entry.status === "ACTIVE") return `V${entry.version} is the live path. Prior versions remain on record.`;
  if (entry.version === 1 && !entry.parent_path_id) return "V1 established the first sequenced route.";
  return `V${entry.version} was superseded. Completed work on later versions stays frozen.`;
}

export function TimelineView() {
  const { timeline, setView } = useIntelligence();
  const active = timeline.find((entry) => entry.status === "ACTIVE") ?? timeline[timeline.length - 1];
  const [selectedId, setSelectedId] = useState<string | null>(active?.path_id ?? null);

  if (!timeline.length) {
    return (
      <EmptyState
        title="No path history"
        body="Each path version is recorded here as an immutable sequence — V1, V2, and beyond."
      />
    );
  }

  return (
    <div className="archive-view space-y-10">
      <div>
        <ScreenKicker verb="ADAPT">Your path over time</ScreenKicker>
        <h1 className="archive-title mt-3 font-display text-paper">Path history</h1>
        <p className="mt-2 text-sm text-mist">An archival record of how your path evolved as evidence changed.</p>
      </div>
      <ol className="timeline-route space-y-0" data-testid="path-timeline">
        {timeline.map((entry, index) => {
          const isActive = entry.status === "ACTIVE";
          const isLast = index === timeline.length - 1;
          const selected = selectedId === entry.path_id;
          return (
            <li
              key={entry.path_id}
              className={`timeline-milestone ${isActive ? "is-active" : "is-archived"} ${isLast ? "is-current" : ""} ${selected ? "is-selected" : ""}`}
            >
              <button
                type="button"
                className="timeline-select"
                aria-expanded={selected}
                aria-controls={`timeline-detail-${entry.path_id}`}
                onClick={() => setSelectedId(entry.path_id)}
              >
                <div className="flex flex-col items-center pt-1">
                  <span className="flex h-8 w-8 items-center justify-center text-paper">
                    <Waypoint kind={isActive ? "filled" : "open"} className="h-3 w-3" />
                  </span>
                  <span className="type-meta mt-1">V{entry.version}</span>
                </div>
                <div className="pb-2 pt-1 text-left">
                  <p className="timeline-status font-mono text-[11px] tracking-[0.14em] text-paper">{statusLabel(entry.status, entry.version)}</p>
                  <p className="type-data mt-1 text-xs text-mist">{new Date(entry.created_at).toLocaleString()}</p>
                  <p className="timeline-reason mt-2 text-xs text-mist">{versionReason(entry)}</p>
                </div>
              </button>
              {selected ? (
                <div id={`timeline-detail-${entry.path_id}`} className="timeline-inspect">
                  <p className="type-section">What changed</p>
                  <p className="mt-2 text-sm text-paper">{whatChanged(entry)}</p>
                  <p className="type-section mt-4">Why</p>
                  <p className="mt-2 text-sm text-mist">{inspectWhy(entry)}</p>
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>
      <p className="type-data text-xs text-mist" aria-hidden>
        {timeline.map((entry) => statusLabel(entry.status, entry.version)).join(" → ")}
      </p>
      <div className="flex justify-end pt-2">
        <Button showMark onClick={() => setView("map")} data-testid="history-continue">
          Explore skill map
        </Button>
      </div>
    </div>
  );
}
