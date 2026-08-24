"use client";

import { useState } from "react";
import { GroundedExplain } from "@/components/judge/AiSurface";
import { CompetencyRow } from "@/components/ui/CompetencyRow";
import { EvidencePanel } from "@/components/ui/EvidencePanel";
import { EmptyState, LoadingState } from "@/components/ui/States";
import { ScreenKicker } from "@/components/ui/Mark";
import { useIntelligence } from "@/lib/session";
import { FOCUS_SKILLS } from "@/lib/status";

export function Overview() {
  const { gaps, roleName, weeklyHours, learningStyle, loading, beforeGaps, skills, learnerId } = useIntelligence();
  const [inspectSkill, setInspectSkill] = useState<string | null>(null);
  const focus = FOCUS_SKILLS.map((skill) => gaps.find((item) => item.skill === skill)).filter(Boolean);
  const shifted = new Set(
    beforeGaps
      .filter((before) => {
        const after = gaps.find((item) => item.skill === before.skill);
        return after && (after.attainment !== before.attainment || after.evidence_state !== before.evidence_state);
      })
      .map((item) => item.skill),
  );

  return (
    <div className="space-y-10">
      <div>
        <ScreenKicker verb="KNOW">Competency</ScreenKicker>
        <h1 className="mt-3 font-display text-4xl font-medium text-paper">{roleName}</h1>
        <p className="mt-2 font-mono text-xs uppercase tracking-[0.14em] text-mist">
          {weeklyHours} hours / week · {learningStyle.replaceAll("_", " ")}
        </p>
      </div>

      <section>
        <p className="text-[11px] uppercase tracking-[0.18em] text-mist">Your competency state</p>
        <div className="mt-2 divide-y divide-line border-y border-line">
          {loading && !gaps.length ? <div className="py-6"><LoadingState /></div> : null}
          {!loading && !focus.length ? (
            <div className="py-6">
              <EmptyState title="No competency profile yet" body="Create a path to diagnose the learner-to-career gap." />
            </div>
          ) : null}
          {focus.map((item) =>
            item ? (
              <div key={item.skill}>
                <CompetencyRow
                  item={item}
                  transitioning={shifted.has(item.skill)}
                  onInspectEvidence={() => setInspectSkill((current) => (current === item.skill ? null : item.skill))}
                  inspecting={inspectSkill === item.skill}
                />
                {inspectSkill === item.skill ? (
                  <EvidencePanel
                    skill={item.skill}
                    fused={skills.find((row) => row.skill === item.skill) ?? null}
                    learnerId={learnerId}
                  />
                ) : null}
                {item.attainment === "GAP" || item.attainment === "NEAR_TARGET" || item.attainment === "UNKNOWN" ? (
                  <div className="pb-4">
                    <GroundedExplain
                      intent="WHY_GAP"
                      skill={item.skill}
                      triggerLabel="Why this gap?"
                      testId={`why-gap-${item.skill}`}
                    />
                  </div>
                ) : null}
              </div>
            ) : null,
          )}
        </div>
      </section>
    </div>
  );
}
