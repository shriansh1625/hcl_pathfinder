"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Mark, ScreenKicker } from "@/components/ui/Mark";
import { useIntelligence } from "@/lib/session";
import { prefersReducedMotion } from "@/lib/motion";
import { prettySkill, visualState, displayAttainment } from "@/lib/status";

export function ResultView() {
  const { attempt, gaps, beforeGaps, setView } = useIntelligence();
  const [phase, setPhase] = useState(0);
  const [skipped, setSkipped] = useState(false);

  useEffect(() => {
    setPhase(0);
    setSkipped(false);
    if (prefersReducedMotion()) {
      setPhase(3);
      return;
    }
    const timers = [0, 280, 560, 840].map((delay, index) =>
      window.setTimeout(() => setPhase(index), delay),
    );
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [attempt?.attempt_id]);

  if (!attempt) {
    return <p className="text-sm text-mist">No assessment result yet.</p>;
  }

  const primary = attempt.skill_results[0];
  const after = gaps.find((item) => item.skill === primary?.skill);
  const before = beforeGaps.find((item) => item.skill === primary?.skill);
  const showEvidence = phase >= 1 || skipped;
  const showAfter = phase >= 2 || skipped;
  const showCta = phase >= 3 || skipped;
  const observed = primary ? primary.observed_level.toFixed(2) : "—";
  const target = after ? after.target_level.toFixed(2) : before ? before.target_level.toFixed(2) : "—";
  const beforeLabel = displayAttainment(before);

  return (
    <div className="result-report adapt-hero mx-auto max-w-xl space-y-8" data-testid="result-hero">
      <div className="adapt-hero-pulse">
        <ScreenKicker verb="PROVE">Evidence recorded</ScreenKicker>
        <h1 className="result-skill mt-3 font-display text-paper">{prettySkill(primary?.skill || attempt.assessment)}</h1>
        <p className="mt-3 text-sm text-mist">Assessment evidence recorded on the backend.</p>
      </div>

      {!skipped && phase < 3 ? (
        <button type="button" className="adapt-skip text-xs uppercase tracking-wider text-mist underline-offset-2 hover:underline" onClick={() => setSkipped(true)}>
          Skip
        </button>
      ) : null}

      <div className="result-chain" data-testid="result-chain">
        <div className={`result-chain-col result-before ${phase >= 0 ? "is-visible" : ""}`} data-testid="result-before">
          <p className="type-section">Before</p>
          {before ? (
            <div className="mt-3 space-y-2">
              <StatusBadge
                state={visualState({
                  blocked: before.blocked,
                  evidence_state: before.evidence_state,
                  attainment: before.attainment,
                  action: before.action,
                })}
              />
              <p className="result-before-value font-mono text-paper">{beforeLabel}</p>
            </div>
          ) : (
            <p className="mt-3 text-sm text-mist">—</p>
          )}
        </div>

        {showEvidence ? (
          <div className="result-chain-arrow adapt-phase-in" aria-hidden>
            <Mark className="h-2.5 w-4 rotate-90 text-paper/35" />
          </div>
        ) : null}

        {showEvidence ? (
          <div className="result-chain-col result-evidence adapt-phase-in" data-testid="result-evidence">
            <p className="type-section">New evidence</p>
            <p className="result-metric mt-3 font-mono tabular-nums text-paper">
              {observed} <span className="result-metric-den">/ {target}</span>
            </p>
            <p className="mt-1 text-xs text-mist">{attempt.adaptation} adaptation signal</p>
          </div>
        ) : null}

        {showAfter ? (
          <div className="result-chain-arrow adapt-phase-in" aria-hidden>
            <Mark className="h-2.5 w-4 rotate-90 text-paper/35" />
          </div>
        ) : null}

        {showAfter && after ? (
          <div className="result-chain-col result-after adapt-phase-in" data-testid="result-after">
            <p className="type-section">After</p>
            <div className="mt-3 space-y-3">
              <p className="result-after-state">{after.attainment.replaceAll("_", " ")}</p>
              <StatusBadge state={visualState(after)} />
              <dl className="result-after-dl font-mono text-sm tabular-nums">
                <div>
                  <dt className="text-mist">Action</dt>
                  <dd className="mt-1 text-paper">{after.action.replaceAll("_", " ")}</dd>
                </div>
                <div>
                  <dt className="text-mist">Target</dt>
                  <dd className="mt-1 text-paper">{after.target_level.toFixed(2)}</dd>
                </div>
              </dl>
            </div>
          </div>
        ) : null}
      </div>

      {showCta ? (
        <div className="result-consequence adapt-phase-in">
          <p className="type-section">Path consequence</p>
          <Button className="cta-go mt-4 w-full justify-between py-3.5" onClick={() => setView("changed")} data-testid="see-what-changed">
            <span>See what changed</span>
            <span className="mark-arrow inline-flex" aria-hidden>
              <Mark className="h-3 w-[18px]" />
            </span>
          </Button>
        </div>
      ) : null}
    </div>
  );
}
