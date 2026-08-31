"use client";

import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/States";
import { Mark, ScreenKicker } from "@/components/ui/Mark";
import { useIntelligence } from "@/lib/session";
import { prettySkill, visualState, humanizeEngineCopy } from "@/lib/status";

export function ProveIt() {
  const { suggested, gaps, loadAssessment, mutating } = useIntelligence();
  const cover = suggested?.covers[0];
  const gap = gaps.find((item) => item.skill === cover) ?? gaps.find((item) => item.action === "VERIFY");

  if (!suggested?.assessment) {
    return (
      <EmptyState
        title="No unverified skills require a gate right now"
        body={humanizeEngineCopy(suggested?.reason || "The backend did not suggest an assessment.")}
      />
    );
  }

  return (
    <div className="prove-instrument mx-auto max-w-xl space-y-10">
      <div>
        <ScreenKicker verb="PROVE">Skill check</ScreenKicker>
        <h1 className="prove-title mt-3 font-display text-paper">Skill under evaluation</h1>
        <p className="mt-3 text-sm text-mist">Some of your skills are still unverified.</p>
      </div>
      <div className="prove-panel">
        <p className="text-xs uppercase tracking-wider text-mist">{suggested.title}</p>
        <h2 className="prove-skill mt-2 font-display text-paper">{prettySkill(cover || suggested.assessment)}</h2>
        <div className="mt-4">
          {gap ? <StatusBadge state={visualState(gap)} /> : <StatusBadge state="UNKNOWN" />}
        </div>
        <p className="mt-4 text-sm text-mist">{humanizeEngineCopy(suggested.reason)}</p>
        <p className="mt-2 text-sm text-paper">Prove what you know.</p>
        <Button
          className="cta-go mt-6 w-full justify-between py-3.5"
          disabled={mutating}
          onClick={() => void loadAssessment(suggested.assessment!)}
        >
          <span>Prove this skill</span>
          <span className="mark-arrow inline-flex" aria-hidden>
            <Mark className="h-3 w-[18px]" />
          </span>
        </Button>
        <p className="mt-3 text-center text-xs text-mist">
          {suggested.question_count} questions · loaded from the live assessment API
        </p>
      </div>
    </div>
  );
}
