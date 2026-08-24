"use client";

import { Mark } from "@/components/ui/Mark";
import {
  blockerDetail,
  blockerStateLine,
  primaryBlocker,
  requiredActionForBlocker,
  waitKindLabel,
} from "@/lib/blockers";
import { prettySkill } from "@/lib/status";
import type { GapItem, PathItem } from "@/lib/types";

export function BlockerChain({
  item,
  gaps,
  compact = false,
}: {
  item: PathItem;
  gaps: GapItem[];
  compact?: boolean;
}) {
  const wait = waitKindLabel(item);
  const blocker = primaryBlocker(item);
  if (!wait || !blocker) return null;
  const gap = gaps.find((row) => row.skill === blocker.skill);
  const action = requiredActionForBlocker(blocker, gaps);

  return (
    <div className={`blocker-chain ${compact ? "blocker-chain-compact" : ""}`} data-testid="blocker-chain">
      <div className="blocker-chain-row">
        <span className="blocker-chain-label">Resource</span>
        <span className="blocker-chain-value">{item.title || item.resource}</span>
      </div>
      <div className="blocker-chain-arrow" aria-hidden>
        <Mark className="h-2.5 w-4 rotate-90 text-paper/35" />
      </div>
      <div className="blocker-chain-row">
        <span className="blocker-chain-label">Requires</span>
        <span className="blocker-chain-value">{prettySkill(blocker.skill)}</span>
      </div>
      <div className="blocker-chain-arrow" aria-hidden>
        <Mark className="h-2.5 w-4 rotate-90 text-paper/35" />
      </div>
      <div className="blocker-chain-row">
        <span className="blocker-chain-label">Current state</span>
        <span className="blocker-chain-value font-mono tabular-nums">{blockerStateLine(blocker, gap)}</span>
      </div>
      <div className="blocker-chain-arrow" aria-hidden>
        <Mark className="h-2.5 w-4 rotate-90 text-paper/35" />
      </div>
      <div className="blocker-chain-row">
        <span className="blocker-chain-label">Required action</span>
        <span className="blocker-chain-value">→ {action}</span>
      </div>
      <div className="blocker-chain-foot">
        <p className="blocker-chain-wait">{wait}</p>
        <p className="blocker-chain-detail">{blockerDetail(item, gap)}</p>
      </div>
    </div>
  );
}
