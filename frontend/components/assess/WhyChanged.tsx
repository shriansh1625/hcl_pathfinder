"use client";

import { GroundedExplain } from "@/components/ai/GroundedExplain";
import { AdaptationTrace, buildAdaptationTrace } from "@/components/ui/AdaptationTrace";
import { ScreenKicker } from "@/components/ui/Mark";
import { useIntelligence } from "@/lib/session";
import { prettySkill, displayAttainment, humanizeEngineCopy } from "@/lib/status";

export function WhyChanged() {
  const { attempt, diff, beforeGaps, gaps, activePath, timeline } = useIntelligence();
  const skill = attempt?.skill_results[0]?.skill;
  const before = beforeGaps.find((item) => item.skill === skill);
  const after = gaps.find((item) => item.skill === skill);
  const steps = buildAdaptationTrace({ attempt, before, after, diff });
  const frozen = (activePath?.items || []).filter((item) => item.status === "COMPLETED");
  const observed = attempt?.skill_results[0]?.observed_level.toFixed(2) ?? "—";
  const beforeLabel = displayAttainment(before);

  return (
    <div className="forensic-inspect mx-auto max-w-2xl space-y-10" data-testid="why-changed">
      <div>
        <ScreenKicker verb="ADAPT">Causality</ScreenKicker>
        <h1 className="forensic-title mt-3 font-display text-paper">Why this changed</h1>
        <p className="mt-3 text-sm text-mist">Evidence → diagnosis → action → path change. Every statement comes from stored backend state.</p>
      </div>

      <section className="forensic-block" data-testid="what-changed-section">
        <p className="type-section">What changed</p>
        <AdaptationTrace steps={steps} />
        {diff ? (
          <ul className="forensic-diff mt-4 space-y-2 text-sm text-paper">
            {diff.added.map((row) => (
              <li key={row.key}>+ {row.title}</li>
            ))}
            {diff.moved.map((row) => (
              <li key={row.key}>
                → {row.title}
                {row.from_week != null && row.to_week != null ? ` (Week ${row.from_week} → Week ${row.to_week})` : ""}
              </li>
            ))}
            {diff.removed.map((row) => (
              <li key={row.key} className="text-mist">− {row.title}</li>
            ))}
            {diff.blocked.map((row) => (
              <li key={row.key}>⊘ {row.title}</li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="forensic-block" data-testid="why-changed-section">
        <p className="type-section">Why it changed</p>
        <dl className="forensic-grid mt-4">
          <div>
            <dt>Evidence</dt>
            <dd>
              {skill ? prettySkill(skill) : "—"}
              <span className="forensic-metric font-mono tabular-nums"> · observed {observed}</span>
            </dd>
          </div>
          <div>
            <dt>Before</dt>
            <dd>{beforeLabel}</dd>
          </div>
          <div>
            <dt>After</dt>
            <dd>{after ? displayAttainment(after) : "—"}</dd>
          </div>
          <div>
            <dt>Action</dt>
            <dd>{after?.action?.replaceAll("_", " ") ?? attempt?.adaptation ?? "—"}</dd>
          </div>
          {after?.explanation ? (
            <div className="forensic-span">
              <dt>Diagnosis</dt>
              <dd>{humanizeEngineCopy(after.explanation)}</dd>
            </div>
          ) : null}
        </dl>
      </section>

      <section className="forensic-block" data-testid="preserved-section">
        <p className="type-section">What was preserved</p>
        {frozen.length ? (
          <ul className="forensic-frozen mt-4 space-y-2 text-sm text-paper">
            {frozen.map((item) => (
              <li key={item.position}>
                Week {item.week ?? "—"} — {item.title} · COMPLETED
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 text-sm text-mist">No completed path items on the active version.</p>
        )}
        {timeline.length ? (
          <p className="mt-4 text-xs text-mist">
            Timeline: {timeline.map((entry) => `V${entry.version} ${entry.status}`).join(" → ")}
          </p>
        ) : null}
      </section>

      <GroundedExplain intent="WHAT_CHANGED" skill={skill} triggerLabel="What changed?" testId="what-changed" />
      <GroundedExplain intent="NEXT_ACTION" triggerLabel="What should I do next?" testId="next-action" />
    </div>
  );
}
