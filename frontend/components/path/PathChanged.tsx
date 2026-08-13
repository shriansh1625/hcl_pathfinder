"use client";

import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { EmptyState } from "@/components/ui/States";
import { useIntelligence } from "@/lib/session";
import { prettySkill } from "@/lib/status";
import type { DiffEntry } from "@/lib/types";

const LABELS = {
  added: "ADDED",
  removed: "REMOVED",
  moved: "MOVED",
  unchanged: "UNCHANGED",
  blocked: "BLOCKED",
} as const;

export function PathChanged() {
  const { previousPath, activePath, diff, attempt, setView } = useIntelligence();
  const frozen = (activePath?.items || []).filter((item) => item.status === "COMPLETED");

  if (!diff && !attempt) {
    return <EmptyState title="No adaptation yet" body="Submit an assessment to generate Path V2 from backend evidence." />;
  }

  const groups: { key: keyof typeof LABELS; items: DiffEntry[] }[] = [
    { key: "added", items: diff?.added ?? [] },
    { key: "removed", items: diff?.removed ?? [] },
    { key: "moved", items: diff?.moved ?? [] },
    { key: "blocked", items: diff?.blocked ?? [] },
    { key: "unchanged", items: (diff?.unchanged ?? []).slice(0, 4) },
  ];

  return (
    <div className="space-y-6">
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-accent">Adaptation</p>
        <h1 className="mt-2 text-3xl font-medium text-paper">Your path changed.</h1>
        <p className="mt-2 text-sm text-mist">New evidence changed your competency profile.</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel className="p-5">
          <p className="text-xs uppercase tracking-wider text-mist">V{previousPath?.version ?? 1}</p>
          <ul className="mt-3 space-y-2 text-sm text-paper">
            {(previousPath?.items || [])
              .filter((item) => item.executable)
              .slice(0, 8)
              .map((item) => (
                <li key={item.position}>
                  {prettySkill(item.target_skill)} — {item.title}
                </li>
              ))}
          </ul>
        </Panel>
        <Panel className="p-5">
          <p className="text-xs uppercase tracking-wider text-mist">V{activePath?.version ?? 2}</p>
          <ul className="mt-3 space-y-2 text-sm text-paper">
            {(diff?.added ?? []).slice(0, 6).map((item) => (
              <li key={item.key}>+ {item.title}</li>
            ))}
            {(diff?.blocked ?? []).slice(0, 4).map((item) => (
              <li key={item.key} className="text-mist">
                {item.title} delayed
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <Panel>
        <div className="divide-y divide-line">
          {groups.map((group) =>
            group.items.length ? (
              <div key={group.key} className="px-5 py-4">
                <p className="font-mono text-[11px] text-accent">{LABELS[group.key]}</p>
                <ul className="mt-2 space-y-2">
                  {group.items.map((item) => (
                    <li key={item.key} data-testid={`diff-${group.key}`}>
                      <p className="text-sm text-paper">{item.title}</p>
                      <p className="text-xs text-mist">{item.reason}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null,
          )}
        </div>
      </Panel>

      <Panel className="border-accent/30 p-5">
        <p className="text-xs uppercase tracking-wider text-accent">Frozen work</p>
        <h2 className="mt-2 text-lg text-paper">Your completed work was protected.</h2>
        {frozen.length ? (
          <ul className="mt-4 space-y-2" data-testid="frozen-work">
            {frozen.map((item) => (
              <li key={item.position} className="text-sm text-paper">
                ✓ Week {item.week ?? "—"} — {item.title} · COMPLETED
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-mist">No completed items on the active path.</p>
        )}
        <p className="mt-4 text-sm text-mist">PathFinder never rewrites completed work.</p>
      </Panel>

      <div className="flex justify-end">
        <Button onClick={() => setView("why")}>Why?</Button>
      </div>
    </div>
  );
}
