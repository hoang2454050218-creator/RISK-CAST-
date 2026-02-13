# ═══════════════════════════════════════════════════════════════════
# RiskCast V2 — Development Setup Script
# Run this AFTER restarting (when Docker Desktop is running)
# ═══════════════════════════════════════════════════════════════════

Write-Host "`n=== RiskCast V2 Dev Setup ===" -ForegroundColor Cyan

# 1. Check Docker is running
Write-Host "`n[1/5] Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker version --format '{{.Server.Version}}' 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: Docker is not running. Please start Docker Desktop and wait for it to initialize." -ForegroundColor Red
        Write-Host "  Then run this script again." -ForegroundColor Red
        exit 1
    }
    Write-Host "  Docker OK: v$dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Docker not found. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# 2. Start PostgreSQL + Redis
Write-Host "`n[2/5] Starting PostgreSQL + Redis..." -ForegroundColor Yellow
Set-Location $PSScriptRoot\..
docker compose up -d postgres redis
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Failed to start containers" -ForegroundColor Red
    exit 1
}

# Wait for PostgreSQL to be ready
Write-Host "  Waiting for PostgreSQL..." -ForegroundColor Yellow
$retries = 0
$maxRetries = 30
while ($retries -lt $maxRetries) {
    $ready = docker exec riskcast-postgres pg_isready -U riskcast -d riskcast 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  PostgreSQL ready!" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 2
    $retries++
}
if ($retries -eq $maxRetries) {
    Write-Host "  ERROR: PostgreSQL did not start in time" -ForegroundColor Red
    exit 1
}

# Wait for Redis to be ready
Write-Host "  Checking Redis..." -ForegroundColor Yellow
docker exec riskcast-redis redis-cli ping 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Redis ready!" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Redis not responding, continuing anyway..." -ForegroundColor Yellow
}

# 3. Start backend (creates tables automatically via init_db)
Write-Host "`n[3/5] Starting backend to create tables..." -ForegroundColor Yellow
Write-Host "  Backend will create all V2 tables via init_db()..." -ForegroundColor Gray

# Quick health check — start uvicorn briefly to init DB tables
$env:ENVIRONMENT = "development"
$proc = Start-Process python -ArgumentList "-c", "import asyncio; from riskcast.db.engine import init_db; asyncio.run(init_db()); print('Tables created!')" -NoNewWindow -PassThru -Wait
if ($proc.ExitCode -eq 0) {
    Write-Host "  V2 tables created!" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Table creation may have failed. Backend startup will retry." -ForegroundColor Yellow
}

# 4. Run seed data
Write-Host "`n[4/5] Seeding database with Vietnamese SME logistics data..." -ForegroundColor Yellow
python -m riskcast.scripts.seed
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Seed complete!" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Seed may have failed. Check error above." -ForegroundColor Yellow
}

# 5. Summary
Write-Host "`n[5/5] Setup Complete!" -ForegroundColor Green
Write-Host "`n=== Next Steps ===" -ForegroundColor Cyan
Write-Host "  1. Start backend:" -ForegroundColor White
Write-Host "     python -m uvicorn riskcast.main:app --host 0.0.0.0 --port 8001 --reload" -ForegroundColor Gray
Write-Host "  2. Start frontend:" -ForegroundColor White
Write-Host "     cd frontend && npm run dev" -ForegroundColor Gray
Write-Host "`n=== Login Accounts ===" -ForegroundColor Cyan
Write-Host "  Admin:    admin@vietlog.vn / vietlog2026" -ForegroundColor White
Write-Host "  Test:     hoangpro268@gmail.com / Hoang2672004" -ForegroundColor White
Write-Host "  Analyst:  analyst@riskcast.io / demo" -ForegroundColor White
Write-Host "  Manager:  manager@riskcast.io / demo" -ForegroundColor White
Write-Host "`n=== Services ===" -ForegroundColor Cyan
Write-Host "  Backend:    http://localhost:8001" -ForegroundColor White
Write-Host "  Frontend:   http://localhost:5175" -ForegroundColor White
Write-Host "  PostgreSQL: localhost:5432 (riskcast/riskcast)" -ForegroundColor White
Write-Host "  Redis:      localhost:6379" -ForegroundColor White
Write-Host "  API Docs:   http://localhost:8001/docs" -ForegroundColor White
Write-Host ""
