"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { EmptyState } from "@/components/ui/States";
import { useIntelligence } from "@/lib/session";
import { prettySkill } from "@/lib/status";
import type { PathItem } from "@/lib/types";

function eligibilityCopy(item: PathItem): string {
  if (item.status === "COMPLETED") return "COMPLETED";
  if (item.kind === "WAITING_FOR_VERIFICATION") return "Cannot start yet";
  if (item.kind === "WAITING_FOR_REMEDIATION") return "Blocked until prerequisite is addressed";
  if (!item.executable) return "Waiting";
  return "Executable";
}

export function PathView() {
  const { activePath, roleName, setView } = useIntelligence();
  const [open, setOpen] = useState<PathItem | null>(null);

  if (!activePath) {
    return <EmptyState title="No active path" body="Generate a path from the goal screen." />;
  }

  const grouped = new Map<number | string, PathItem[]>();
  for (const item of activePath.items) {
    const key = item.week ?? "Unscheduled";
    grouped.set(key, [...(grouped.get(key) ?? []), item]);
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-accent">Roadmap</p>
        <h1 className="mt-2 text-3xl font-medium text-paper">Your path to {roleName}</h1>
        <p className="mt-1 font-mono text-sm text-mist">
          V{activePath.version} · {activePath.status} · {activePath.total_estimated_hours ?? "—"}h
        </p>
      </div>

      <div className="space-y-4">
        {[...grouped.entries()].map(([week, items]) => (
          <div key={String(week)}>
            <p className="mb-2 font-mono text-xs uppercase tracking-wider text-mist">
              {typeof week === "number" ? `Week ${week}` : week}
            </p>
            <div className="space-y-2">
              {items.map((item) => (
                <button
                  key={item.position}
                  type="button"
                  onClick={() => setOpen(item)}
                  className="flex w-full items-start justify-between gap-4 rounded-xl border border-line bg-ink-800 px-4 py-3 text-left hover:border-accent/40"
                >
                  <div>
                    <p className="text-sm text-paper">{item.title || prettySkill(item.target_skill)}</p>
                    <p className="mt-1 text-xs text-mist">
                      {prettySkill(item.target_skill)} · {item.intervention || item.kind}
                      {item.duration_hours ? ` · ${item.duration_hours}h` : ""}
                    </p>
                  </div>
                  <span className="shrink-0 font-mono text-[11px] text-mist">{eligibilityCopy(item)}</span>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-end">
        <Button onClick={() => setView("prove")}>Continue</Button>
      </div>

      {open ? <WhyDrawer item={open} onClose={() => setOpen(null)} /> : null}
    </div>
  );
}

export function WhyDrawer({ item, onClose }: { item: PathItem; onClose: () => void }) {
  const cause = item.causality || {};
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/50" role="dialog" aria-modal="true">
      <button type="button" className="h-full flex-1" aria-label="Close" onClick={onClose} />
      <Panel className="h-full w-full max-w-md overflow-y-auto rounded-none border-y-0 border-r-0">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h2 className="text-base text-paper">Why this is here</h2>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
        <div className="space-y-4 p-5 text-sm">
          <p className="text-paper">{item.title}</p>
          <Field label="Skill gap" value={cause.why_this_skill || item.explanation} />
          <Field label="Intervention" value={cause.why_this_intervention || item.intervention} />
          <Field label="Positioning" value={cause.why_this_position || `Week ${item.week ?? "—"}`} />
          <Field label="Resource" value={cause.why_this_resource || item.resource} />
          <Field label="Why selected" value={cause.why_selected || item.explanation} />
          {item.prerequisites?.length ? (
            <Field
              label="Prerequisites"
              value={item.prerequisites
                .map((row) => String(row.skill || row.slug || JSON.stringify(row)))
                .join(", ")}
            />
          ) : null}
          {!item.executable ? (
            <p className="text-xs text-mist">
              {item.kind === "WAITING_FOR_VERIFICATION"
                ? "Cannot start yet — verification is still required."
                : item.kind === "WAITING_FOR_REMEDIATION"
                  ? "Blocked until prerequisite is addressed."
                  : "Waiting."}
            </p>
          ) : null}
        </div>
      </Panel>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wider text-mist">{label}</p>
      <p className="mt-1 leading-relaxed text-paper">{value || "—"}</p>
    </div>
  );
}
