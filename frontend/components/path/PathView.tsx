"use client";

import { useState } from "react";
import { BlockerChain } from "@/components/ui/BlockerChain";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/States";
import { ScreenKicker, Waypoint } from "@/components/ui/Mark";
import {
  blockerDetail,
  blockerStateLine,
  primaryBlocker,
  resourceWaitingLabel,
  waitKindLabel,
} from "@/lib/blockers";
import { GroundedExplain } from "@/components/ai/GroundedExplain";
import { ProgressActions } from "@/components/path/ProgressActions";
import { useIntelligence } from "@/lib/session";
import { breakdownRows, primaryBreakdownReason, semanticRelevanceTier } from "@/lib/score-breakdown";
import { humanizeEngineCopy, prettySkill } from "@/lib/status";
import type { PathItem } from "@/lib/types";

function BlockerExposition({ item, gaps }: { item: PathItem; gaps: ReturnType<typeof useIntelligence>["gaps"] }) {
  const wait = waitKindLabel(item);
  const blocker = primaryBlocker(item);
  if (!wait || !blocker) return null;
  const gap = gaps.find((row) => row.skill === blocker.skill);
  return (
    <div className="blocker-expo" data-testid="blocker-exposition">
      <p className="blocker-expo-wait">{wait}</p>
      <p className="blocker-expo-skill">{prettySkill(blocker.skill)}</p>
      <p className="blocker-expo-state font-mono tabular-nums">{blockerStateLine(blocker, gap)}</p>
      <p className="blocker-expo-detail">{blockerDetail(item, gap)}</p>
    </div>
  );
}

function nodeKind(item: PathItem, waiting: string | null, isCompleted: boolean, isExecutable: boolean) {
  if (isCompleted) return "frozen";
  if (item.kind === "VERIFICATION_GATE" || item.gate) return "gate";
  if (waiting === "WAITING FOR VERIFICATION") return "verify";
  if (waiting === "WAITING FOR REMEDIATION") return "remediate";
  if (isExecutable) return "executable";
  return "pending";
}

function routeArchetype(item: PathItem): "milestone" | "assessment" | "gate" | "resource" {
  if (item.kind === "VERIFICATION_GATE" || item.gate) return "gate";
  if (item.type === "ASSESSMENT" || item.intervention === "VERIFY") return "assessment";
  if (item.type === "MILESTONE" || item.intervention === "MILESTONE") return "milestone";
  return "resource";
}

function archetypeLabel(archetype: ReturnType<typeof routeArchetype>): string {
  switch (archetype) {
    case "milestone":
      return "Milestone";
    case "assessment":
      return "Assessment";
    case "gate":
      return "Gate";
    default:
      return "Resource";
  }
}

