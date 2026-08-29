"use client";

import { useMemo, useState } from "react";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/States";
import { ScreenKicker, Waypoint } from "@/components/ui/Mark";
import { useIntelligence } from "@/lib/session";
import { focusGaps, prettySkill, visualState } from "@/lib/status";

type Edge = {
  from: string;
  to: string;
  kind: "HARD" | "SOFT";
  relation: "dependent" | "blocker" | "prep";
};

type Point = { x: number; y: number };

function layoutPlot(
  selected: string,
  blockers: string[],
  dependents: string[],
  prep: string[],
  extras: string[],
): Record<string, Point> {
  const pos: Record<string, Point> = {
    [selected]: { x: 400, y: 188 },
  };
  blockers.slice(0, 4).forEach((slug, i) => {
    const n = Math.min(blockers.length, 4);
    pos[slug] = { x: 88, y: n === 1 ? 188 : 72 + (i * 232) / Math.max(n - 1, 1) };
  });
  dependents.slice(0, 4).forEach((slug, i) => {
    const n = Math.min(dependents.length, 4);
    pos[slug] = { x: 712, y: n === 1 ? 188 : 72 + (i * 232) / Math.max(n - 1, 1) };
  });
  prep.slice(0, 3).forEach((slug, i) => {
    pos[slug] = { x: 250 + i * 150, y: 338 };
  });
  extras.forEach((slug, i) => {
    if (pos[slug]) return;
    pos[slug] = { x: 220 + (i % 3) * 180, y: 48 };
  });
  return pos;
}

