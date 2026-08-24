# PathFinder — Final Submission Readiness

## Product summary

PathFinder is an adaptive career-path intelligence product for HCLTech AMPlified Round 2. It diagnoses learner-to-career gaps from evidence, sequences a personalized learning path, proves competency through assessments, and adapts the path when new evidence changes the diagnosis.

## Architecture summary

- Frontend: Next.js 15 production app (npm run build + next start)
- Backend: FastAPI + SQLAlchemy + Alembic
- Data: YAML ontology (8 careers, 47 skills, 62 active resources, 4 canonical assessments)
- Intelligence: Deterministic gap engine, causal recommendation, BGE semantic retrieval (optional), grounded LLM explanations (optional)
- State: PostgreSQL via Docker Compose (localhost:5433)

## Supported careers

AI/ML Engineer, Cybersecurity Analyst, Backend Developer, Frontend Developer, Data Engineer, Cloud Architect, DevOps Engineer, Product Manager

## AI/ML stack

| Layer | Technology |
|---|---|
| Gap diagnosis | Deterministic evidence fusion + gap engine |
| Recommendations | Weighted scoring + causal selection + prerequisite eligibility |
| Semantic relevance | BGE-small-en-v1.5 via fastembed (5% weight, optional) |
| Explanations | Grounded LLM (Groq/OpenAI-compatible, optional) |
| Benchmark | 20-scenario intelligence benchmark (frozen expectations) |

## Benchmark result

20/20 PASS — python scripts/intelligence_benchmark.py

## Test result

| Suite | Result |
|---|---|
| Backend pytest | 218 passed, 1 skipped |
| Frontend vitest | 48 passed |
| API release gate | 14/14 PASS |
| Career proof | 5/5 PASS |
| Browser release gate | 48/48 PASS |
| Production build | PASS |

## Browser result

Canonical QA: scripts/release_gate_workspace_qa.mjs
Screenshot package: scripts/capture_submission_screenshots.mjs
Failure matrix: scripts/failure_matrix_qa.mjs
Accessibility audit: scripts/accessibility_audit.mjs

## Demo startup

docker compose up -d db
cd backend && alembic upgrade head && cd ..
python scripts/validate_ontology.py && python scripts/seed.py
cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run build && PORT=3002 npm run start

Open http://127.0.0.1:3002

## Known limitations

- Semantic retrieval requires fastembed in the Python venv.
- Grounded AI explanations require PATHFINDER_AI_* env vars.
- Screenshot capture requires Playwright (cd .tmp-pw && npm install).

## Judge FAQ

Q: Is this multi-career? A: Eight careers with distinct gaps and paths.
Q: Does the path change for real? A: Yes — assessment/progress triggers backend adaptation with V1/V2 history.
Q: Is AI making recommendations? A: No — deterministic engine; AI is optional explanations only.

## 90-second demo path

1. Goal NL intake (15s)
2. Career Explorer (15s)
3. Build path to workspace (10s)
4. Dashboard + WHY drawer (15s)
5. Assessment to result (15s)
6. Path V2 cascade (15s)
7. History + judge rail (5s)