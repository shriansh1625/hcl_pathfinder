"use client";

import { useEffect, useMemo, useState } from "react";
import { GroundedExplain } from "@/components/ai/GroundedExplain";
import { AdaptationTrace, buildAdaptationTrace } from "@/components/ui/AdaptationTrace";
import { Button } from "@/components/ui/Button";
import { CompetencyRow } from "@/components/ui/CompetencyRow";
import { EmptyState } from "@/components/ui/States";
import { FlipList } from "@/components/ui/FlipList";
import { Mark, ScreenKicker } from "@/components/ui/Mark";
import { useIntelligence } from "@/lib/session";
import { prefersReducedMotion } from "@/lib/motion";
import { prettySkill, displayDiagnosisTransition } from "@/lib/status";
import type { DiffEntry, PathItem } from "@/lib/types";

const LABELS = {
  added: "ADDED",
  removed: "REMOVED",
  moved: "MOVED",
  unchanged: "UNCHANGED",
  blocked: "BLOCKED",
} as const;

const CASCADE = [
  { n: "01", label: "Path V1" },
  { n: "02", label: "New evidence" },
  { n: "03", label: "Affected skill" },
  { n: "04", label: "New diagnosis" },
  { n: "05", label: "Action" },
  { n: "06", label: "Path change" },
  { n: "07", label: "Path V2" },
] as const;

function pathKey(item: PathItem): string {
  if (item.gate || item.kind === "VERIFICATION_GATE") return `gate:${item.target_skill}`;
  if (item.resource) return `resource:${item.resource}`;
  return `pos:${item.position}:${item.title}`;
}

function kindFor(
  key: string,
  item: PathItem,
  diff: { added: DiffEntry[]; removed: DiffEntry[]; moved: DiffEntry[]; blocked: DiffEntry[] } | null,
  phase: "v1" | "v2",
): string {
  if (item.status === "COMPLETED") return "frozen";
  if (phase === "v1") return "unchanged";
  if (!diff) return "unchanged";
  if (diff.added.some((row) => row.key === key || row.title === item.title)) return "added";
  if (diff.removed.some((row) => row.key === key || row.title === item.title)) return "removed";
  if (diff.moved.some((row) => row.key === key || row.title === item.title)) return "moved";
  if (diff.blocked.some((row) => row.key === key || row.title === item.title)) return "blocked";
  return "unchanged";
}

