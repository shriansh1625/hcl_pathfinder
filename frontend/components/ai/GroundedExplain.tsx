"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useIntelligence } from "@/lib/session";
import type { AIExplain, AIExplainIntent } from "@/lib/types";

export function GroundedExplain({
  intent,
  skill,
  resource,
  query,
  triggerLabel,
  testId,
}: {
  intent: AIExplainIntent;
  skill?: string;
  resource?: string;
  query?: string;
  triggerLabel: string;
  testId?: string;
}) {
  const { learnerId } = useIntelligence();
  const [open, setOpen] = useState(false);
  const [showFacts, setShowFacts] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AIExplain | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  async function run() {
    if (!learnerId) return;
    setOpen(true);
    setUnavailable(false);
    setLoading(true);
    try {
      const body = await api.explain(learnerId, { intent, skill, resource, query });
      setResult(body);
    } catch {
      setResult(null);
      setUnavailable(true);
    } finally {
      setLoading(false);
    }
  }

  if (!learnerId) return null;

  return (
    <div className="grounded-surface" data-testid={testId}>
      <button type="button" className="grounded-trigger" onClick={() => void run()}>
        {triggerLabel}
      </button>
      {open ? (
        <div className="grounded-body">
          {loading ? <p className="grounded-loading">Generating explanation…</p> : null}
          {!loading && unavailable ? (
            <p className="text-sm text-mist">
              Explanation is unavailable. The diagnosis and path above are unchanged.
            </p>
          ) : null}
          {!loading && result ? (
            <>
              <p className="grounded-answer">{result.answer}</p>
              <button
                type="button"
                className="grounded-why"
                onClick={() => setShowFacts((current) => !current)}
              >
                {showFacts ? "Hide facts" : "Why?"}
              </button>
              {showFacts ? (
                <div className="grounded-facts" data-testid="grounded-in">
                  <p className="grounded-kicker">Grounded in</p>
                  <ul>
                    {result.facts
                      .filter((fact) => !fact.id.endsWith(".slug"))
                      .map((fact) => (
                      <li key={fact.id}>
                        <span>{fact.label}</span>
                        <span className="font-mono tabular-nums">{fact.value}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