export function PathView() {
  const { activePath, roleName, gaps } = useIntelligence();
  const [open, setOpen] = useState<PathItem | null>(null);

  if (!activePath) {
    return <EmptyState title="No active path" body="Generate a path from the goal screen." />;
  }

  const grouped = new Map<number | string, PathItem[]>();
  for (const item of activePath.items) {
    const key = item.week ?? "Unscheduled";
    grouped.set(key, [...(grouped.get(key) ?? []), item]);
  }

  const currentItem = activePath.items.find((item) => item.executable && item.status !== "COMPLETED");
  const currentWeek = currentItem?.week;
  const currentPos = currentItem?.position;
  const nextItem = activePath.items.find(
    (item) => item.position > (currentPos ?? -1) && item.status !== "COMPLETED" && item.kind === "EXECUTABLE",
  );
  const completed = activePath.items.filter((item) => item.status === "COMPLETED").length;
  const blocked = activePath.items.filter((item) => waitKindLabel(item)).length;

  return (
    <div className="path-canvas" data-testid="path-canvas">
      <header className="path-canvas-head">
        <ScreenKicker verb="PATH">Version {activePath.version}</ScreenKicker>
        <h1 className="path-destination-title">Your path to {roleName}</h1>
        <p className="type-data mt-2 text-sm text-mist">
          V{activePath.version} · {activePath.status} · {activePath.total_estimated_hours ?? "—"}h
        </p>
      </header>

      <div className="path-route-legend" aria-label="Route legend" data-testid="path-route-legend">
        <span className="is-current">You are here</span>
        <span className="is-next">Next</span>
        <span className="is-blocked">Blocked · {blocked}</span>
        <span className="is-frozen">Complete · {completed}</span>
        {currentPos != null ? <span className="is-position">Step {currentPos + 1}</span> : null}
      </div>

      <div className="path-mobile-rail" data-testid="path-mobile-rail" aria-label="Route compass">
        <div className="path-mobile-rail-spine" aria-hidden>
          <span className="path-mobile-node is-you" />
          <span className="path-mobile-line" />
          <span className={`path-mobile-node ${nextItem ? "is-next" : ""}`} />
          <span className="path-mobile-line is-dim" />
          <span className={`path-mobile-node ${blocked ? "is-blocked" : "is-dest"}`} />
        </div>
        <div className="path-mobile-rail-copy">
          <p className="path-mobile-kicker">Where you are</p>
          <p className="path-mobile-current">
            {currentItem?.title || (currentPos != null ? `Step ${currentPos + 1}` : "Route start")}
          </p>
          {currentWeek != null ? <p className="path-mobile-week">Week {currentWeek}</p> : null}
          {nextItem ? (
            <p className="path-mobile-next">
              Next · {nextItem.title || prettySkill(nextItem.target_skill)}
            </p>
          ) : null}
          {blocked ? <p className="path-mobile-blocked">Blocked · {blocked} waiting on prerequisites</p> : null}
          {completed ? <p className="path-mobile-done">Complete · {completed}</p> : null}
        </div>
      </div>

      {currentWeek != null ? (
        <p className="path-week-sticky" aria-live="polite">
          Current week {currentWeek}
        </p>
      ) : null}

      <div className="path-spine" aria-label="Learning route">
        <div className="path-dest-node" aria-hidden>
          <span className="path-dest-dot" />
          <span className="path-dest-label">{roleName}</span>
        </div>

        {[...grouped.entries()].map(([week, items]) => (
          <section key={String(week)} className="path-week">
            <p className="path-week-label">
              {typeof week === "number" ? `Week ${week}` : week}
            </p>
            <div className="path-route">
              {items.map((item) => {
                const waiting = waitKindLabel(item);
                const isCompleted = item.status === "COMPLETED";
                const isExecutable = item.executable && item.kind === "EXECUTABLE" && !waiting;
                const kind = nodeKind(item, waiting, isCompleted, isExecutable);
                const archetype = routeArchetype(item);
                return (
                  <div
                    key={item.position}
                    className={`path-item-wrap path-node is-${kind} path-archetype-${archetype} ${isCompleted ? "is-frozen" : ""} ${waiting ? "is-waiting" : ""} ${isExecutable ? "is-current" : ""}`}
                    data-testid={waiting ? "blocked-prerequisite" : isExecutable ? "path-current-step" : undefined}
                  >
                    <Waypoint
                      kind={
                        archetype === "milestone"
                          ? "filled"
                          : isCompleted
                            ? "filled"
                            : waiting
                              ? "blocked"
                              : isExecutable
                                ? "open"
                                : "path"
                      }
                      className={`path-waypoint ${archetype === "milestone" ? "h-3.5 w-3.5" : archetype === "assessment" || archetype === "gate" ? "h-3 w-3" : "h-2.5 w-2.5"}`}
                    />
                    <button
                      type="button"
                      onClick={() => setOpen(item)}
                      className={`path-row path-node-body ${isExecutable ? "is-executable" : ""} ${waiting ? "is-waiting" : ""} ${isCompleted ? "is-completed" : ""}`}
                    >
                      <div className="path-node-primary">
                        <div className="path-node-heading">
                          <span className={`path-archetype-tag is-${archetype}`}>{archetypeLabel(archetype)}</span>
                          <p className="path-node-title">{item.title || prettySkill(item.target_skill)}</p>
                        </div>
                        <span className="path-node-state">{resourceWaitingLabel(item)}</span>
                      </div>
                      <p className="path-node-meta">
                        {item.week != null ? <span>Week {item.week}</span> : null}
                        <span>{prettySkill(item.target_skill)}</span>
                        {archetype === "resource" ? <span>{item.duration_hours ? `${item.duration_hours}h` : item.intervention}</span> : null}
                      </p>
                      <span className="path-node-why">Why</span>
                      {waiting ? <BlockerExposition item={item} gaps={gaps} /> : null}
                    </button>
                    <ProgressActions item={item} pathId={activePath.id} />
                  </div>
                );
              })}
            </div>
          </section>
        ))}

        <div className="path-dest-node is-terminus" aria-hidden>
          <span className="path-dest-dot is-end" />
          <span className="path-dest-label">{roleName}</span>
        </div>
      </div>

      {open ? <WhyDrawer item={open} onClose={() => setOpen(null)} /> : null}
    </div>
  );
}

