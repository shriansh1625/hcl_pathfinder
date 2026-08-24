"use client";



import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";

import { StatusBadge } from "@/components/ui/StatusBadge";

import { Mark, ScreenKicker } from "@/components/ui/Mark";

import { useIntelligence } from "@/lib/session";

import { prefersReducedMotion } from "@/lib/motion";

import { prettySkill, visualState } from "@/lib/status";



const PHASE_LABELS = [

  "New evidence recorded",

  "Skill state transition",

  "Gap status updated",

  "Ready to inspect path change",

] as const;



export function ResultView() {

  const { attempt, gaps, beforeGaps, setView } = useIntelligence();

  const [phase, setPhase] = useState(0);

  const [skipped, setSkipped] = useState(false);



  useEffect(() => {

    setPhase(0);

    setSkipped(false);

    if (prefersReducedMotion()) {

      setPhase(PHASE_LABELS.length - 1);

      return;

    }

    const timers = PHASE_LABELS.map((_, index) =>

      window.setTimeout(() => setPhase(index), index * 320),

    );

    return () => timers.forEach((timer) => window.clearTimeout(timer));

  }, [attempt?.attempt_id]);



  if (!attempt) {

    return <p className="text-sm text-mist">No assessment result yet.</p>;

  }



  const primary = attempt.skill_results[0];

  const after = gaps.find((item) => item.skill === primary?.skill);

  const before = beforeGaps.find((item) => item.skill === primary?.skill);

  const showTransition = phase >= 1;

  const showMetrics = phase >= 2;

  const showCta = phase >= 3 || skipped;



  return (

    <div className="adapt-hero mx-auto max-w-xl space-y-8" data-testid="result-hero">

      <div className="adapt-hero-pulse">

        <ScreenKicker verb="PROVE">New evidence</ScreenKicker>

        <h1 className="mt-3 font-display text-4xl font-medium text-paper">

          {phase === 0 ? "Something happened." : prettySkill(primary?.skill || attempt.assessment)}

        </h1>

        <p className="mt-3 text-sm text-mist">{PHASE_LABELS[Math.min(phase, PHASE_LABELS.length - 1)]}</p>

      </div>



      {!skipped && phase < PHASE_LABELS.length - 1 ? (

        <button type="button" className="adapt-skip text-xs text-mist underline-offset-2 hover:underline" onClick={() => setSkipped(true)}>

          Skip sequence

        </button>

      ) : null}



      <div className="border-y border-line py-6">

        {showTransition ? (

          <div className="flex items-center gap-3 text-sm adapt-phase-in">

            {before ? (

              <StatusBadge

                state={visualState({

                  blocked: before.blocked,

                  evidence_state: before.evidence_state,

                  attainment: before.attainment,

                  action: before.action,

                })}

              />

            ) : null}

            <span className="text-mist">→</span>

            {after ? <StatusBadge state={visualState(after)} /> : null}

          </div>

        ) : null}

        {showMetrics ? (

          <dl className="adapt-phase-in mt-6 grid grid-cols-2 gap-4 font-mono text-sm tabular-nums">

            <div>

              <dt className="text-mist">Observed</dt>

              <dd className="mt-1 text-paper">{primary ? primary.observed_level.toFixed(2) : "—"}</dd>

            </div>

            <div>

              <dt className="text-mist">Target</dt>

              <dd className="mt-1 text-paper">{after ? after.target_level.toFixed(2) : "—"}</dd>

            </div>

            <div className="col-span-2">

              <dt className="text-mist">Action</dt>

              <dd className="mt-1 text-paper">

                {after?.action === "REMEDIATE" || after?.action === "REMEDIATE_BLOCKER"

                  ? "Remediation required"

                  : after?.action || attempt.adaptation}

              </dd>

            </div>

          </dl>

        ) : null}

      </div>



      {showCta ? (

        <Button className="cta-go adapt-phase-in w-full justify-between py-3.5" onClick={() => setView("changed")}>

          <span>See path change</span>

          <span className="mark-arrow inline-flex" aria-hidden>

            <Mark className="h-3 w-[18px]" />

          </span>

        </Button>

      ) : null}

    </div>

  );

}
