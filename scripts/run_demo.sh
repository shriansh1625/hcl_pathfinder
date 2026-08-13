#!/usr/bin/env bash
# PathFinder Slice 3.2 — one-command judge demo (Unix)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo ">> Checking Docker..."
command -v docker >/dev/null

echo ">> Starting Postgres..."
docker compose up -d db

for _ in $(seq 1 30); do
  health="$(docker inspect --format='{{.State.Health.Status}}' pathfinder-db 2>/dev/null || true)"
  if [ "$health" = "healthy" ]; then break; fi
  sleep 2
done

export DATABASE_URL="postgresql+psycopg://pathfinder:pathfinder@localhost:5433/pathfinder"

echo ">> Running migrations..."
(cd backend && python -m alembic upgrade head)

echo ">> Seeding ontology..."
(cd backend && python -c "from app.db.session import SessionLocal; from app.db.seed import seed_ontology; seed_ontology(SessionLocal())")

echo ">> Executing primary judge demo..."
python scripts/judge_demo.py
