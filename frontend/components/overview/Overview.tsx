"use client";

import { StatusBadge } from "@/components/ui/StatusBadge";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { EmptyState, LoadingState } from "@/components/ui/States";
import { useIntelligence } from "@/lib/session";
import { FOCUS_SKILLS, isUnknown, prettySkill, proficiencyLabel, visualState } from "@/lib/status";
import { Button } from "@/components/ui/Button";

export function Overview() {
  const { gaps, roleName, weeklyHours, loading, setView } = useIntelligence();
  const focus = FOCUS_SKILLS.map((skill) => gaps.find((item) => item.skill === skill)).filter(Boolean);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-accent">Career target</p>
        <h1 className="mt-2 text-3xl font-medium text-paper">{roleName}</h1>
        <p className="mt-1 font-mono text-sm text-mist">{weeklyHours} hrs / week</p>
      </div>

      <Panel>
        <PanelHeader kicker="Evidence" title="Your competency state" />
        <div className="divide-y divide-line">
          {loading && !gaps.length ? <div className="p-5"><LoadingState /></div> : null}
          {!loading && !focus.length ? (
            <div className="p-5">
              <EmptyState title="No competency profile yet" body="Create a path to diagnose the learner-to-career gap." />
            </div>
          ) : null}
          {focus.map((item) => {
            if (!item) return null;
            const unknown = isUnknown(item);
            return (
              <div key={item.skill} className="grid grid-cols-[1fr_auto_auto] items-center gap-4 px-5 py-4">
                <div>
                  <p className="text-sm text-paper">{item.name || prettySkill(item.skill)}</p>
                  <p className="mt-1 text-xs text-mist">
                    {unknown
                      ? "Evidence required. UNKNOWN is not a score of zero."
                      : `Target ${item.target_level.toFixed(2)} · ${item.action}`}
                  </p>
                </div>
                <p className="font-mono text-lg text-paper" data-testid={`proficiency-${item.skill}`}>
                  {proficiencyLabel(item)}
                </p>
                <StatusBadge state={visualState(item)} />
              </div>
            );
          })}
        </div>
      </Panel>

      <div className="flex justify-end">
        <Button onClick={() => setView("blockers")}>Continue</Button>
      </div>
    </div>
  );
}
