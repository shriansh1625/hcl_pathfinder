# PathFinder

Adaptive Career Path Intelligence for HCLTech AMPlified Season 1 Round 2.

PathFinder diagnoses the **learner-to-career gap**, then (in later slices) sequences a path, tests the learner, and adapts from evidence.

This repository is a **clean-room Round 2 product**. It does not depend on any prior challenge work.

## Current scope — Slice 2.1 (recommendation forensics)

Slice 1.1 gap engine plus Slice 2 personalized paths plus Slice 2.1 causality forensics.

- Structured resource retrieval (structured filter + optional local embedding relevance)
- Explainable resource scoring
- HARD/UNKNOWN prerequisite eligibility
- Dependency-aware sequencing and weekly packing
- Versioned `learning_paths` / `path_items`
- Causal selection (score is not sufficient)
- Structured `PathCause` metadata and path-quality checks

**Not implemented yet:** assessment runtime, adaptation, resume parsing, LLM, product UI.

## Product thesis

Course recommenders answer “what should I take?”

PathFinder is being built to answer: what capabilities am I missing for a target career, what should I learn first, why now, how do I prove it, and how should the path change when evidence arrives?

## Architecture

```
frontend/     Next.js 15 — placeholder shell only
backend/      FastAPI + SQLAlchemy + Alembic
data/         YAML source of truth (ontology, catalog, assessments)
docs/         Architecture and data model
scripts/      validate + seed
tests/        ontology, schema, and health checks
```

YAML is the human-maintainable source of truth. Postgres is runtime state. Seed upserts by stable UUIDv5(slug) and is safe to re-run.

## Local setup

Requirements: Python 3.11+, Node 20+, Docker.

```bash
# 1. Database
docker compose up -d db

# 2. Backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt

# 3. Migrate + seed
cd backend
alembic upgrade head
cd ..
python scripts/validate_ontology.py
python scripts/seed.py

# 4. API
cd backend
uvicorn app.main:app --reload --port 8000

# 5. Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

**Production demo** (recommended for judges):

```bash
docker compose up -d db
cd backend && alembic upgrade head && cd ..
python scripts/validate_ontology.py && python scripts/seed.py
cd backend && uvicorn app.main:app --port 8000
# separate terminal:
cd frontend && npm run build && PORT=3002 npm run start
```

Set `NEXT_PUBLIC_API_URL` in `.env.local` if the API is not on `http://localhost:8000`. Postgres always maps to **localhost:5433** via Docker Compose.

API: http://localhost:8000/health  
Frontend (dev): http://localhost:3000
Frontend (production demo): http://localhost:3002
Postgres: localhost:5433 (user/password/db: `pathfinder`)

Copy `.env.example` to `.env.local` only if you need to override defaults. Do not commit `.env.local` or create a repo-root `.env` file.

### Submission screenshots

```bash
cd .tmp-pw && npm install
PF_BASE_URL=http://127.0.0.1:3002 node ../scripts/capture_submission_screenshots.mjs
```

Output: `artifacts/submission-screenshots/` (18 desktop + 6 mobile captures). See `FINAL_READINESS.md` for the full judge demo path.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://pathfinder:pathfinder@localhost:5433/pathfinder` | SQLAlchemy URL |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8000` | API bind |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Frontend API base URL (build-time for production) |
| `PF_WEB_PORT` | `3002` | Production `next start` port for demo |

## Commands

```bash
docker compose up -d db
cd backend && alembic upgrade head && cd ..
python scripts/validate_ontology.py
python scripts/seed.py
python -m pytest
# Slice 2
# POST /v1/learners/{id}/paths
# GET  /v1/learners/{id}/paths
# GET  /v1/learners/{id}/paths/{path_id}
# GET  /v1/learners/{id}/roles/{role}/recommendations
cd backend && uvicorn app.main:app --port 8000
cd frontend && npm run dev
cd frontend && npm run build
```

## Project structure

See `docs/ARCHITECTURE.md` and `docs/DATA_MODEL.md`.
