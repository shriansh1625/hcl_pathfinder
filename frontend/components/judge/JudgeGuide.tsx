"use client";

import { useMemo } from "react";
import { useIntelligence } from "@/lib/session";
import { prettySkill, displayAttainment, humanizeEngineCopy } from "@/lib/status";
import type { ViewId } from "@/lib/types";

const STEPS: { id: string; label: string; views: ViewId[] }[] = [
  { id: "diagnose", label: "Diagnose", views: ["overview", "blockers"] },
  { id: "path", label: "Path V1", views: ["path"] },
  { id: "prove", label: "Prove It", views: ["prove"] },
  { id: "assess", label: "Assess", views: ["assess"] },
  { id: "result", label: "Result", views: ["result"] },
  { id: "changed", label: "Path V2", views: ["changed"] },
  { id: "why", label: "Why", views: ["why"] },
  { id: "history", label: "History", views: ["history"] },
  { id: "map", label: "Skill map", views: ["map"] },
];

function stepIndex(view: ViewId): number {
  return STEPS.findIndex((step) => step.views.includes(view));
}

function contextFor(
  view: ViewId,
  opts: {
    roleName: string;
    attempt: ReturnType<typeof useIntelligence>["attempt"];
    suggested: ReturnType<typeof useIntelligence>["suggested"];
    gaps: ReturnType<typeof useIntelligence>["gaps"];
  },
): { learned: string; changed: string; next: string } {
  const skill = opts.attempt?.skill_results[0]?.skill;
  const pretty = skill ? prettySkill(skill) : opts.suggested?.covers[0] ? prettySkill(opts.suggested.covers[0]) : "the target skill";
  const before = opts.gaps.find((row) => row.skill === skill);

  switch (view) {
    case "overview":
    case "blockers":
      return {
        learned: `Diagnosed competency vs ${opts.roleName}.`,
        changed: "Gaps and blockers come from stored evidence.",
        next: "Review your path — one item should already be completed.",
      };
    case "path":
      return {
        learned: "Path V1 sequenced from diagnosis and prerequisites.",
        changed: "Completed work is anchored; blocked resources show why they wait.",
        next: `Prove ${pretty} to add new evidence.`,
      };
    case "prove":
      return {
        learned: humanizeEngineCopy(opts.suggested?.reason || "Assessment targets skills that still have no evidence."),
        changed: "No adaptation until evidence is submitted.",
        next: "Take the live assessment — questions come from the backend.",
      };
    case "assess":
      return {
        learned: "Assessment responses will become evidence rows.",
        changed: "Scoring, fusion, and adaptation run on the backend.",
        next: "Submit to update diagnosis and possibly the path.",
      };
    case "result":
      return {
        learned: skill
          ? `New evidence for ${pretty}: observed ${opts.attempt?.skill_results[0]?.observed_level.toFixed(2) ?? "—"}.`
          : "Assessment result stored.",
        changed: before
          ? `${pretty} moved from ${displayAttainment(before)} toward updated diagnosis.`
          : "Competency profile updated.",
        next: opts.attempt ? "Inspect PATH CHANGED — same objects, new plan." : "Submit the assessment to record evidence first.",
      };
    case "changed":
      return {
        learned: "Adaptation preserved completed items.",
        changed: "Remediation entered; downstream items may have moved.",
        next: "Open Why this changed for the causal trace.",
      };
    case "why":
      return {
        learned: "Every statement maps to backend state.",
        changed: "Evidence → diagnosis → action → path change.",
        next: "Ask PathFinder to explain the change, then open GROUNDED IN.",
      };
    case "history":
      return {
        learned: "Path versions are immutable.",
        changed: "Only one path remains ACTIVE.",
        next: "Explore Skill Map to see dependency relationships.",
      };
    case "map":
      return {
        learned: "Skill dependencies show what blocks what.",
        changed: "Neighborhood view highlights HARD and SOFT links.",
        next: "Reset to start another learner demo.",
      };
    default:
      return {
        learned: "PathFinder uses evidence, not guesses.",
        changed: "—",
        next: "Continue the flow.",
      };
  }
}

export function JudgeGuide() {
  const { judgeMode, view, setView, roleName, attempt, suggested, gaps } = useIntelligence();
  const active = stepIndex(view);
  const next = active >= 0 && active < STEPS.length - 1 ? STEPS[active + 1] : null;
  const context = useMemo(
    () => contextFor(view, { roleName, attempt, suggested, gaps }),
    [view, roleName, attempt, suggested, gaps],
  );

  if (!judgeMode) return null;

  return (
    <header className="judge-rail" data-testid="judge-guide" aria-label="Judge demo context">
      <div className="judge-rail-top">
        <p className="judge-rail-where">
          {STEPS[active]?.label ?? "Workspace"} · {view.replaceAll("_", " ")}
        </p>
        <div className="judge-rail-progress" aria-hidden>
          {STEPS.map((step, index) => (
            <span key={step.id} className={index <= active ? "is-on" : ""} />
          ))}
        </div>
      </div>
      <dl className="judge-rail-context">
        <div>
          <dt>Where you are</dt>
          <dd>{STEPS[active]?.label ?? "Workspace"}</dd>
        </div>
        <div>
          <dt>What PathFinder learned</dt>
          <dd>{context.learned}</dd>
        </div>
        <div>
          <dt>What changed</dt>
          <dd>{context.changed}</dd>
        </div>
        <div>
          <dt>Look next</dt>
          <dd>
            {next && !(view === "assess" && !attempt) ? (
              <button type="button" className="judge-rail-next" onClick={() => setView(next.views[0])}>
                {context.next}
              </button>
            ) : (
              context.next
            )}
          </dd>
        </div>
      </dl>
    </header>
  );
}
