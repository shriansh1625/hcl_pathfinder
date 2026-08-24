"use client";



import { GroundedExplain } from "@/components/ai/GroundedExplain";
import { AdaptationTrace, buildAdaptationTrace } from "@/components/ui/AdaptationTrace";

import { ScreenKicker } from "@/components/ui/Mark";

import { useIntelligence } from "@/lib/session";



export function WhyChanged() {

  const { attempt, diff, beforeGaps, gaps } = useIntelligence();

  const skill = attempt?.skill_results[0]?.skill;

  const before = beforeGaps.find((item) => item.skill === skill);

  const after = gaps.find((item) => item.skill === skill);

  const steps = buildAdaptationTrace({ attempt, before, after, diff });



  return (

    <div className="mx-auto max-w-2xl space-y-10">

      <div>

        <ScreenKicker verb="ADAPT">Causality</ScreenKicker>

        <h1 className="mt-3 font-display text-4xl font-medium text-paper">Why this changed</h1>

        <p className="mt-3 text-sm text-mist">

          Evidence → diagnosis → action → path change. Every statement comes from stored backend state.

        </p>

      </div>

      <AdaptationTrace steps={steps} />

      <GroundedExplain
        intent="WHAT_CHANGED"
        skill={skill}
        triggerLabel="What changed?"
        testId="what-changed"
      />
      <GroundedExplain
        intent="NEXT_ACTION"
        triggerLabel="What should I do next?"
        testId="next-action"
      />

    </div>

  );

}
