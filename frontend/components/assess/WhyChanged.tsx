"use client";

import { GroundedExplain } from "@/components/ai/GroundedExplain";
import { AdaptationTrace, buildAdaptationTrace } from "@/components/ui/AdaptationTrace";
import { ScreenKicker } from "@/components/ui/Mark";
import { useIntelligence } from "@/lib/session";
import { prettySkill } from "@/lib/status";

export function WhyChanged() {
  const { attempt, diff, beforeGaps, gaps, activePath, timeline } = useIntelligence();
  const skill = attempt?.skill_results[0]?.skill;
  const before = beforeGaps.find((item) => item.skill === skill);
  const after = gaps.find((item) => item.skill === skill);
  const steps = buildAdaptationTrace({ attempt, before, after, diff });
  const frozen = (activePath?.items || []).filter((item) => item.status === "COMPLETED");

  return (
    <div className="mx-auto max-w-2xl space-y-10" data-testid="why-changed">
      <div>
        <ScreenKicker verb="ADAPT">Causality</ScreenKicker>
        <h1 className="mt-3 font-display text-4xl font-medium text-paper">Why this changed</h1>
        <p className="mt-3 text-sm text-mist">Evidence → diagnosis → action → path change. Every statement comes from stored backend state.</p>
      </div>

      <section data-testid="what-changed-section">
        <p className="type-section">What changed</p>
        <AdaptationTrace steps={steps} />
        {diff ? (
          <ul className="mt-4 space-y-2 text-sm text-paper">
            {diff.added.map((row) => (
              <li key={row.key}>+ {row.title}</li>
            ))}
            {diff.moved.map((row) => (
              <li key={row.key}>
                → {row.title}
                {row.from_week != null && row.to_week != null ? ` (Week ${row.from_week} → ${row.to_week})` : ""}
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

      <section data-testid="why-changed-section">
        <p className="type-section">Why it changed</p>
        <dl className="mt-4 space-y-3 text-sm">
          <div>
            <dt className="text-mist">Evidence</dt>
            <dd className="mt-1 text-paper">
              {skill ? prettySkill(skill) : "—"} · observed {attempt?.skill_results[0]?.observed_level.toFixed(2) ?? "—"}
            </dd>
          </div>
          <div>
            <dt className="text-mist">Old state</dt>
            <dd className="mt-1 text-paper">{before ? (before.evidence_state === "UNKNOWN" ? "UNKNOWN" : before.attainment) : "—"}</dd>
          </div>
          <div>
            <dt className="text-mist">New state</dt>
            <dd className="mt-1 text-paper">{after?.attainment ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-mist">Action</dt>
            <dd className="mt-1 text-paper">{after?.action?.replaceAll("_", " ") ?? attempt?.adaptation ?? "—"}</dd>
          </div>
          {after?.explanation ? (
            <div>
              <dt className="text-mist">Diagnosis</dt>
              <dd className="mt-1 text-paper">{after.explanation}</dd>
            </div>
          ) : null}
        </dl>
      </section>

      <section data-testid="preserved-section">
        <p className="type-section">What was preserved</p>
        {frozen.length ? (
          <ul className="mt-4 space-y-2 text-sm text-paper">
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