"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Mark } from "@/components/ui/Mark";
import { MIN_RESOLVE_MS, withMinimumDuration } from "@/lib/motion";
import type { GoalIntake } from "@/lib/types";

type Phase =
  | "idle"
  | "reading"
  | "matching"
  | "resolved"
  | "ambiguous"
  | "unsupported"
  | "error";

type Props = {
  goalText: string;
  onGoalTextChange: (value: string) => void;
  busy: boolean;
  onResolve: () => Promise<GoalIntake>;
  onManual: () => void;
  resolvedIntake: GoalIntake | null;
  onContinueFromResolution: () => void;
  onSelectAmbiguousRole: (slug: string) => void;
  onSeeSupportedCareers: () => void;
};

function phaseFromResult(result: GoalIntake): Phase {
  if (result.resolution_status === "RESOLVED" && result.role) return "resolved";
  if (result.resolution_status === "AMBIGUOUS") return "ambiguous";
  return "unsupported";
}

export function GoalIntelligenceField({
  goalText,
  onGoalTextChange,
  busy,
  onResolve,
  onManual,
  resolvedIntake,
  onContinueFromResolution,
  onSelectAmbiguousRole,
  onSeeSupportedCareers,
}: Props) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [focused, setFocused] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [activeIntake, setActiveIntake] = useState<GoalIntake | null>(null);

  const displayIntake = activeIntake ?? resolvedIntake;

  const inputLocked = busy || phase === "reading" || phase === "matching";
  const showInput =
    phase === "idle" ||
    phase === "error" ||
    phase === "reading" ||
    phase === "matching";

  async function handleResolve() {
    if (inputLocked) return;
    if (goalText.trim().length < 3) {
      setValidationError("Please describe your goal in at least a few words.");
      return;
    }
    setValidationError(null);
    const started = Date.now();
    setPhase("reading");
    try {
      const result = await withMinimumDuration(started, onResolve());
      setActiveIntake(result);
      setPhase("matching");
      await new Promise((r) =>
        window.setTimeout(r, Math.max(0, MIN_RESOLVE_MS * 0.35 - (Date.now() - started))),
      );
      setPhase(phaseFromResult(result));
    } catch {
      setPhase("error");
    }
  }

  function handleEditGoal() {
    setActiveIntake(null);
    setPhase("idle");
  }

  return (
    <div className={`goal-intel-field ${focused ? "is-focused" : ""} ${phase !== "idle" ? `phase-${phase}` : ""}`}>
      <p className="goal-intel-kicker">What are you trying to become?</p>

      {showInput ? (
        <>
          <textarea
            className="goal-intel-input"
            placeholder="I want to become a machine learning engineer focused on computer vision…"
            value={goalText}
            onChange={(event) => {
              onGoalTextChange(event.target.value);
              if (validationError) setValidationError(null);
            }}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            disabled={inputLocked}
          />
          <p className="goal-intel-hint">Describe the career you want in your own words.</p>
          {validationError ? (
            <p className="goal-intel-error" role="alert">
              {validationError}
            </p>
          ) : null}
          {phase === "error" ? (
            <p className="goal-intel-error" role="alert">
              Goal interpretation did not complete. You can try again or pick a career manually.
            </p>
          ) : null}
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
              disabled={inputLocked}
              onClick={() => void handleResolve()}
            >
              {inputLocked ? "Resolving…" : "Resolve goal"}
            </Button>
            <Button
              variant="ghost"
              disabled={phase === "reading" || phase === "matching"}
              onClick={() => {
                setValidationError(null);
                onManual();
              }}
            >
              Pick career manually
            </Button>
          </div>
        </>
      ) : null}

      {phase === "resolved" && displayIntake?.role ? (
        <div className="goal-resolved-card">
          <p className="goal-resolved-kicker">Goal understood</p>
          <p className="goal-resolved-role">{displayIntake.role.name}</p>
          {displayIntake.focus_mentions?.length ? (
            <p className="goal-intel-focus">
              Focus: {displayIntake.focus_mentions.join(", ")}
            </p>
          ) : null}
          <p className="goal-intel-match-note">Matched to PathFinder&apos;s supported career ontology.</p>
          <dl className="goal-resolved-meta">
            <div>
              <dt>Role fit</dt>
              <dd>Canonical career ontology</dd>
            </div>
            {displayIntake.role.how ? (
              <div>
                <dt>Match</dt>
                <dd>{displayIntake.role.how}</dd>
              </div>
            ) : null}
          </dl>
          <Button className="mt-4" onClick={onContinueFromResolution}>
            Continue
          </Button>
        </div>
      ) : null}

      {phase === "ambiguous" && displayIntake ? (
        <div className="goal-ambiguous-card">
          <p className="goal-resolved-kicker">Which route fits your goal?</p>
          <p className="goal-intel-match-note">
            Your goal could fit more than one PathFinder route. Choose the career that best matches what you want.
          </p>
          <ul className="goal-candidate-list">
            {displayIntake.role_alternatives.map((item) => (
              <li key={item.slug}>
                <button
                  type="button"
                  className="goal-candidate-row"
                  onClick={() => onSelectAmbiguousRole(item.slug)}
                >
                  <span className="goal-candidate-name">{item.name}</span>
                  <span className="goal-candidate-action">Select</span>
                </button>
              </li>
            ))}
          </ul>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="ghost" onClick={handleEditGoal}>
              Edit goal
            </Button>
            <Button variant="ghost" onClick={onManual}>
              Pick career manually
            </Button>
          </div>
        </div>
      ) : null}

      {phase === "unsupported" && displayIntake ? (
        <div className="goal-unsupported-card">
          <p className="goal-resolved-kicker">Goal not mapped yet</p>
          <p className="goal-unsupported-copy">
            We couldn&apos;t map that goal to one of PathFinder&apos;s current career routes.
            {displayIntake.unresolved.length
              ? ` Unrecognized: ${displayIntake.unresolved.join(", ")}.`
              : ""}
          </p>
          <p className="goal-intel-preserved">Your text is preserved — you can edit it or choose from supported careers.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button onClick={onSeeSupportedCareers}>See supported careers</Button>
            <Button variant="ghost" onClick={handleEditGoal}>
              Edit goal
            </Button>
            <Button variant="ghost" onClick={onManual}>
              Pick career manually
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
