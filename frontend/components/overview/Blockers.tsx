"use client";

import { ResourceBlockerCard } from "@/components/ui/ResourceBlockerCard";
import { EmptyState } from "@/components/ui/States";
import { ScreenKicker } from "@/components/ui/Mark";
import { waitKindLabel } from "@/lib/blockers";
import { useIntelligence } from "@/lib/session";
import { humanizeEngineCopy, prettySkill, proficiencyLabel, visualState } from "@/lib/status";
import { StatusBadge } from "@/components/ui/StatusBadge";

export function Blockers() {
  const { gaps, activePath } = useIntelligence();

  const waitingResources = (activePath?.items ?? []).filter((item) => waitKindLabel(item) !== null);
  const gapBlockers = [...gaps]
    .filter((item) => item.attainment !== "TARGET_MET" && item.action_priority > 0)
    .sort((a, b) => b.action_priority - a.action_priority)
    .slice(0, 5);

  return (
    <div className="space-y-10">
      <div>
        <ScreenKicker verb="DIAGNOSE">Blockers</ScreenKicker>
        <h1 className="mt-3 font-display text-4xl font-medium text-paper">What is blocking your path</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-mist">
          Each blocked resource is waiting on a prerequisite skill state from the backend — not a score,
          not a guess.
        </p>
      </div>

      {waitingResources.length ? (
        <section className="space-y-4">
          <p className="text-[11px] uppercase tracking-[0.16em] text-mist">Blocked resources</p>
          <div className="divide-y divide-line border-y border-line">
            {waitingResources.map((item) => (
              <div key={`${item.position}-${item.resource}`} className="py-6">
                <ResourceBlockerCard item={item} gaps={gaps} />
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section>
        <p className="text-[11px] uppercase tracking-[0.16em] text-mist">Career blockers by priority</p>
        {!gapBlockers.length && !waitingResources.length ? (
          <EmptyState
            title="No blockers diagnosed"
            body="PathFinder has not identified any competency gaps or blocked resources for this role yet."
          />
        ) : null}
        <div className="divide-y divide-line border-y border-line">
          {gapBlockers.map((item) => (
            <article key={item.skill} className="grid gap-4 py-6 md:grid-cols-[1.2fr_0.8fr]">
              <div>
                <div className="flex items-start justify-between gap-3">
                  <h2 className="text-lg text-paper">{item.name || prettySkill(item.skill)}</h2>
                  <div className="flex items-center gap-2">
                    {item.conflict ? (
                      <span className="conflict-pill" data-testid={`conflict-pill-${item.skill}`}>
                        CONFLICT
                      </span>
                    ) : null}
                    <StatusBadge state={visualState(item)} />
                  </div>
                </div>
                <p className="mt-2 font-mono text-sm tabular-nums text-mist">
                  {item.evidence_state === "UNKNOWN"
                    ? "Evidence required"
                    : item.conflict && item.proficiency !== null
                      ? `Fused ${item.proficiency.toFixed(2)} · target ${item.target_level.toFixed(2)}`
                      : `${proficiencyLabel(item)} → ${item.target_level.toFixed(2)}`}
                </p>
                <p className="mt-4 text-xs leading-relaxed text-mist">{humanizeEngineCopy(item.explanation)}</p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-wider text-mist">Required action</p>
                <p className="mt-1 text-sm text-paper">{item.action}</p>
                <p className="mt-4 text-[11px] uppercase tracking-wider text-mist">Downstream impact</p>
                <p className="mt-1 text-sm text-paper">
                  {item.hard_downstream.slice(0, 4).map(prettySkill).join(", ") || "—"}
                </p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
