"use client";

import { Panel } from "@/components/ui/Panel";
import { EmptyState } from "@/components/ui/States";
import { useIntelligence } from "@/lib/session";

export function TimelineView() {
  const { timeline } = useIntelligence();
  if (!timeline.length) {
    return <EmptyState title="No path history" body="A generated path will appear here as V1." />;
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-accent">History</p>
        <h1 className="mt-2 text-3xl font-medium text-paper">Path history</h1>
      </div>
      <Panel className="p-6">
        <ol className="space-y-0" data-testid="path-timeline">
          {timeline.map((entry, index) => (
            <li key={entry.path_id} className="flex gap-4">
              <div className="flex flex-col items-center">
                <span className="flex h-8 w-8 items-center justify-center rounded-full border border-accent text-xs text-accent">
                  V{entry.version}
                </span>
                {index < timeline.length - 1 ? <span className="h-10 w-px bg-line" /> : null}
              </div>
              <div className="pb-8">
                <p className="text-sm text-paper">
                  {entry.status === "ACTIVE" ? "Active" : entry.status === "SUPERSEDED" ? "Superseded" : entry.status}
                </p>
                <p className="mt-1 font-mono text-xs text-mist">
                  {new Date(entry.created_at).toLocaleString()}
                </p>
                {entry.parent_path_id ? (
                  <p className="mt-1 text-xs text-mist">Parent of this version exists in the chain.</p>
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
      </Panel>
    </div>
  );
}
