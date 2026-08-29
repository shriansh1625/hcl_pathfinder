"use client";

import { useState } from "react";
import { GroundedExplain } from "@/components/ai/GroundedExplain";
import { CompetencyRow } from "@/components/ui/CompetencyRow";
import { EvidencePanel } from "@/components/ui/EvidencePanel";
import { EmptyState, LoadingState } from "@/components/ui/States";
import { ScreenKicker } from "@/components/ui/Mark";
import { IntelligenceExplainer } from "@/components/overview/IntelligenceExplainer";
import { useIntelligence } from "@/lib/session";
import { focusGaps, prettySkill, humanizeEngineCopy, visualState } from "@/lib/status";
import { StatusBadge } from "@/components/ui/StatusBadge";

export function Overview() {
  const {
    gaps,
    dashboard,
    roleName,
    weeklyHours,
    learningStyle,
    loading,
    beforeGaps,
    skills,
    learnerId,
    activePath,
  } = useIntelligence();
  const [inspectSkill, setInspectSkill] = useState<string | null>(null);
  const [showAllGaps, setShowAllGaps] = useState(false);
  const focus = focusGaps(gaps);
  const primaryGaps = focus.slice(0, 3);
  const secondaryGaps = focus.slice(3);
  const shifted = new Set(
    beforeGaps
      .filter((before) => {
        const after = gaps.find((item) => item.skill === before.skill);
        return after && (after.attainment !== before.attainment || after.evidence_state !== before.evidence_state);
      })
      .map((item) => item.skill),
  );
  const progress = dashboard?.overall_progress;
  const blockers = dashboard?.blockers ?? gaps.filter((item) => item.blocked);
  const missing = gaps.filter(
    (item) => item.attainment === "GAP" || item.attainment === "NEAR_TARGET" || item.attainment === "UNKNOWN",
  ).length;
  const known = gaps.filter((item) => item.evidence_state !== "UNKNOWN").length;
  const topGap = focus.find((item) => item.attainment === "GAP" || item.attainment === "UNKNOWN") ?? focus[0];

  return (
    <div className="command-center">
      <header className="command-hero">
        <div>
          <ScreenKicker verb="KNOW">Dashboard</ScreenKicker>
          <p className="type-section mt-1">Destination</p>
          <h1 className="type-hero mt-2 text-paper">{roleName}</h1>
          {dashboard?.goal_text ? (
            <p className="mt-4 max-w-xl text-[1.02rem] leading-relaxed text-paper/90" data-testid="dashboard-goal">
              {dashboard.goal_text}
            </p>
          ) : null}
          <p className="type-meta mt-3 normal-case tracking-normal">
            {weeklyHours} hours / week · {learningStyle.replaceAll("_", " ")}
            {dashboard?.path_version ? ` · Path V${dashboard.path_version}` : ""}
          </p>
        </div>
        <div className="command-next hidden lg:block">
          <p className="type-section">What to do next</p>
          <p className="mt-3 font-display text-2xl leading-snug tracking-tight text-paper">
            {dashboard?.next_action?.title ?? "Awaiting a sequenced path"}
          </p>
          <p className="mt-2 text-sm text-mist">{dashboard?.next_action?.intervention ?? "No pending step"}</p>
          {topGap ? (
            <p className="command-top-gap mt-4">
              <span className="type-section">Top gap</span>
              <span className="mt-1 block font-display text-lg text-paper">{prettySkill(topGap.skill)}</span>
            </p>
          ) : null}
        </div>
      </header>

      <IntelligenceExplainer compact />

      <dl className="command-position">
        <div className="command-cell is-dominant">
          <dt>Current position</dt>
          <dd>{progress ? `${progress.completed_items} / ${progress.total_items}` : "—"}</dd>
          <p className="command-note">path items complete</p>
        </div>
        <div className="command-cell">
          <dt>Evidence held</dt>
          <dd>
            {progress ? `${progress.evidence_coverage}/${progress.competency_total}` : known ? String(known) : "—"}
          </dd>
          <p className="command-note">competencies with proof</p>
        </div>
        <div className="command-cell">
          <dt>Still open</dt>
          <dd>{missing || "—"}</dd>
          <p className="command-note">gaps, near-target, no evidence</p>
        </div>
        <div className="command-cell">
          <dt>Milestone</dt>
          <dd>{dashboard?.current_milestone?.label ?? "Pending"}</dd>
          <p className="command-note">{dashboard?.current_milestone?.status ?? "Awaiting path"}</p>
        </div>
      </dl>

      <div className="command-brief">
        <div className="space-y-8">
          {dashboard?.why_this_matters ? (
            <section>
              <p className="type-section">Why this matters</p>
              <p className="mt-3 max-w-2xl text-[0.95rem] leading-relaxed text-mist">{dashboard.why_this_matters}</p>
            </section>
          ) : null}
          {dashboard?.recent_adaptation ? (
            <section>
              <p className="type-section">Recent change</p>
              <p className="mt-3 text-sm leading-relaxed text-mist">{dashboard.recent_adaptation.summary}</p>
            </section>
          ) : null}
          {blockers.length > 0 ? (
            <section>
              <p className="type-section">What is blocking</p>
              <ul className="mt-3 space-y-2 text-sm text-mist">
                {blockers.slice(0, 5).map((item) => (
                  <li key={item.skill}>
                    <span className="text-paper">{prettySkill(item.skill)}</span> — blocked by{" "}
                    {item.blockers.map(prettySkill).join(", ") || "prerequisites"}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
        <div className="space-y-8">
          <section className="command-next lg:hidden">
            <p className="type-section">What to do next</p>
            <p className="mt-3 font-display text-xl text-paper">{dashboard?.next_action?.title ?? "—"}</p>
            <p className="mt-2 text-sm text-mist">{dashboard?.next_action?.intervention ?? "No pending step"}</p>
            {topGap ? (
              <p className="command-top-gap mt-4">
                <span className="type-section">Top gap</span>
                <span className="mt-1 block font-display text-lg text-paper">{prettySkill(topGap.skill)}</span>
              </p>
            ) : null}
          </section>
          {dashboard?.this_week?.length ? (
            <section>
              <p className="type-section">This week</p>
              <ul className="command-week mt-3">
                {dashboard.this_week.map((item) => (
                  <li key={item.position}>
                    <span className="text-paper">{item.title}</span>
                    <span className="font-mono text-[11px] uppercase tracking-wider text-mist">{item.status}</span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
          {activePath && dashboard?.upcoming_assessment?.assessment ? (
            <section>
              <p className="type-section">Upcoming assessment</p>
              <p className="mt-2 text-sm text-mist">
                {dashboard.upcoming_assessment.title} — {humanizeEngineCopy(dashboard.upcoming_assessment.reason)}
              </p>
            </section>
          ) : null}
        </div>
      </div>

      <section className="command-route">
        <p className="type-section">Priority competency gaps</p>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-mist">
          Top gaps by role priority — current evidence vs target. UNKNOWN means no evidence, not zero.
        </p>
        <div className="mt-4 divide-y divide-line border-y border-line">
          {loading && !gaps.length ? (
            <div className="py-6">
              <LoadingState label="Reading your evidence" detail="Loading fused competency from the live backend." />
            </div>
          ) : null}
          {!loading && !focus.length ? (
            <div className="py-6">
              <EmptyState
                title="No competency profile yet"
                body="PathFinder needs evidence before it can determine your competency. Create a path to begin diagnosis."
              />
            </div>
          ) : null}
          {primaryGaps.map((item, index) => (
            <div
              key={item.skill}
              className="competency-reveal"
              style={{ animationDelay: `${Math.min(index * 48, 400)}ms` }}
            >
              <CompetencyRow
                item={item}
                transitioning={shifted.has(item.skill)}
                onInspectEvidence={() => setInspectSkill((current) => (current === item.skill ? null : item.skill))}
                inspecting={inspectSkill === item.skill}
              />
              {inspectSkill === item.skill ? (
                <EvidencePanel
                  skill={item.skill}
                  fused={skills.find((row) => row.skill === item.skill) ?? null}
                  learnerId={learnerId}
                />
              ) : null}
              {item.attainment === "GAP" || item.attainment === "NEAR_TARGET" || item.attainment === "UNKNOWN" ? (
                <div className="pb-4">
                  <GroundedExplain
                    intent="WHY_GAP"
                    skill={item.skill}
                    triggerLabel="Why this gap?"
                    testId={`why-gap-${item.skill}`}
                  />
                </div>
              ) : null}
            </div>
          ))}
        </div>
        {secondaryGaps.length ? (
          <div className="competency-secondary mt-4">
            <button
              type="button"
              className="competency-expand"
              onClick={() => setShowAllGaps((open) => !open)}
              aria-expanded={showAllGaps}
            >
              {showAllGaps ? "Hide additional competencies" : `Show ${secondaryGaps.length} more competencies`}
            </button>
            {showAllGaps ? (
              <ul className="competency-chip-list mt-3">
                {secondaryGaps.map((item) => (
                  <li key={item.skill} className="competency-chip-row">
                    <span className="text-sm text-paper">{item.name || prettySkill(item.skill)}</span>
                    <StatusBadge state={visualState(item)} />
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </section>

      {dashboard?.milestones.length ? (
        <section>
          <p className="type-section">Milestones</p>
          <div className="milestone-route mt-2">
            {dashboard.milestones.map((milestone) => (
              <article
                key={milestone.id}
                className={milestone.id === dashboard.current_milestone?.id ? "is-current" : ""}
              >
                <span className="milestone-node" aria-hidden />
                <div>
                  <p className="font-medium text-paper">{milestone.label}</p>
                  <p className="mt-1 text-xs text-mist">
                    {milestone.completed_items}/{milestone.total_items} items · {milestone.status}
                  </p>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
