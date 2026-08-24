"use client";

import { Mark } from "@/components/ui/Mark";
import { prettySkill } from "@/lib/status";
import type { AssessmentAttempt, DiffEntry, GapItem, GapSnapshot } from "@/lib/types";

export type TraceStep = {
  label: string;
  body: string;
};

export function buildAdaptationTrace(opts: {
  attempt: AssessmentAttempt | null;
  before?: GapSnapshot | GapItem | null;
  after?: GapItem | null;
  diff?: {
    added: DiffEntry[];
    moved: DiffEntry[];
    blocked: DiffEntry[];
  } | null;
}): TraceStep[] {
  const { attempt, before, after, diff } = opts;
  const skill = attempt?.skill_results[0]?.skill ?? after?.skill ?? before?.skill;
  const observed = attempt?.skill_results[0]?.observed_level;
  const steps: TraceStep[] = [];

  if (skill && before && after) {
    const beforeLabel = before.evidence_state === "UNKNOWN" ? "UNKNOWN" : before.attainment;
    steps.push({
      label: "NEW EVIDENCE",
      body: `${prettySkill(skill)}\n${beforeLabel} → ${after.attainment}`,
    });
  }

  if (after && observed !== undefined) {
    steps.push({
      label: "DIAGNOSIS",
      body: `Target: ${after.target_level.toFixed(2)}\nObserved: ${observed.toFixed(2)}`,
    });
  }

  if (after?.action) {
    steps.push({
      label: "ACTION",
      body: after.action.replaceAll("_", " "),
    });
  }

  if (after?.downstream_impact || after?.explanation) {
    steps.push({
      label: "CONSEQUENCE",
      body: after.downstream_impact || after.explanation,
    });
  }

  const pathLines: string[] = [];
  for (const row of diff?.added ?? []) {
    pathLines.push(`+ ${row.title}`);
  }
  for (const row of diff?.moved ?? []) {
    const from = row.from_week != null ? `Week ${row.from_week}` : "unscheduled";
    const to = row.to_week != null ? `Week ${row.to_week}` : "unscheduled";
    pathLines.push(`→ ${row.title} moved ${from} → ${to}`);
  }
  for (const row of diff?.blocked ?? []) {
    pathLines.push(`⊘ ${row.title} delayed`);
  }
  if (pathLines.length) {
    steps.push({
      label: "PATH CHANGE",
      body: pathLines.join("\n"),
    });
  }

  return steps;
}

export function AdaptationTrace({ steps }: { steps: TraceStep[] }) {
  if (!steps.length) return null;
  return (
    <ol className="adapt-trace" data-testid="adaptation-trace">
      {steps.map((step, index) => (
        <li key={`${step.label}-${index}`} className="adapt-trace-step">
          <p className="adapt-trace-label">{step.label}</p>
          <p className="adapt-trace-body whitespace-pre-line">{step.body}</p>
          {index < steps.length - 1 ? (
            <span className="adapt-trace-join" aria-hidden>
              <Mark className="h-2.5 w-4 rotate-90 text-paper/35" />
            </span>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
