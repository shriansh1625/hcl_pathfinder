"use client";



import { useState } from "react";

import { BlockerChain } from "@/components/ui/BlockerChain";

import { Button } from "@/components/ui/Button";

import { EmptyState } from "@/components/ui/States";

import { Mark, ScreenKicker } from "@/components/ui/Mark";

import {

  blockerDetail,

  blockerStateLine,

  primaryBlocker,

  resourceWaitingLabel,

  waitKindLabel,

} from "@/lib/blockers";

import { GroundedExplain } from "@/components/judge/AiSurface";
import { useIntelligence } from "@/lib/session";

import { prettySkill } from "@/lib/status";

import type { PathItem } from "@/lib/types";



function BlockerExposition({ item, gaps }: { item: PathItem; gaps: ReturnType<typeof useIntelligence>["gaps"] }) {

  const wait = waitKindLabel(item);

  const blocker = primaryBlocker(item);

  if (!wait || !blocker) return null;

  const gap = gaps.find((row) => row.skill === blocker.skill);

  return (

    <div className="blocker-expo" data-testid="blocker-exposition">

      <p className="blocker-expo-wait">{wait}</p>

      <p className="blocker-expo-skill">{prettySkill(blocker.skill)}</p>

      <p className="blocker-expo-state font-mono tabular-nums">{blockerStateLine(blocker, gap)}</p>

      <p className="blocker-expo-detail">{blockerDetail(item, gap)}</p>

    </div>

  );

}



export function PathView() {

  const { activePath, roleName, gaps } = useIntelligence();

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

    <div className="space-y-10">

      <div>

        <ScreenKicker verb="PATH">Version {activePath.version}</ScreenKicker>

        <h1 className="mt-3 font-display text-4xl font-medium text-paper">Your path to {roleName}</h1>

        <p className="mt-2 font-mono text-sm tabular-nums text-mist">

          V{activePath.version} · {activePath.status} · {activePath.total_estimated_hours ?? "—"}h

        </p>

      </div>



      <div className="space-y-8">

        {[...grouped.entries()].map(([week, items]) => (

          <div key={String(week)}>

            <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.16em] text-mist">

              {typeof week === "number" ? `Week ${week}` : week}

            </p>

            <div className="space-y-2">

              {items.map((item) => {

                const waiting = waitKindLabel(item);

                return (

                  <button

                    key={item.position}

                    type="button"

                    onClick={() => setOpen(item)}

                    className="path-row flex w-full flex-col items-stretch gap-3 border border-line bg-transparent px-4 py-3 text-left"

                  >

                    <div className="flex items-start justify-between gap-4">

                      <div className="flex items-start gap-3">

                        <Mark className="mt-1 h-3 w-[18px] shrink-0 text-paper/40" />

                        <div>

                          <p className="text-sm text-paper">{item.title || prettySkill(item.target_skill)}</p>

                          <p className="mt-1 text-xs text-mist">

                            {prettySkill(item.target_skill)} · {item.intervention || item.kind}

                            {item.duration_hours ? ` · ${item.duration_hours}h` : ""}

                          </p>

                        </div>

                      </div>

                      <span className="shrink-0 font-mono text-[11px] tracking-wider text-mist">

                        {resourceWaitingLabel(item)}

                      </span>

                    </div>

                    {waiting ? <BlockerExposition item={item} gaps={gaps} /> : null}

                  </button>

                );

              })}

            </div>

          </div>

        ))}

      </div>



      {open ? <WhyDrawer item={open} onClose={() => setOpen(null)} /> : null}

    </div>

  );

}



export function WhyDrawer({ item, onClose }: { item: PathItem; onClose: () => void }) {

  const { gaps, learnerId } = useIntelligence();

  const cause = item.causality || {};

  const waiting = waitKindLabel(item);



  return (

    <div className="drawer-scrim fixed inset-0 z-40 flex justify-end bg-black/45" role="dialog" aria-modal="true" aria-labelledby="why-drawer-title">

      <button type="button" className="h-full flex-1" aria-label="Close" onClick={onClose} />

      <section className="drawer-panel h-full w-full max-w-md overflow-y-auto border-l border-line bg-ink-900">

        <div className="flex items-center justify-between border-b border-line px-5 py-4">

          <h2 id="why-drawer-title" className="font-display text-xl text-paper">Why this is here</h2>

          <Button variant="ghost" onClick={onClose}>

            Close

          </Button>

        </div>

        <div className="space-y-5 p-5 text-sm">

          <p className="text-paper">{item.title}</p>

          {waiting ? <BlockerChain item={item} gaps={gaps} /> : null}

          <Field label="Skill gap" value={cause.why_this_skill || item.explanation} />

          <Field label="Intervention" value={cause.why_this_intervention || item.intervention} />

          <Field label="Positioning" value={cause.why_this_position || `Week ${item.week ?? "—"}`} />

          <Field label="Resource" value={cause.why_this_resource || item.resource} />

          <Field label="Why selected" value={cause.why_selected || item.explanation} />

          {learnerId ? (
            <GroundedExplain
              intent="WHY_RESOURCE"
              resource={item.resource || undefined}
              skill={item.target_skill || undefined}
              triggerLabel="Why this resource?"
              testId="why-resource"
            />
          ) : null}

        </div>

      </section>

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
