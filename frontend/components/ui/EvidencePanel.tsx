"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { prettySkill } from "@/lib/status";
import type { EvidenceRow, FusedSkill } from "@/lib/types";

export function EvidencePanel({
  skill,
  fused,
  learnerId,
}: {
  skill: string;
  fused: FusedSkill | null;
  learnerId: string | null;
}) {
  const [rows, setRows] = useState<EvidenceRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!learnerId || !skill) return;
    setLoading(true);
    setError(null);
    api
      .evidence(learnerId, skill)
      .then(setRows)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [learnerId, skill]);

  if (!fused && !rows.length && !loading) return null;

  return (
    <section className="evidence-panel" data-testid={`evidence-panel-${skill}`} aria-label={`Evidence for ${prettySkill(skill)}`}>
      <p className="evidence-panel-skill">{prettySkill(skill)}</p>

      <div className="evidence-panel-body">
        <p className="evidence-panel-label">Evidence</p>
        {loading ? <p className="text-xs text-mist">Loading evidence from backend…</p> : null}
        {error ? (
          <p className="text-xs text-rose-100">
            Could not load evidence rows. {error} Try again from Overview after the API recovers.
          </p>
        ) : null}
        {!loading && !rows.length ? <p className="text-xs text-mist">No evidence rows stored for this skill.</p> : null}
        <ul className="evidence-panel-rows">
          {rows.map((row) => (
            <li key={row.id} className="evidence-panel-row">
              <p className="evidence-panel-source">{row.source.replaceAll("_", " ")}</p>
              <p className="font-mono text-sm tabular-nums text-paper">{row.observed_level.toFixed(2)}</p>
            </li>
          ))}
        </ul>

        {fused ? (
          <dl className="evidence-panel-summary">
            <div>
              <dt>Fused</dt>
              <dd className="font-mono tabular-nums">
                {fused.proficiency === null ? "—" : fused.proficiency.toFixed(2)}
              </dd>
            </div>
            {fused.dominant_source ? (
              <div>
                <dt>Dominant source</dt>
                <dd>{fused.dominant_source.replaceAll("_", " ")}</dd>
              </div>
            ) : null}
          </dl>
        ) : null}

        {fused?.conflict ? (
          <div className="evidence-panel-conflict" data-testid="evidence-conflict">
            <p className="evidence-panel-conflict-title">CONFLICT DETECTED</p>
            <p className="text-xs text-mist">
              Multiple evidence sources disagree. Fusion uses stored backend weights — the dominant source
              carries greater influence.
            </p>
          </div>
        ) : null}
      </div>
    </section>
  );
}
