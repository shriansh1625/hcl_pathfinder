# PathFinder — start full local stack (Windows)
# Usage: .\scripts\start_stack.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host ">> Starting PostgreSQL (Docker)..." -ForegroundColor Cyan
docker compose up -d db
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$ready = $false
for ($i = 0; $i -lt 45; $i++) {
    $health = docker inspect --format='{{.State.Health.Status}}' pathfinder-db 2>$null
    if ($health -eq "healthy") { $ready = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $ready) {
    Write-Host "Postgres did not become healthy in time." -ForegroundColor Red
    exit 1
}

$env:DATABASE_URL = "postgresql+psycopg2://pathfinder:pathfinder@localhost:5433/pathfinder"
$env:PYTHONPATH = Join-Path $Root "backend"

Write-Host ">> Migrating database..." -ForegroundColor Cyan
Push-Location backend
python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host ">> Seeding ontology (idempotent)..." -ForegroundColor Cyan
python scripts/seed.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ">> Starting API on http://localhost:8000 ..." -ForegroundColor Cyan
Write-Host "   In another terminal: cd frontend && npm run dev" -ForegroundColor Yellow
Write-Host "   Open http://localhost:3000/#get-started" -ForegroundColor Yellow
Push-Location backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
