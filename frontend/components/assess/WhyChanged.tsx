"use client";

import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { useIntelligence } from "@/lib/session";
import { prettySkill } from "@/lib/status";

export function WhyChanged() {
  const { attempt, diff, beforeGaps, gaps, previousPath, activePath, setView } = useIntelligence();
  const skill = attempt?.skill_results[0]?.skill;
  const before = beforeGaps.find((item) => item.skill === skill);
  const after = gaps.find((item) => item.skill === skill);
  const added = (diff?.added ?? []).find((item) => item.skill === skill);
  const blocked = diff?.blocked ?? [];
  const frozen = (activePath?.items || []).filter((item) => item.status === "COMPLETED");

  const statements = [
    skill && before
      ? `${prettySkill(skill)} was previously ${before.evidence_state === "UNKNOWN" ? "UNKNOWN" : before.attainment}.`
      : null,
    attempt
      ? `Your assessment produced new evidence (observed ${attempt.skill_results[0]?.observed_level.toFixed(2) ?? "—"}).`
      : null,
    after
      ? `The new evidence placed ${prettySkill(after.skill)} at ${after.attainment} versus the ${prettySkill(after.skill)} target of ${after.target_level.toFixed(2)}.`
      : null,
    added?.reason ?? null,
    blocked[0]
      ? `${blocked[0].title} was delayed. ${blocked[0].reason}`
      : null,
    frozen[0]
      ? `Completed work such as ${frozen[0].title} was preserved from V${previousPath?.version ?? 1} into V${activePath?.version ?? 2}.`
      : null,
  ].filter(Boolean) as string[];

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-accent">Causality</p>
        <h1 className="mt-2 text-3xl font-medium text-paper">Why did it change?</h1>
      </div>
      <Panel className="p-6">
        <ol className="space-y-4">
          {statements.map((line) => (
            <li key={line} className="text-sm leading-relaxed text-paper">
              {line}
            </li>
          ))}
        </ol>
        <p className="mt-6 text-xs text-mist">
          Every statement is taken from stored backend state, the assessment result, or PathDiff.
          PathFinder does not invent career advice.
        </p>
      </Panel>
      <div className="flex justify-end">
        <Button onClick={() => setView("history")}>Continue</Button>
      </div>
    </div>
  );
}
