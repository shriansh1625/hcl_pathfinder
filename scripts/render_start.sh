#!/usr/bin/env bash
# Render free tier: migrate + seed on each start (preDeployCommand requires paid plan).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
alembic upgrade head
cd "$ROOT"
python scripts/seed.py
cd "$ROOT/backend"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:?}"
