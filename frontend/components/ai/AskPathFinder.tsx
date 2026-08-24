"use client";

import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { useIntelligence } from "@/lib/session";
import type { AIExplain } from "@/lib/types";

const SUGGESTIONS = [
  "Why am I learning statistics?",
  "Why can't I start this?",
  "What changed after my assessment?",
  "What should I do this week?",
  "Why is Python important for this role?",
  "What happens if I prove Docker?",
];

export function AskPathFinder() {
  const { learnerId } = useIntelligence();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [showFacts, setShowFacts] = useState(false);
  const [result, setResult] = useState<AIExplain | null>(null);
  const [unavailable, setUnavailable] = useState(false);

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
    <section className="ask-surface" data-testid="ask-pathfinder" aria-label="Ask PathFinder">
      <p className="grounded-kicker">Asking about your path</p>
      <h2 className="mt-2 font-display text-xl text-paper">Ask PathFinder</h2>
      <p className="mt-1 text-sm text-mist">Questions are answered from your verified state only.</p>
      <form className="mt-4 flex gap-2" onSubmit={onSubmit}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          maxLength={500}
          placeholder="Ask about a skill, resource, or path change"
          className="ask-input min-w-0 flex-1"
          aria-label="Question about your path"
        />
        <button type="submit" className="btn-press border border-line px-3 py-2 text-sm text-paper" disabled={loading}>
          Ask
        </button>
      </form>
      <div className="mt-3 flex flex-wrap gap-2">
        {SUGGESTIONS.map((item) => (
          <button
            key={item}
            type="button"
            className="ask-chip"
            onClick={() => {
              setQuery(item);
              void ask(item);
            }}
          >
            {item}
          </button>
        ))}
      </div>
      {loading ? <p className="grounded-loading mt-4">Generating explanation…</p> : null}
      {!loading && unavailable ? (
        <p className="mt-4 text-sm text-mist">
          Explanation is unavailable. PathFinder still diagnoses and sequences from evidence.
        </p>
      ) : null}
      {!loading && result ? (
        <div className="grounded-body mt-4">
          <p className="grounded-answer">{result.answer}</p>
          <button type="button" className="grounded-why" onClick={() => setShowFacts((current) => !current)}>
            {showFacts ? "Hide facts" : "Why?"}
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