export function PathChanged() {
  const { previousPath, activePath, diff, attempt, beforeGaps, gaps, setView } = useIntelligence();
  const [phase, setPhase] = useState<"v1" | "v2">("v1");
  const [cascadeStep, setCascadeStep] = useState(0);
  const [skipped, setSkipped] = useState(false);

  const skill = attempt?.skill_results[0]?.skill;
  const before = beforeGaps.find((item) => item.skill === skill);
  const after = gaps.find((item) => item.skill === skill);
  const frozen = (activePath?.items || []).filter((item) => item.status === "COMPLETED");

  const trace = useMemo(
    () => buildAdaptationTrace({ attempt, before, after, diff }),
    [attempt, before, after, diff],
  );

  useEffect(() => {
    setPhase("v1");
    setCascadeStep(0);
    setSkipped(false);
    const reduced = prefersReducedMotion();
    const stepMs = reduced ? 0 : 140;
    const v2Delay = reduced ? 0 : 980;

    const cascadeTimer = window.setInterval(() => {
      setCascadeStep((step) => {
        const next = Math.min(step + 1, CASCADE.length - 1);
        if (next >= 5) setPhase("v2");
        return next;
      });
    }, stepMs);

    const v2Timer = window.setTimeout(() => setPhase("v2"), v2Delay);

    return () => {
      window.clearInterval(cascadeTimer);
      window.clearTimeout(v2Timer);
    };
  }, [activePath?.id]);

  const displayItems = useMemo(() => {
    const v1 = previousPath?.items ?? [];
    const v2 = activePath?.items ?? [];
    if (phase === "v1") return v1;
    const v2Keys = new Set(v2.map(pathKey));
    const removed = v1.filter((item) => !v2Keys.has(pathKey(item)));
    return [...v2, ...removed];
  }, [phase, previousPath, activePath]);

  if (!diff && !attempt) {
    return <EmptyState title="No adaptation yet" body="Submit an assessment to generate Path V2 from backend evidence." />;
  }

  const groups: { key: keyof typeof LABELS; items: DiffEntry[] }[] = [
    { key: "added", items: diff?.added ?? [] },
    { key: "removed", items: diff?.removed ?? [] },
    { key: "moved", items: diff?.moved ?? [] },
    { key: "blocked", items: diff?.blocked ?? [] },
    { key: "unchanged", items: (diff?.unchanged ?? []).slice(0, 4) },
  ];

  const liveIndex = skipped ? CASCADE.length - 1 : cascadeStep;
  const replay = `${phase}:${activePath?.id ?? "none"}:${liveIndex}`;
  const showEvidence = liveIndex >= 1;
  const showSkill = liveIndex >= 2 && after;
  const showDiagnosis = liveIndex >= 3 && after;
  const showAction = liveIndex >= 4 && after;

  function skipSequence() {
    setSkipped(true);
    setPhase("v2");
    setCascadeStep(CASCADE.length - 1);
  }

  return (
    <div className="path-hero space-y-10" data-testid="path-changed-hero">
      <div>
        <ScreenKicker verb="ADAPT">Path changed</ScreenKicker>
        <h1 className="mt-3 font-display text-4xl font-medium text-paper">PATH CHANGED</h1>
        <p className="mt-3 text-sm text-mist">Same learning objects. New plan — because evidence changed.</p>
        {!skipped && liveIndex < CASCADE.length - 1 ? (
          <button type="button" className="adapt-skip mt-3 text-xs uppercase tracking-wider text-mist underline-offset-2 hover:underline" onClick={skipSequence}>
            Skip
          </button>
        ) : null}
      </div>

      <ol className="cascade path-hero-cascade" data-testid="adapt-cascade">
        {CASCADE.map((step, index) => (
          <li
            key={step.n}
            className={`cascade-step ${index <= liveIndex ? "is-live" : ""} ${index === liveIndex ? "is-current" : ""}`}
            data-testid={`cascade-${step.label.toLowerCase().replace(/\s+/g, "-")}`}
          >
            <span className="cascade-index">{step.n}</span>
            <span>{step.label}</span>
            {index < CASCADE.length - 1 ? (
              <span className="cascade-join" aria-hidden>
                <Mark className="h-2.5 w-4" />
              </span>
            ) : null}
          </li>
        ))}
      </ol>

      {showEvidence ? (
        <div className="path-hero-evidence adapt-phase-in" data-testid="new-evidence-indicator">
          <p className="type-section">New evidence</p>
          <p className="mt-2 text-sm text-paper">
            {skill ? prettySkill(skill) : "Assessment"} · observed{" "}
            {attempt?.skill_results[0]?.observed_level.toFixed(2) ?? "—"}
          </p>
        </div>
      ) : null}

      {showSkill && after ? (
        <div className="path-hero-skill adapt-phase-in" data-testid="affected-skill">
          <p className="type-section">Affected skill</p>
          <CompetencyRow item={after} transitioning={liveIndex === 2} />
        </div>
      ) : null}

      {showDiagnosis && after ? (
        <div className="path-hero-diagnosis adapt-phase-in" data-testid="new-diagnosis">
          <p className="type-section">New diagnosis</p>
          <p className="mt-2 font-mono text-sm text-paper">
            {displayDiagnosisTransition(before, after)}
          </p>
        </div>
      ) : null}

      {showAction && after ? (
        <div className="path-hero-action adapt-phase-in" data-testid="adapt-action">
          <p className="type-section">Action</p>
          <p className="mt-2 text-sm text-paper">{after.action.replaceAll("_", " ")}</p>
        </div>
      ) : null}

      <AdaptationTrace steps={trace} />

      <section className={`path-hero-flip ${phase === "v1" ? "is-v1" : "is-v2"}`} data-testid="path-flip-stage">
        <div className="mb-4 flex items-baseline justify-between gap-4">
          <p className="text-[11px] uppercase tracking-[0.16em] text-mist">
            V{previousPath?.version ?? 1}
            <span className="mx-2 text-paper/50">→</span>
            V{activePath?.version ?? 2}
            <span className="ml-3 text-mist/70">{phase === "v1" ? "prior path" : "adapted path"}</span>
          </p>
        </div>
        <p className="adapt-causality-line" aria-live="polite">
          {liveIndex < 1
            ? "Prior route holds."
            : liveIndex < 3
              ? "New evidence arrived. Affected skill is reacting."
              : liveIndex < 5
                ? "Diagnosis updated. Action is entering the route."
                : "Dependent waypoints are shifting. Frozen work stays anchored."}
        </p>
        <FlipList replay={replay}>
          {displayItems.map((item) => {
            const key = pathKey(item);
            const kind = kindFor(key, item, diff, phase);
            return (
              <div
                key={key}
                data-flip-key={key}
                data-flip-lock={kind === "frozen" ? "1" : undefined}
                className={`path-row adapt-waypoint diff-${kind}`}
              >
                <span className={`adapt-waypoint-dot is-${kind}`} aria-hidden />
                <div className="adapt-waypoint-body">
                  <p className={`text-sm text-paper ${kind === "removed" ? "diff-removed-title" : ""}`}>
                    {item.title || prettySkill(item.target_skill)}
                  </p>
                  <p className="mt-1 text-xs text-mist">
                    {prettySkill(item.target_skill)}
                    {item.week != null ? ` · Week ${item.week}` : ""}
                  </p>
                </div>
                <span className="font-mono text-[11px] tracking-wider text-mist">
                  {kind === "frozen" ? "FROZEN WORK" : LABELS[kind as keyof typeof LABELS] ?? kind.toUpperCase()}
                </span>
              </div>
            );
          })}
        </FlipList>
      </section>

      <section className="divide-y divide-line border-y border-line">
        {groups.map((group) =>
          group.items.length ? (
            <div key={group.key} className="py-5">
              <p className="font-mono text-[11px] tracking-[0.14em] text-mist">{LABELS[group.key]}</p>
              <ul className="mt-3 space-y-2">
                {group.items.map((item) => (
                  <li key={item.key} data-testid={`diff-${group.key}`} className={`diff-${group.key}`}>
                    <p className="text-sm text-paper">{item.title}</p>
                    <p className="text-xs text-mist">{item.reason}</p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null,
        )}
      </section>

      <section className="diff-frozen border-y border-line py-5">
        <p className="text-[11px] uppercase tracking-[0.16em] text-mist">Frozen work</p>
        <h2 className="mt-2 font-display text-2xl text-paper">Completed work preserved</h2>
        {frozen.length ? (
          <ul className="mt-4 space-y-2" data-testid="frozen-work">
            {frozen.map((item) => (
              <li key={item.position} className="text-sm text-paper">
                Week {item.week ?? "—"} — {item.title} · COMPLETED
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-mist">No completed items on the active path.</p>
        )}
      </section>

      <div className="space-y-5">
        <GroundedExplain intent="WHAT_CHANGED" skill={skill} triggerLabel="What changed?" testId="what-changed-path" />
        <GroundedExplain intent="NEXT_ACTION" triggerLabel="What should I do next?" testId="next-action-path" />
        <div className="flex justify-end">
          <Button onClick={() => setView("why")}>Why this changed</Button>
        </div>
      </div>
    </div>
  );
}