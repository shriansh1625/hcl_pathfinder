"use client";

export function IntelligenceExplainer({ compact = false }: { compact?: boolean }) {
  return (
    <section className={`intel-explainer ${compact ? "is-compact" : ""}`} data-testid="intelligence-explainer">
      <p className="type-section">How recommendations work</p>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-mist">
        PathFinder diagnoses what you know, what your target role still requires, and changes your path when new
        evidence changes the diagnosis. The LLM explains — it does not decide.
      </p>
      <ol className="intel-layers mt-4">
        <li className="intel-layer is-deterministic">
          <p className="intel-layer-kind">Deterministic engine</p>
          <p className="intel-layer-detail">
            Evidence fusion, role-relative gaps, HARD/SOFT dependencies, eligibility, causal sequencing, adaptation.
          </p>
        </li>
        <li className="intel-layer is-semantic">
          <p className="intel-layer-kind">Semantic signal (BGE)</p>
          <p className="intel-layer-detail">
            Bounded retrieval relevance — one weighted factor in resource scoring, never the sole selector.
          </p>
        </li>
        <li className="intel-layer is-llm">
          <p className="intel-layer-kind">Grounded LLM</p>
          <p className="intel-layer-detail">
            Explains verified state only. Cannot mutate proficiency, prerequisites, or path decisions.
          </p>
        </li>
      </ol>
    </section>
  );
}
