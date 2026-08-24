"use client";

import { EmptyState } from "@/components/ui/States";
import { Mark, ScreenKicker } from "@/components/ui/Mark";
import { useIntelligence } from "@/lib/session";

export function TimelineView() {
  const { timeline } = useIntelligence();
  if (!timeline.length) {
    return <EmptyState title="No path history" body="A generated path will appear here as V1." />;
  }

  return (
    <div className="space-y-10">
      <div>
        <ScreenKicker verb="ADAPT">History</ScreenKicker>
        <h1 className="mt-3 font-display text-4xl font-medium text-paper">Path history</h1>
      </div>
      <ol className="space-y-0" data-testid="path-timeline">
        {timeline.map((entry, index) => (
          <li key={entry.path_id} className="flex gap-4">
            <div className="flex flex-col items-center">
              <span className="flex h-8 w-8 items-center justify-center text-paper">
                <Mark className="h-3 w-[18px]" />
              </span>
              <span className="font-mono text-[11px] text-mist">V{entry.version}</span>
              {index < timeline.length - 1 ? <span className="mt-1 h-8 w-px bg-line" /> : null}
            </div>
            <div className="pb-8 pt-1">
              <p className="text-sm text-paper">
                {entry.status === "ACTIVE" ? "Active" : entry.status === "SUPERSEDED" ? "Superseded" : entry.status}
              </p>
              <p className="mt-1 font-mono text-xs text-mist">
                {new Date(entry.created_at).toLocaleString()}
              </p>
              {entry.parent_path_id ? (
                <p className="mt-1 text-xs text-mist">Continues the previous version.</p>
              ) : (
                <p className="mt-1 text-xs text-mist">Created as the first path.</p>
              )}
            </div>
          </li>
        ))}
      </ol>
      <p className="font-mono text-xs text-mist">
        {timeline.map((entry) => `V${entry.version}`).join(" → ")}
      </p>
    </div>
  );
}
