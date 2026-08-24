"use client";

import { useState } from "react";
import { GroundedExplain } from "@/components/ai/GroundedExplain";
import { CompetencyRow } from "@/components/ui/CompetencyRow";
import { EvidencePanel } from "@/components/ui/EvidencePanel";
import { EmptyState, LoadingState } from "@/components/ui/States";
import { ScreenKicker } from "@/components/ui/Mark";
import { useIntelligence } from "@/lib/session";
import { focusGaps, prettySkill } from "@/lib/status";

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
  const focus = focusGaps(gaps);
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

  return (
    <div className="diagnostic-stack space-y-10">
      <div>
        <ScreenKicker verb="KNOW">Dashboard</ScreenKicker>
        <h1 className="type-headline mt-3 text-4xl font-medium text-paper">{roleName}</h1>
        {dashboard?.goal_text ? (
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-paper/90" data-testid="dashboard-goal">
            {dashboard.goal_text}
          </p>
        ) : null}
        <p className="type-meta mt-2 normal-case">
          {weeklyHours} hours / week · {learningStyle.replaceAll("_", " ")}
          {dashboard?.path_version ? ` · Path V${dashboard.path_version}` : ""}
        </p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="dash-stat">
          <p className="text-xs uppercase tracking-[0.16em] text-mist">Progress</p>
          <p className="mt-2 text-2xl text-paper">
            {progress ? `${progress.completed_items}/${progress.total_items}` : "—"}
          </p>
          <p className="text-xs text-mist">path items complete</p>
        </div>
        <div className="dash-stat">
          <p className="text-xs uppercase tracking-[0.16em] text-mist">Evidence</p>
          <p className="mt-2 text-2xl text-paper">
            {progress ? `${progress.evidence_coverage}/${progress.competency_total}` : "—"}
          </p>
          <p className="text-xs text-mist">competencies with proof</p>
        </div>
        <div className="dash-stat">
          <p className="text-xs uppercase tracking-[0.16em] text-mist">Milestone</p>
          <p className="mt-2 text-lg text-paper">{dashboard?.current_milestone?.label ?? "Pending"}</p>
          <p className="text-xs text-mist">{dashboard?.current_milestone?.status ?? "Awaiting path"}</p>
        </div>
        <div className="dash-stat">
          <p className="text-xs uppercase tracking-[0.16em] text-mist">Next action</p>
          <p className="mt-2 text-sm text-paper">{dashboard?.next_action?.title ?? "—"}</p>
          <p className="text-xs text-mist">{dashboard?.next_action?.intervention ?? "No pending step"}</p>
        </div>
      </section>

      {dashboard?.why_this_matters ? (
        <section>
          <p className="type-section">Why this matters</p>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-mist">{dashboard.why_this_matters}</p>
        </section>
      ) : null}

      {dashboard?.recent_adaptation ? (
        <section>
          <p className="type-section">Recent adaptation</p>
          <p className="mt-2 text-sm text-mist">{dashboard.recent_adaptation.summary}</p>
        </section>
      ) : null}

      <section>
        <p className="type-section">Competency snapshot</p>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-mist">
          Determined by PathFinder from fused evidence — explained separately by the grounded AI layer.
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
          {focus.map((item, index) => (
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
      </section>

      {dashboard?.milestones.length ? (
        <section>
          <p className="type-section">Milestones</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {dashboard.milestones.map((milestone) => (
              <div key={milestone.id} className="rounded border border-line p-4">
                <p className="font-medium text-paper">{milestone.label}</p>
                <p className="mt-1 text-xs text-mist">
                  {milestone.completed_items}/{milestone.total_items} items · {milestone.status}
                </p>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {blockers.length > 0 ? (
        <section>
          <p className="type-section">Blockers</p>
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

      {dashboard?.this_week.length ? (
        <section>
          <p className="type-section">This week</p>
          <ul className="mt-3 space-y-2 text-sm">
            {dashboard.this_week.map((item) => (
              <li key={item.position} className="flex justify-between gap-4 text-mist">
                <span className="text-paper">{item.title}</span>
                <span>{item.status}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {activePath && dashboard?.upcoming_assessment?.assessment ? (
        <section>
          <p className="type-section">Upcoming assessment</p>
          <p className="mt-2 text-sm text-mist">
            {dashboard.upcoming_assessment.title} — {dashboard.upcoming_assessment.reason}
          </p>
        </section>
      ) : null}
    </div>
  );
}
