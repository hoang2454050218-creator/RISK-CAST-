# RISKCAST Quick Verification Script (PowerShell)
# ================================================
# Chạy: .\verify_quick.ps1
#
# Script này kiểm tra nhanh xem hệ thống có sống không.

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     RISKCAST QUICK VERIFICATION                           ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$failed = 0

function Test-Check {
    param (
        [string]$Name,
        [scriptblock]$Test
    )
    try {
        $result = & $Test
        if ($result) {
            Write-Host "  ✓ PASS: $Name" -ForegroundColor Green
            $script:passed++
        } else {
            Write-Host "  ✗ FAIL: $Name" -ForegroundColor Red
            $script:failed++
        }
    } catch {
        Write-Host "  ✗ FAIL: $Name - $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
    }
}

Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray
Write-Host "  PHASE 1: Environment" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

# Check Python
Test-Check "Python installed" {
    $version = python --version 2>&1
    $version -match "Python 3\.(1[1-9]|[2-9]\d)"
}

# Check pip
Test-Check "pip installed" {
    $null = pip --version 2>&1
    $LASTEXITCODE -eq 0
}

# Check app directory
Test-Check "app/ directory exists" {
    Test-Path "app"
}

# Check tests directory  
Test-Check "tests/ directory exists" {
    Test-Path "tests"
}

Write-Host ""
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray
Write-Host "  PHASE 2: Dependencies" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

# Check key packages
$packages = @("fastapi", "pydantic", "sqlalchemy", "httpx", "structlog", "pytest")
foreach ($pkg in $packages) {
    Test-Check "$pkg installed" {
        $null = python -c "import $using:pkg" 2>&1
        $LASTEXITCODE -eq 0
    }
}

Write-Host ""
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray
Write-Host "  PHASE 3: Core Imports" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

# Check core modules can be imported
$modules = @(
    "app.core.config",
    "app.omen.schemas",
    "app.oracle.schemas",
    "app.riskcast.schemas.decision",
    "app.riskcast.service",
    "app.reasoning.engine",
    "app.audit.schemas",
    "app.alerter.service"
)

foreach ($mod in $modules) {
    $shortName = $mod.Split('.')[-1]
    Test-Check "import $shortName" {
        $null = python -c "import $using:mod" 2>&1
        $LASTEXITCODE -eq 0
    }
}

Write-Host ""
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray
Write-Host "  PHASE 4: FastAPI App" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check "FastAPI app loads" {
    $result = python -c "from app.main import app; print('OK')" 2>&1
    $result -contains "OK"
}

Write-Host ""
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray
Write-Host "  PHASE 5: Quick Tests" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check "Pytest runs without import errors" {
    $result = python -m pytest --collect-only -q 2>&1
    -not ($result -match "ImportError|ModuleNotFoundError|SyntaxError")
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  RESULTS:" -ForegroundColor White
Write-Host "  ─────────" -ForegroundColor Gray
Write-Host "  Passed: $passed" -ForegroundColor Green
Write-Host "  Failed: $failed" -ForegroundColor Red
Write-Host ""

if ($failed -eq 0) {
    Write-Host "  ╔═══════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "  ║  ✓ SYSTEM IS ALIVE! Code is not dead.                 ║" -ForegroundColor Green
    Write-Host "  ╚═══════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Next step: Run full verification with:" -ForegroundColor Cyan
    Write-Host "    python verify_deployment.py" -ForegroundColor White
    exit 0
} else {
    Write-Host "  ╔═══════════════════════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "  ║  ✗ SYSTEM HAS ISSUES - See failures above             ║" -ForegroundColor Red
    Write-Host "  ╚═══════════════════════════════════════════════════════╝" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Fix the issues above, then run again." -ForegroundColor Yellow
    exit 1
}
