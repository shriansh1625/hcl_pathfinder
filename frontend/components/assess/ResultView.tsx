"use client";

import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useIntelligence } from "@/lib/session";
import { prettySkill, visualState } from "@/lib/status";
import type { VisualState } from "@/lib/status";

export function ResultView() {
  const { attempt, gaps, beforeGaps, setView } = useIntelligence();
  if (!attempt) {
    return <p className="text-sm text-mist">No assessment result yet.</p>;
  }
  const primary = attempt.skill_results[0];
  const after = gaps.find((item) => item.skill === primary?.skill);
  const before = beforeGaps.find((item) => item.skill === primary?.skill);
  const beforeState = (before?.evidence_state === "UNKNOWN" ? "UNKNOWN" : before?.attainment) as VisualState | undefined;

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-accent">Assessment result</p>
        <h1 className="mt-2 text-3xl font-medium text-paper">
          {prettySkill(primary?.skill || attempt.assessment)}
        </h1>
      </div>
      <Panel className="p-6">
        <div className="flex items-center gap-3 text-sm">
          {beforeState ? <StatusBadge state={beforeState === "UNKNOWN" ? "UNKNOWN" : visualState({
            blocked: before?.blocked ?? false,
            evidence_state: before?.evidence_state ?? "UNKNOWN",
            attainment: before?.attainment ?? "UNKNOWN",
            action: before?.action ?? "VERIFY",
          })} /> : null}
          <span className="text-mist">↓</span>
          {after ? <StatusBadge state={visualState(after)} /> : null}
        </div>
        <dl className="mt-6 grid grid-cols-2 gap-4 font-mono text-sm">
          <div>
            <dt className="text-mist">Observed</dt>
            <dd className="mt-1 text-paper">{primary ? primary.observed_level.toFixed(2) : "—"}</dd>
          </div>
          <div>
            <dt className="text-mist">Target</dt>
            <dd className="mt-1 text-paper">{after ? after.target_level.toFixed(2) : "—"}</dd>
          </div>
        </dl>
        <p className="mt-6 text-sm uppercase tracking-wider text-accent">
          {after?.action === "REMEDIATE" || after?.action === "REMEDIATE_BLOCKER"
            ? "Remediation required"
            : after?.action || attempt.adaptation}
        </p>
        <p className="mt-4 text-sm leading-relaxed text-mist">
          Your new evidence changes what PathFinder knows about you.
        </p>
        <Button className="mt-6 w-full py-3" onClick={() => setView("changed")}>
          See what changed
        </Button>
      </Panel>
    </div>
  );
}
