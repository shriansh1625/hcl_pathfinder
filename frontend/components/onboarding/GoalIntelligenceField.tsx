"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Mark } from "@/components/ui/Mark";
import { MIN_RESOLVE_MS, withMinimumDuration } from "@/lib/motion";
import type { GoalIntake } from "@/lib/types";

type Phase = "idle" | "reading" | "matching" | "resolved";

type Props = {
  goalText: string;
  onGoalTextChange: (value: string) => void;
  busy: boolean;
  onResolve: () => Promise<GoalIntake>;
  onManual: () => void;
  resolvedIntake: GoalIntake | null;
  onContinueFromResolution: () => void;
};

export function GoalIntelligenceField({
  goalText,
  onGoalTextChange,
  busy,
  onResolve,
  onManual,
  resolvedIntake,
  onContinueFromResolution,
}: Props) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (!resolvedIntake) setPhase("idle");
  }, [resolvedIntake]);

  async function handleResolve() {
    if (goalText.trim().length < 3 || busy) return;
    const started = Date.now();
    setPhase("reading");
    try {
      const result = await withMinimumDuration(started, onResolve());
      setPhase("matching");
      await new Promise((r) => window.setTimeout(r, Math.max(0, MIN_RESOLVE_MS * 0.35 - (Date.now() - started))));
      setPhase("resolved");
      void result;
    } catch {
      setPhase("idle");
    }
  }

  const showResolved = phase === "resolved" && resolvedIntake?.role;

  return (
    <div className={`goal-intel-field ${focused ? "is-focused" : ""} ${phase !== "idle" ? `phase-${phase}` : ""}`}>
      <p className="goal-intel-kicker">Your goal</p>
      {!showResolved ? (
        <>
          <textarea
            className="goal-intel-input"
            placeholder="I want to become a machine learning engineer focused on computer vision…"
            value={goalText}
            onChange={(event) => onGoalTextChange(event.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            disabled={busy || phase === "reading" || phase === "matching"}
          />
          <p className="goal-intel-hint">Describe the career you want in your own words.</p>
          {phase === "reading" || phase === "matching" ? (
            <div className="goal-resolve-status" role="status" aria-live="polite">
              <Mark className="goal-resolve-mark h-3 w-[18px] text-accent/80" />
              <p className="goal-resolve-label">
                {phase === "reading" ? "Reading your goal" : "Matching your goal to the career graph"}
              </p>
            </div>
          ) : null}
          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              className={phase === "reading" ? "btn-compress" : ""}
              disabled={busy || goalText.trim().length < 3 || phase !== "idle"}
              onClick={() => void handleResolve()}
            >
              {phase === "reading" || phase === "matching" ? "Resolving…" : "Resolve goal"}
            </Button>
            <Button variant="ghost" disabled={busy} onClick={onManual}>
              Pick career manually
            </Button>
          </div>
        </>
      ) : (
        <div className="goal-resolved-card">
          <p className="goal-resolved-kicker">Destination found</p>
          <p className="goal-resolved-role">{resolvedIntake!.role!.name}</p>
          <dl className="goal-resolved-meta">
            <div>
              <dt>Role fit</dt>
              <dd>Canonical career ontology</dd>
            </div>
            {resolvedIntake!.role!.how ? (
              <div>
                <dt>Match</dt>
                <dd>{resolvedIntake!.role!.how}</dd>
              </div>
            ) : null}
          </dl>
          <Button className="mt-4" onClick={onContinueFromResolution}>
            Continue
          </Button>
        </div>
      )}
    </div>
  );
}
