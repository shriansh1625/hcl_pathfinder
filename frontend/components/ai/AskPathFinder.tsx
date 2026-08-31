"use client";

import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { useIntelligence } from "@/lib/session";
import type { AIExplain } from "@/lib/types";

const CONTEXT_PROMPTS = [
  "Why am I learning this skill?",
  "What changed after my assessment?",
  "What should I do this week?",
];

export function AskPathFinder() {
  const { learnerId, roleName, activePath, gaps } = useIntelligence();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [showFacts, setShowFacts] = useState(false);
  const [result, setResult] = useState<AIExplain | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  const topGap = gaps.find((item) => item.attainment === "GAP" || item.attainment === "UNKNOWN");

  async function ask(text: string) {
    if (!learnerId || !text.trim()) return;
    setLoading(true);
    setUnavailable(false);
    setShowFacts(false);
    try {
      const body = await api.explain(learnerId, { intent: "QUERY", query: text.trim() });
      setResult(body);
    } catch {
      setResult(null);
      setUnavailable(true);
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void ask(query);
  }

  if (!learnerId) return null;

  return (
    <section className="ask-analyst" data-testid="ask-pathfinder" aria-label="Ask PathFinder">
      <div className="ask-analyst-head">
        <div>
          <p className="grounded-kicker">Your learning guide</p>
          <h2 className="mt-1 font-display text-xl text-paper">Ask PathFinder</h2>
        </div>
        <div className="ask-context-chips" aria-label="Verified context">
          <span>{roleName}</span>
          {activePath ? <span>Path V{activePath.version}</span> : null}
          {topGap ? <span>Gap: {topGap.name || topGap.skill}</span> : null}
        </div>
      </div>
      <form className="ask-analyst-form" onSubmit={onSubmit}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          maxLength={500}
          placeholder="Ask about a skill, blocker, or path change…"
          className="ask-analyst-input"
          aria-label="Question about your path"
        />
        <button type="submit" className="ask-analyst-submit" disabled={loading || !query.trim()}>
          {loading ? "…" : "Ask"}
        </button>
      </form>
      <div className="ask-context-actions">
        {CONTEXT_PROMPTS.map((item) => (
          <button
            key={item}
            type="button"
            className="ask-context-link"
            onClick={() => {
              setQuery(item);
              void ask(item);
            }}
          >
            {item}
          </button>
        ))}
      </div>
      {loading ? <p className="grounded-loading mt-4">Reading your verified state…</p> : null}
      {!loading && unavailable ? (
        <p className="mt-4 text-sm text-mist">
          Explanation is unavailable. PathFinder still diagnoses and sequences from evidence.
        </p>
      ) : null}
      {!loading && result ? (
        <div className="grounded-body mt-4">
          <p className="grounded-answer">{result.answer}</p>
          <button type="button" className="grounded-why" onClick={() => setShowFacts((current) => !current)}>
            {showFacts ? "Hide grounded facts" : "Grounded in"}
          </button>
          {showFacts ? (
            <div className="grounded-facts" data-testid="ask-grounded-in">
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
        </div>
      ) : null}
    </section>
  );
}
