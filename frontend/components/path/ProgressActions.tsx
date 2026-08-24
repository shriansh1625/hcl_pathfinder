"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/States";
import { Mark } from "@/components/ui/Mark";
import { waitKindLabel } from "@/lib/blockers";
import { useIntelligence } from "@/lib/session";
import { prettySkill } from "@/lib/status";
import type { PathItem, ProgressFeedback, ProgressOutcome } from "@/lib/types";

export function canShowProgressActions(item: PathItem): boolean {
  if (waitKindLabel(item)) return false;
  if (item.status === "COMPLETED") return false;
  return item.executable && item.kind === "EXECUTABLE";
}

export function isFrozenPathItem(item: PathItem): boolean {
  return item.status === "COMPLETED";
}

type ProgressActionsProps = {
  item: PathItem;
  pathId: string;
};

export function ProgressActions({ item, pathId }: ProgressActionsProps) {
  const { recordProgress, updatingModel, setView, progressFeedback, progressFeedbackTarget, clearProgressFeedback } =
    useIntelligence();
  const [mode, setMode] = useState<ProgressOutcome | null>(null);
  const [confidence, setConfidence] = useState(0.65);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const matchedFeedback =
    progressFeedback &&
    progressFeedbackTarget?.position === item.position &&
    progressFeedbackTarget.targetSkill === item.target_skill
      ? progressFeedback
      : null;

  async function submit(outcome: ProgressOutcome, selfLevel?: number | null) {
    setSubmitError(null);
    try {
      await recordProgress(pathId, item.position, outcome, selfLevel);
      setMode(null);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Progress feedback failed");
    }
  }

  if (submitError) {
    return (
      <div className="progress-surface max-w-full" data-testid="progress-error">
        <ErrorState
          message={submitError}
          context="Progress was not recorded. Your competency model and path are unchanged."
          onRetry={() => setSubmitError(null)}
        />
      </div>
    );
  }

  if (matchedFeedback) {
    return (
      <div className="progress-surface max-w-full" data-testid="progress-result">
        <ProgressResult
          result={matchedFeedback}
          onSeeChanged={() => setView("changed")}
          onDismiss={clearProgressFeedback}
        />
      </div>
    );
  }

  if (isFrozenPathItem(item)) {
    return (
      <div className="progress-frozen max-w-full" data-testid="progress-frozen">
        <p className="progress-kicker">Frozen work</p>
        <p className="mt-1 text-xs leading-relaxed text-mist">
          This step is complete on your path record. Completed work stays frozen when the path adapts.
        </p>
      </div>
    );
  }

  if (mode === "COMPLETED" || mode === "STRUGGLED") {
    return (
      <div className="progress-surface is-active max-w-full" data-testid="progress-confidence">
        <p className="progress-kicker">Evidence, not a shortcut</p>
        <p className="mt-1 text-xs text-mist">
          Your report enters the competency model as PROGRESS evidence — weighted below assessments.
        </p>
        <label htmlFor={`progress-level-${item.position}`} className="progress-confidence-label">
          How confident are you now?
        </label>
        <div className="progress-slider-row progress-slider-track-glow">
          <span className="font-mono text-[10px] tabular-nums text-mist">0.00</span>
          <input
            id={`progress-level-${item.position}`}
            type="range"
            min={0}
            max={100}
            step={5}
            value={Math.round(confidence * 100)}
            onChange={(event) => setConfidence(Number(event.target.value) / 100)}
            className="progress-slider"
            aria-valuemin={0}
            aria-valuemax={1}
            aria-valuenow={confidence}
            aria-valuetext={`${confidence.toFixed(2)} confidence`}
          />
          <span className="font-mono text-[10px] tabular-nums text-mist">1.00</span>
        </div>
        <p className="font-mono text-xs tabular-nums text-paper" aria-live="polite">
          {confidence.toFixed(2)}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {updatingModel ? (
            <p className="progress-updating" role="status">
              <Mark className="progress-updating-mark h-2.5 w-4 text-accent/80" />
              Updating competency model…
            </p>
          ) : (
            <>
              <Button onClick={() => void submit(mode, confidence)}>Submit progress</Button>
              <Button variant="ghost" onClick={() => setMode(null)}>
                Cancel
              </Button>
            </>
          )}
        </div>
      </div>
    );
  }

  if (!canShowProgressActions(item)) {
    return null;
  }

  return (
    <div className="progress-surface max-w-full" data-testid="progress-actions">
      <p className="progress-kicker">Report progress on {prettySkill(item.target_skill)}</p>
      <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label="Progress outcome">
        <Button
          variant="secondary"
          className="px-3 py-1.5 text-xs"
          disabled={updatingModel}
          onClick={() => setMode("COMPLETED")}
        >
          Complete
        </Button>
        <Button
          variant="secondary"
          className="px-3 py-1.5 text-xs"
          disabled={updatingModel}
          onClick={() => setMode("STRUGGLED")}
        >
          I struggled
        </Button>
        <Button
          variant="ghost"
          className="px-3 py-1.5 text-xs"
          disabled={updatingModel}
          onClick={() => void submit("SKIPPED", null)}
        >
          Skip
        </Button>
      </div>
    </div>
  );
}

function ProgressResult({
  result,
  onSeeChanged,
  onDismiss,
}: {
  result: ProgressFeedback;
  onSeeChanged: () => void;
  onDismiss: () => void;
}) {
  if (result.adaptation === "NO_ACTIVE_PATH") {
    return (
      <ErrorState
        message="No active path is available to re-plan."
        context="Progress was recorded but the server could not attach it to an active path."
      />
    );
  }

  if (result.adaptation === "CREATED") {
    return (
      <div data-testid="progress-result-created">
        <ol className="progress-chain" aria-label="Adaptation sequence">
          <li>Progress recorded</li>
          <li>Competency updated</li>
          <li>Path changed</li>
        </ol>
        <p className="mt-3 text-xs leading-relaxed text-paper">{result.summary}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant="secondary" onClick={onSeeChanged}>
            See what changed
          </Button>
          <Button variant="ghost" onClick={onDismiss}>
            Dismiss
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="progress-result-stable">
      <p className="progress-kicker">Progress recorded</p>
      <p className="mt-2 text-xs leading-relaxed text-paper">
        Your progress was recorded. Your current path did not need to change.
      </p>
      {result.summary ? <p className="mt-2 text-xs text-mist">{result.summary}</p> : null}
      <Button variant="ghost" className="mt-3" onClick={onDismiss}>
        Dismiss
      </Button>
    </div>
  );
}
