# PathFinder

Adaptive Career Path Intelligence for HCLTech AMPlified Season 1 Round 2.

PathFinder diagnoses the **learner-to-career gap**, then (in later slices) sequences a path, tests the learner, and adapts from evidence.

This repository is a **clean-room Round 2 product**. It does not depend on any prior challenge work.

## Current scope — Slice 1.1 (career intelligence refinement)

Slice 0 foundation plus a deterministic gap engine:

- Evidence ingest (append-only)
- Weighted fusion with reliability, observer confidence, and recency
- Evidence state vs target attainment (`target_met` only when proficiency ≥ target)
- Separate gap priority, verification priority, and immediate action
- HARD blockers vs SOFT preparation vs RELATED
- Explainable gap reasons (no LLM)

**Not implemented yet:** resource recommendation, embeddings, sequencing, assessment runtime, adaptation, resume parsing, product UI.

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

API: http://localhost:8000/health  
Frontend: http://localhost:3000  
Postgres: localhost:5433 (user/password/db: `pathfinder`)

Copy `.env.example` to `.env` only if you need to override defaults. Do not commit `.env`.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://pathfinder:pathfinder@localhost:5433/pathfinder` | SQLAlchemy URL |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8000` | API bind |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Frontend API base (unused in Slice 0 UI) |

## Commands

```bash
docker compose up -d db
cd backend && alembic upgrade head && cd ..
python scripts/validate_ontology.py
python scripts/seed.py
python -m pytest
# Slice 1 verification
# POST /v1/learners
# POST /v1/learners/{id}/evidence
# GET  /v1/learners/{id}/skills
# GET  /v1/learners/{id}/roles/{role}/gaps
# GET  /v1/roles/{role}/competencies
cd backend && uvicorn app.main:app --port 8000
cd frontend && npm run dev
cd frontend && npm run build
```

## Project structure

See `docs/ARCHITECTURE.md` and `docs/DATA_MODEL.md`.
