# PathFinder — Reproducibility & Deployment Hardening Report

**Date:** 2026-08-30
**Scope:** Teammate / fresh Windows / judge / production deployment readiness
**Intelligence:** No changes to deterministic engines, fusion, scoring, or benchmarks.

---

## 1. Environment

| Check | Status | Notes |
|-------|--------|-------|
| `.env.local` local-only | **PASS** | Gitignored (`git check-ignore .env.local`) |
| `.env` absent | **PASS** | No repo-root `.env` file |
| `.env.example` accurate | **PASS** | Updated with CORS, AI, semantic, QA vars |
| `frontend/.env.example` | **PASS** | `NEXT_PUBLIC_API_URL` + optional `PORT` |
| `DATABASE_URL` configurable | **PASS** | Via `.env.local`; default in code has no host port |
| `NEXT_PUBLIC_API_URL` configurable | **PASS** | Required for `next build` (no hardcoded fallback) |
| AI credentials env-only | **PASS** | `PATHFINDER_AI_API_KEY` in settings only |
| Semantic settings documented | **PASS** | README + `.env.example` |
| No hardcoded ports in app logic | **PASS** | Removed from `config.py`, `main.py`, `next.config.ts`, `package.json` dev script |

**Application changes:**
- `backend/app/core/config.py` — no `:5433` / `:8000` defaults in connection strings
- `backend/app/main.py` — `PATHFINDER_CORS_ORIGINS` env (comma-separated)
- `frontend/next.config.ts` — fails fast if `NEXT_PUBLIC_API_URL` unset
- `frontend/package.json` — `next dev` uses `PORT` env, not fixed `--port 3000`

Ports remain in **docker-compose.yml**, **`.env.example`**, **README**, and **script usage comments** only.

---

## 2. Fresh machine setup

Documented order in `README.md`:

```text
1. cp .env.example .env.local && cp frontend/.env.example frontend/.env.local
2. docker compose up -d db
3. cd backend && alembic upgrade head
4. python scripts/validate_ontology.py && python scripts/seed.py
5. pip install -r backend/requirements.txt && uvicorn app.main:app --port 8000
6. cd frontend && npm install && npm run build && PORT=3002 npm run start
```

**Official demo path:** `npm run build` + `next start` (not `next dev`).

---

## 3. Dependencies

| Package | Location | Install |
|---------|----------|---------|
| **fastembed** | `backend/requirements.txt` | `pip install -r backend/requirements.txt` |
| **Playwright** | `.tmp-pw/package.json` (local) | `cd .tmp-pw && npm install` |
| Frontend | `frontend/package.json` | `npm install` |
| Backend | `backend/requirements.txt` | pip in venv |

No hidden assumptions beyond copying env examples and Docker for Postgres.

---

## 4. Database (live run)

```bash
alembic upgrade head
python scripts/seed.py
```

**Output:**

```text
Seed complete: 47 skills, 8 roles, 58 relationships, 62 resources, 4 assessments.
```

**API meta verification** (`scripts/api_smoke_test.py`):

| Entity | Expected | Actual |
|--------|----------|--------|
| skills | 47 | 47 |
| roles | 8 | 8 |
| skill_relationships | 58 | 58 |
| resources | 62 | 62 |
| assessments | 4 | 4 |

---

## 5. API (live run)

**Command:**

```bash
PATHFINDER_API_URL=http://127.0.0.1:8000 python scripts/api_smoke_test.py
```

**Result:** **19/19 PASS**

Endpoints exercised: `/health`, `/ready`, `/v1/roles`, `/v1/meta/ontology`, intake, learner CRUD, evidence, gaps, paths, progress, dashboard, path-timeline, AI explain, assessments.

---

## 6. Repository hygiene

| Search | Finding |
|--------|---------|
| API keys in source | **None** (`sk-` pattern clean) |
| `.env` / `.env.local` in repo | **Absent** (local copies gitignored) |
| Cursor metadata paths | **None** in source |
| Machine-specific paths | **None** in application code |
| Debug artifacts | `artifacts/assessment-debug/` added to `.gitignore` |

Legitimate docs and example commands retain localhost URLs for judge convenience.

---

## 7. README

**Updated** `README.md` with: Problem, Solution, Architecture, AI/ML, Semantic retrieval, Grounded AI, Multi-career, Adaptive paths, Setup, Environment, Database, Backend, Frontend, Production demo, Benchmark, Browser QA, Screenshots, Judge demo, Security.

---

## 8. Security

| Check | Status |
|-------|--------|
| `.env.local` untracked | PASS |
| No key in source | PASS |
| No key in committed docs | PASS |
| AI via env only | PASS |

---

## 9. Final environment test (executed)

| Step | Result |
|------|--------|
| Docker Postgres | Running |
| `alembic upgrade head` | OK |
| `python scripts/seed.py` | OK (counts above) |
| Backend `:8000` | Running (pre-existing instance) |
| `npm run build` | PASS |
| `PORT=3005 npm run start` | PASS — onboarding HTML + `/health` proxy 200 |
| `api_smoke_test.py` | 19/19 |
| `pytest -q` | 218 passed, 1 skipped |

---

## 10. Exact commands (copy-paste)

```powershell
# Windows PowerShell — from repo root
cp .env.example .env.local
cp frontend\.env.example frontend\.env.local

docker compose up -d db
cd backend
pip install -r requirements.txt
alembic upgrade head
cd ..
python scripts\validate_ontology.py
python scripts\seed.py

# Terminal 1 — API
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — production UI
cd frontend
npm install
npm run build
$env:PORT=3002; npm run start

# Verify
$env:PATHFINDER_API_URL="http://127.0.0.1:8000"
python scripts\api_smoke_test.py
python scripts\intelligence_benchmark.py
python -m pytest -q
cd frontend; npm test
```

---

## Git

No commit, push, or stage performed.
