# PathFinder

Adaptive Career Path Intelligence for HCLTech AMPlified Season 1 Round 2.

PathFinder diagnoses the **learner-to-career gap**, then (in later slices) sequences a path, tests the learner, and adapts from evidence.

This repository is a **clean-room Round 2 product**. It does not depend on any prior challenge work.

## Current scope — Slice 0 (foundation only)

Implemented:

- Git-ready monorepo
- FastAPI backend skeleton
- Minimal Next.js app (no product UI)
- PostgreSQL via Docker
- Alembic migrations
- Canonical skill / role / resource / assessment ontology in YAML
- Idempotent seed with validation (including HARD prerequisite cycle detection)
- Domain schema for evidence, UNKNOWN skill state, versioned paths, and adaptation events

**Not implemented yet:** recommendation engine, sequencing, assessments runtime, adaptation engine, resume parsing, LLM calls, skill-graph UI, onboarding.

## Product thesis

Course recommenders answer “what should I take?”

PathFinder is being built to answer: what capabilities am I missing for a target career, what should I learn first, why now, how do I prove it, and how should the path change when evidence arrives?

## Architecture (Slice 0)

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
cd backend && uvicorn app.main:app --port 8000
cd frontend && npm run dev
cd frontend && npm run build
```

## Project structure

See `docs/ARCHITECTURE.md` and `docs/DATA_MODEL.md`.
