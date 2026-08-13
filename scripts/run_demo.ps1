# PathFinder Slice 3.2 — one-command judge demo (Windows)
# Usage: .\scripts\run_demo.ps1
# Resets only the dedicated demo learner namespace; does not destroy the database.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step($msg) {
    Write-Host ">> $msg" -ForegroundColor Cyan
}

$sw = [System.Diagnostics.Stopwatch]::StartNew()

Write-Step "Checking Docker..."
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker is required but not found in PATH." -ForegroundColor Red
    exit 1
}

Write-Step "Starting Postgres (docker compose)..."
docker compose up -d db | Out-Null

$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    $health = docker inspect --format='{{.State.Health.Status}}' pathfinder-db 2>$null
    if ($health -eq "healthy") { $ready = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $ready) {
    Write-Host "Postgres did not become healthy in time." -ForegroundColor Red
    exit 1
}

$env:DATABASE_URL = "postgresql+psycopg://pathfinder:pathfinder@localhost:5433/pathfinder"

Write-Step "Running migrations..."
Push-Location backend
python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }

Write-Step "Seeding ontology (includes assessment fingerprints)..."
python -c "from app.db.session import SessionLocal; from app.db.seed import seed_ontology; seed_ontology(SessionLocal())"
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

$coldMs = $sw.ElapsedMilliseconds
Write-Step "Cold start through seed: $([math]::Round($coldMs/1000, 1))s"

Write-Step "Executing primary judge demo..."
$demoSw = [System.Diagnostics.Stopwatch]::StartNew()
python scripts/judge_demo.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$warmMs = $demoSw.ElapsedMilliseconds

Write-Host ""
Write-Host "TIMING cold_start=${coldMs}ms warm_demo=${warmMs}ms" -ForegroundColor Green
Write-Host "Manual steps required: 1 (this script)" -ForegroundColor Green
