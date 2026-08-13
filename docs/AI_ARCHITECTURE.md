# AI / ML architecture boundary (Slice 2.1)

PathFinder's **deterministic domain core is authoritative**.
AI is a later interpreter and retriever, not a source of ontology.

This slice does **not** integrate an LLM or require embeddings.

## Where AI will enter

```
AI INPUT
    → AI OUTPUT
    → VALIDATION against ontology/catalog
    → DETERMINISTIC DOMAIN LOGIC
    → persisted learner/path state
```

| Capability | AI role | Authoritative owner |
|---|---|---|
| 1. Structured learner-state intelligence | none required | evidence fusion + gap engine |
| 2. Semantic resource retrieval | optional embeddings behind `SemanticRetriever` | structured retrieval + scoring |
| 3. Resume/profile extraction | LLM/NER proposes skill mentions | canonical skill resolver |
| 4. Natural-language explanation | LLM rewrites structured `PathCause` facts | `explanation.py` + `path/causality.py` |
| 5. Assessment interpretation | LLM may summarize free-text | scored items + fusion |
| 6. Adaptive reasoning | LLM may suggest *why* to mutate | adaptation engine (not built) |

## AI INPUT

Allowed inputs, when added later:

- learner gap profile (already computed)
- catalog rows (ids, titles, descriptions)
- resume text / chat text
- assessment free-text answers
- structured `PathCause` facts

Forbidden as AI input-of-record:

- invented skill slugs
- invented resource URLs
- invented role requirements

## AI OUTPUT

Allowed outputs:

- candidate skill mentions (`"PyTorch"`, `"docker compose"`)
- candidate resource ranking hints (similarity scores)
- prose explanations constrained to provided facts
- extraction confidence

Never allowed as direct writes:

- new `skills` rows
- new `learning_resources` rows
- new prerequisites
- new role_skills
- new URLs

## VALIDATION

Every AI mention must resolve to a canonical entity:

```
"PyTorch" → neural_networks (skill) and/or pytorch-basics (resource)
```

Resolver rules:

1. Exact slug match
2. Canonical name match (case-insensitive)
3. Documented alias table (future)
4. Else **reject or ask for clarification**

If resolution fails, the system must not create an ontology node.

Embeddings, when added:

- live in a side table keyed by `learning_resources.id`
- optional
- if the provider is down, `SemanticRetriever` keeps the constant fallback
- must not change eligibility or HARD sequencing

## DETERMINISTIC DOMAIN LOGIC

After validation, only code may:

- fuse evidence
- compute gaps, blockers, actions
- retrieve, score, sequence, pack
- persist `learning_paths` / `path_items`

A high embedding similarity cannot select a resource with `role_importance = 0`.
An LLM cannot mark an UNKNOWN prerequisite as mastered.
UNKNOWN produces a verification gate, not a fabricated course or a numeric gap of 0.

Future assessment results enter only through `AssessmentResult` → normalized evidence → fusion → eligibility recompute. Slice 2.2 defines that contract and does not score questions.

## Explanation grounding

Current explanations are generated from:

- gap / attainment / action
- role importance
- resource coverage
- prerequisite state
- duration / weekly hours
- learning style
- sequence position (`PathCause`)

Future LLM copy may only paraphrase those fields.
It must not add claims that are absent from `score_breakdown` + `causality`.

## Safety answers

| Question | Answer |
|---|---|
| Where is the AI? | Not in Slice 2.1. Interfaces exist; providers do not. |
| Can the AI hallucinate a course? | No. Path items must be catalog slugs. Unresolved titles are rejected. |
| Can the AI invent a skill? | No. Mentions that do not resolve to `skills.slug` are rejected. |
| Can it explain without an LLM? | Yes. `PathCause` + deterministic explanation strings. |
| What if Cybersecurity is selected with no evidence? | Verification gates for UNKNOWN role competencies. Not an empty path. |
| Can a blocked resource appear as ready-to-start? | No. It is `WAITING_FOR_VERIFICATION` or `WAITING_FOR_REMEDIATION`. |
