"use client";

import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/States";
import { useIntelligence } from "@/lib/session";
import { FOCUS_SKILLS, prettySkill, visualState } from "@/lib/status";

export function SkillMap() {
  const { gaps } = useIntelligence();
  const focus = FOCUS_SKILLS.map((skill) => gaps.find((item) => item.skill === skill)).filter(Boolean);
  if (!focus.length) {
    return <EmptyState title="No competency graph yet" body="Diagnose a learner to see what blocks what." />;
  }

  const edges = focus.flatMap((item) => {
    if (!item) return [];
    const hard = item.hard_downstream.slice(0, 3).map((target) => ({
      from: item.skill,
      to: target,
      kind: "HARD" as const,
    }));
    const blockedBy = item.blockers.map((source) => ({
      from: source,
      to: item.skill,
      kind: "HARD" as const,
    }));
    const soft = item.preparation_skills.slice(0, 2).map((source) => ({
      from: source,
      to: item.skill,
      kind: "SOFT" as const,
    }));
    return [...hard, ...blockedBy, ...soft];
  });

  const unique = edges.filter(
    (edge, index, all) =>
      all.findIndex((row) => row.from === edge.from && row.to === edge.to && row.kind === edge.kind) === index,
  );

  return (
    <div className="space-y-6">
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-accent">Skill map</p>
        <h1 className="mt-2 text-3xl font-medium text-paper">What blocks what?</h1>
        <p className="mt-2 max-w-2xl text-sm text-mist">
          HARD edges are prerequisites. SOFT edges are preparation. This is a dependency readout
          from the gap profile, not a decorative graph.
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {focus.map((item) =>
          item ? (
            <Panel key={item.skill} className="p-4">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm text-paper">{item.name || prettySkill(item.skill)}</p>
                <StatusBadge state={visualState(item)} />
              </div>
              <p className="mt-3 text-[11px] uppercase tracking-wider text-mist">Downstream</p>
              <p className="text-xs text-paper">
                {item.hard_downstream.slice(0, 4).map(prettySkill).join(", ") || "—"}
              </p>
            </Panel>
          ) : null,
        )}
      </div>
      <Panel className="p-5">
        <p className="text-xs uppercase tracking-wider text-mist">Edges</p>
        <ul className="mt-3 space-y-2 font-mono text-xs text-paper">
          {unique.slice(0, 18).map((edge) => (
            <li key={`${edge.kind}-${edge.from}-${edge.to}`}>
              {prettySkill(edge.from)}
              <span className="mx-2 text-accent">{edge.kind}</span>
              {prettySkill(edge.to)}
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