export function SkillMap() {
  const { gaps } = useIntelligence();
  const focus = focusGaps(gaps);
  const [selected, setSelected] = useState<string | null>(focus[0]?.skill ?? null);
  const selectedItem = gaps.find((item) => item.skill === selected) ?? focus[0];

  const unique = useMemo(() => {
    const edges: Edge[] = focus.flatMap((item) => {
      if (!item) return [];
      const hard = item.hard_downstream.slice(0, 3).map((target) => ({
        from: item.skill,
        to: target,
        kind: "HARD" as const,
        relation: "dependent" as const,
      }));
      const blockedBy = item.blockers.map((source) => ({
        from: source,
        to: item.skill,
        kind: "HARD" as const,
        relation: "blocker" as const,
      }));
      const soft = item.preparation_skills.slice(0, 2).map((source) => ({
        from: source,
        to: item.skill,
        kind: "SOFT" as const,
        relation: "prep" as const,
      }));
      return [...hard, ...blockedBy, ...soft];
    });
    return edges.filter(
      (edge, index, all) =>
        all.findIndex((row) => row.from === edge.from && row.to === edge.to && row.kind === edge.kind) === index,
    );
  }, [focus]);

  const plot = useMemo(() => {
    if (!selectedItem) return { pos: {} as Record<string, Point>, nodes: [] as string[] };
    const blockers = selectedItem.blockers;
    const dependents = selectedItem.hard_downstream.slice(0, 4);
    const prep = selectedItem.preparation_skills.slice(0, 3);
    const extras = focus
      .map((item) => item.skill)
      .filter((slug) => slug !== selectedItem.skill && !blockers.includes(slug) && !dependents.includes(slug) && !prep.includes(slug));
    const pos = layoutPlot(selectedItem.skill, blockers, dependents, prep, extras.slice(0, 3));
    const nodes = Object.keys(pos);
    return { pos, nodes };
  }, [selectedItem, focus]);

  if (!focus.length) {
    return <EmptyState title="No competency graph yet" body="Diagnose a learner to see what blocks what." />;
  }

  const neighborhood = new Set([
    selectedItem?.skill,
    ...(selectedItem?.blockers ?? []),
    ...(selectedItem?.hard_downstream ?? []),
    ...(selectedItem?.preparation_skills ?? []),
  ]);

  return (
    <div className="skill-instrument space-y-10">
      <div>
        <ScreenKicker verb="DIAGNOSE">Dependencies</ScreenKicker>
        <h1 className="skill-instrument-title mt-3 font-display text-paper">What blocks what?</h1>
        <p className="mt-3 max-w-2xl text-sm text-mist">
          Select a skill to illuminate HARD blockers, HARD dependents, and SOFT preparation. Unselected relationships recede.
        </p>
      </div>

      {selectedItem ? (
        <dl className="skill-readout">
          <div>
            <dt>Current</dt>
            <dd className="font-mono tabular-nums">
              {selectedItem.proficiency == null ? "No evidence" : selectedItem.proficiency.toFixed(2)}
            </dd>
          </div>
          <div>
            <dt>Target</dt>
            <dd className="font-mono tabular-nums">{selectedItem.target_level.toFixed(2)}</dd>
          </div>
          <div>
            <dt>State</dt>
            <dd>
              <StatusBadge state={visualState(selectedItem)} />
            </dd>
          </div>
        </dl>
      ) : null}

      <div className="skill-picker" role="list">
        {focus.map((item) =>
          item ? (
            <button
              key={item.skill}
              type="button"
              role="listitem"
              onClick={() => setSelected(item.skill)}
              className={`skill-pick ${selected === item.skill ? "is-selected" : ""}`}
            >
              <Waypoint kind={selected === item.skill ? "filled" : "open"} className="h-2.5 w-2.5" />
              <span className="skill-pick-name">{item.name || prettySkill(item.skill)}</span>
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

      {selectedItem ? (
        <div className="skill-plot" data-testid="skill-plot">
          <svg viewBox="0 0 800 400" className="skill-plot-svg" role="img" aria-label="Skill dependency neighborhood">
            {unique.map((edge) => {
              const a = plot.pos[edge.from];
              const b = plot.pos[edge.to];
              if (!a || !b) return null;
              const active =
                Boolean(selected) &&
                (selected === edge.from || selected === edge.to || neighborhood.has(edge.from) || neighborhood.has(edge.to));
              return (
                <line
                  key={`${edge.kind}-${edge.from}-${edge.to}`}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  className={`skill-edge skill-edge-${edge.kind.toLowerCase()} ${active ? "is-active" : "is-faded"}`}
                />
              );
            })}
            {plot.nodes.map((slug) => {
              const p = plot.pos[slug];
              if (!p) return null;
              const isSel = slug === selectedItem.skill;
              const inHood = neighborhood.has(slug);
              const gap = gaps.find((row) => row.skill === slug);
              return (
                <g
                  key={slug}
                  className={`skill-node ${isSel ? "is-selected" : ""} ${inHood ? "is-near" : "is-far"}`}
                  transform={`translate(${p.x}, ${p.y})`}
                >
                  <circle r={isSel ? 9 : 6} className="skill-node-dot" />
                  <text y={isSel ? 26 : 22} className="skill-node-label">
                    {prettySkill(slug)}
                  </text>
                  {gap ? (
                    <text y={isSel ? 42 : 36} className="skill-node-meta">
                      {gap.proficiency == null ? "No evidence" : gap.proficiency.toFixed(2)}
                    </text>
                  ) : null}
                </g>
              );
            })}
          </svg>
          <p className="skill-plot-legend" aria-hidden>
            <span className="is-hard">HARD</span>
            <span className="is-soft">SOFT</span>
            Blockers sit left. Dependents sit right.
          </p>
        </div>
      ) : null}

      {selectedItem ? (
        <div className="skill-neighborhood">
          <Neighborhood label="HARD blockers" items={selectedItem.blockers} empty="None" />
          <Neighborhood label="HARD dependents" items={selectedItem.hard_downstream} empty="None" />
          <Neighborhood label="SOFT preparation" items={selectedItem.preparation_skills} empty="None" />
        </div>
      ) : null}

      <ul className="skill-graph font-mono text-xs">
        {unique.slice(0, 18).map((edge) => {
          const active =
            Boolean(selected) &&
            (selected === edge.from ||
              selected === edge.to ||
              neighborhood.has(edge.from) ||
              neighborhood.has(edge.to));
          return (
            <li
              key={`${edge.kind}-${edge.from}-${edge.to}`}
              className={`edge-row ${active ? "is-active" : "is-faded"}`}
            >
              {prettySkill(edge.from)}
              <span className="mx-2 tracking-[0.14em] text-mist">{edge.kind}</span>
              {prettySkill(edge.to)}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Neighborhood({ label, items, empty }: { label: string; items: string[]; empty: string }) {
  return (
    <div>
      <p className="type-section">{label}</p>
      <p className="mt-2 text-sm text-paper">
        {items.length ? items.map(prettySkill).join(" · ") : <span className="text-mist">{empty}</span>}
      </p>
    </div>
  );
}
