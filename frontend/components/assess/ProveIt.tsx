"use client";

import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/States";
import { useIntelligence } from "@/lib/session";
import { prettySkill, visualState } from "@/lib/status";

export function ProveIt() {
  const { suggested, gaps, loadAssessment, mutating } = useIntelligence();
  const cover = suggested?.covers[0];
  const gap = gaps.find((item) => item.skill === cover) ?? gaps.find((item) => item.action === "VERIFY");

  if (!suggested?.assessment) {
    return (
      <EmptyState
        title="No unverified skills require a gate right now"
        body={suggested?.reason || "The backend did not suggest an assessment."}
      />
    );
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-accent">Prove it</p>
        <h1 className="mt-2 text-3xl font-medium text-paper">Some of your skills are still unverified.</h1>
      </div>
      <Panel className="p-6">
        <p className="text-xs uppercase tracking-wider text-mist">{suggested.title}</p>
        <h2 className="mt-2 text-2xl text-paper">{prettySkill(cover || suggested.assessment)}</h2>
        <div className="mt-4">
          {gap ? <StatusBadge state={visualState(gap)} /> : <StatusBadge state="UNKNOWN" />}
        </div>
        <p className="mt-4 text-sm text-mist">{suggested.reason}</p>
        <p className="mt-2 text-sm text-paper">Prove what you know.</p>
        <Button
          className="mt-6 w-full py-3"
          disabled={mutating}
          onClick={() => void loadAssessment(suggested.assessment!)}
        >
          Take assessment
        </Button>
        <p className="mt-3 text-center text-xs text-mist">
          {suggested.question_count} questions · loaded from the live assessment API
        </p>
      </Panel>
    </div>
  );
}