export function WhyDrawer({ item, onClose }: { item: PathItem; onClose: () => void }) {
  const { gaps, learnerId, activePath } = useIntelligence();
  const cause = item.causality || {};
  const waiting = waitKindLabel(item);
  const scores = breakdownRows(item.score_breakdown || {});
  const primary = primaryBreakdownReason(item.score_breakdown || {});
  const semantic = semanticRelevanceTier(item.score_breakdown || {});
  const [showFactors, setShowFactors] = useState(false);

  return (
    <div className="drawer-scrim fixed inset-0 flex justify-end bg-black/45" role="dialog" aria-modal="true" aria-labelledby="why-drawer-title">
      <button type="button" className="h-full flex-1" aria-label="Dismiss why panel" onClick={onClose} />
      <section className="drawer-panel surface-focus h-full w-full max-w-md overflow-y-auto border-l border-line bg-ink-900">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h2 id="why-drawer-title" className="font-display text-xl text-paper">Why this is here</h2>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
        <div className="space-y-5 p-5 text-sm">
          <p className="text-paper">{item.title}</p>
          {waiting ? <BlockerChain item={item} gaps={gaps} /> : null}

          {primary ? (
            <div className="why-hero" data-testid="why-primary-reason">
              <p className="type-section">Why this resource</p>
              <p className="why-hero-label mt-2">{primary.label}</p>
              <p className="why-hero-value mt-1 font-mono text-2xl tabular-nums text-paper">{primary.value}</p>
              <p className="mt-2 text-xs leading-relaxed text-mist">
                Primary signal from the recommendation engine — one bounded factor among several.
              </p>
            </div>
          ) : (
            <Field label="Skill gap" value={humanizeEngineCopy(cause.why_this_skill || item.explanation)} />
          )}

          {semantic ? (
            <div className="why-semantic" data-testid="why-semantic-relevance">
              <p className="type-section">Semantic relevance</p>
              <p className="mt-2 font-display text-lg text-paper">{semantic}</p>
              <p className="mt-2 text-xs leading-relaxed text-mist">
                Bounded semantic similarity between this resource and your goal context — not an AI pick.
              </p>
            </div>
          ) : null}

          {cause.why_not_earlier ? (
            <div className="why-now">
              <p className="type-section">Why now</p>
              <p className="mt-2 leading-relaxed text-paper">{cause.why_not_earlier}</p>
            </div>
          ) : null}

          {scores.length ? (
            <div className="why-forensic-grid" data-testid="why-score-breakdown">
              <button
                type="button"
                className="why-factors-toggle"
                onClick={() => setShowFactors((open) => !open)}
                aria-expanded={showFactors}
              >
                {showFactors ? "Hide scoring factors" : "Show all scoring factors"}
              </button>
              {showFactors ? (
                <dl className="why-score-rows mt-3">
                  {scores.map((row) => (
                    <div key={row.key} className="why-score-row" data-testid={`why-breakdown-${row.key}`}>
                      <dt>{row.label}</dt>
                      <dd className="font-mono tabular-nums">{row.value}</dd>
                    </div>
                  ))}
                </dl>
              ) : null}
            </div>
          ) : null}

          <Field label="Resource" value={cause.why_this_resource || item.resource || item.title} />
          <Field label="Intervention" value={cause.why_this_intervention || item.intervention} />
          {learnerId && activePath ? <ProgressActions item={item} pathId={activePath.id} /> : null}
          {learnerId ? (
            <GroundedExplain
              intent="WHY_RESOURCE"
              resource={item.resource || undefined}
              skill={item.target_skill || undefined}
              triggerLabel="Grounded in"
              testId="why-resource"
            />
          ) : null}
        </div>
      </section>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wider text-mist">{label}</p>
      <p className="mt-1 leading-relaxed text-paper">{value || "—"}</p>
    </div>
  );
}
