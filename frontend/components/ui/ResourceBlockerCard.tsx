"use client";

import {
  blockerStateLine,
  primaryBlocker,
  requiredActionForBlocker,
  waitKindLabel,
} from "@/lib/blockers";
import { prettySkill } from "@/lib/status";
import type { GapItem, PathItem, PrerequisiteRow } from "@/lib/types";

function whyLabel(blocker: PrerequisiteRow): string {
  if (blocker.state === "UNKNOWN") return `Requires ${prettySkill(blocker.skill)}`;
  return `${prettySkill(blocker.skill)} prerequisite`;
}

function actionLabel(blocker: PrerequisiteRow, gaps: GapItem[]): string {
  const action = requiredActionForBlocker(blocker, gaps);
  return `${action} ${prettySkill(blocker.skill)}`;
}

export function ResourceBlockerCard({ item, gaps }: { item: PathItem; gaps: GapItem[] }) {
  const blocker = primaryBlocker(item);
  const wait = waitKindLabel(item);
  const gap = blocker ? gaps.find((row) => row.skill === blocker.skill) : null;

  return (
    <article className="resource-blocker-card" data-testid="resource-blocker-card">
      <Field label="What is blocked?" value={item.title || item.resource} />
      <Field label="Why?" value={blocker ? whyLabel(blocker) : item.explanation || "—"} />
      <Field
        label="Current state"
        value={
          blocker
            ? `${prettySkill(blocker.skill)}\n${blockerStateLine(blocker, gap)}`
            : "—"
        }
      />
      <Field
        label="What must happen?"
        value={blocker ? actionLabel(blocker, gaps) : "—"}
      />
      <Field label="Status" value={wait ?? "WAITING"} />
    </article>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="resource-blocker-field">
      <p className="resource-blocker-label">{label}</p>
      <p className="resource-blocker-value whitespace-pre-line">{value}</p>
    </div>
  );
}
