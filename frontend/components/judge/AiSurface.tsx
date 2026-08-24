"use client";

import type { AIExplainIntent } from "@/lib/types";

/** Compile-time surface for Slice 4. Full grounded AI ships in Slice 5. */
export function GroundedExplain({
  triggerLabel,
  testId,
}: {
  intent: AIExplainIntent;
  skill?: string;
  resource?: string;
  query?: string;
  triggerLabel: string;
  testId?: string;
}) {
  return (
    <button type="button" className="grounded-trigger" data-testid={testId} disabled aria-disabled="true">
      {triggerLabel}
    </button>
  );
}

export function AskPathFinder() {
  return null;
}
