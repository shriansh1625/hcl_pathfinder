"use client";

import { useMemo, useState } from "react";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/States";
import { Mark, ScreenKicker } from "@/components/ui/Mark";
import { useIntelligence } from "@/lib/session";
import { focusGaps, prettySkill, visualState } from "@/lib/status";

export function SkillMap() {
  const { gaps } = useIntelligence();
  const focus = focusGaps(gaps);
  const [selected, setSelected] = useState<string | null>(focus[0]?.skill ?? null);
  const selectedItem = gaps.find((item) => item.skill === selected) ?? focus[0];

  const unique = useMemo(() => {
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
    return edges.filter(
      (edge, index, all) =>
        all.findIndex((row) => row.from === edge.from && row.to === edge.to && row.kind === edge.kind) === index,
    );
  }, [focus]);

  if (!focus.length) {
    return <EmptyState title="No competency graph yet" body="Diagnose a learner to see what blocks what." />;
  }

  return (
    <div className="space-y-10">
      <div>
        <ScreenKicker verb="DIAGNOSE">Dependencies</ScreenKicker>
        <h1 className="mt-3 font-display text-4xl font-medium text-paper">What blocks what?</h1>
        <p className="mt-3 max-w-2xl text-sm text-mist">
          Select a skill to illuminate its HARD prerequisite path. This is a dependency readout, not a decorative graph.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {focus.map((item) =>
          item ? (
            <button
              key={item.skill}
              type="button"
              onClick={() => setSelected(item.skill)}
              className={`border-b px-3 py-2 text-left text-sm ${
                selected === item.skill ? "border-paper/55 text-paper" : "border-line text-mist"
              }`}
            >
              <span className="block">{item.name || prettySkill(item.skill)}</span>
              <StatusBadge state={visualState(item)} />
            </button>
          ) : null,
        )}
      </div>

      {selectedItem?.blocked ? (
        <p className="text-sm text-mist">
          {prettySkill(selectedItem.skill)} is blocked until {selectedItem.blockers.map(prettySkill).join(", ")} is addressed.
        </p>
      ) : null}

      <ul className="space-y-3 font-mono text-xs">
        {unique.slice(0, 18).map((edge) => {
          const active =
            selected === edge.from ||
            selected === edge.to ||
            (selectedItem?.blockers.includes(edge.from) && selected === edge.to);
          return (
            <li key={`${edge.kind}-${edge.from}-${edge.to}`} className={`edge-row ${active ? "is-active" : ""}`}>
              {prettySkill(edge.from)}
              <Mark className="mx-2 inline h-2.5 w-4 align-middle text-current opacity-70" />
              <span className="tracking-[0.14em] text-mist">{edge.kind}</span>
              <Mark className="mx-2 inline h-2.5 w-4 align-middle text-current opacity-70" />
              {prettySkill(edge.to)}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
