Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$originalLocation = Get-Location

$pytestRoot = "D:\finai-pytest\v23"

try {
    Set-Location $repositoryRoot

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Version 2.3 verification" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    $env:EXECUTION_MODE = "sandbox"
    $env:ALPACA_EXECUTION_ENABLED = "false"
    $env:ALPACA_TRADE_STREAM_ENABLED = "false"
    $env:ALPACA_RECONCILIATION_ENABLED = "false"
    $env:ALPACA_ORDER_DISCOVERY_ENABLED = "false"

    Write-Host ""
    Write-Host "Checking Python..." -ForegroundColor Cyan

    python --version

    if ($LASTEXITCODE -ne 0) {
        throw "Python check failed."
    }

    Write-Host ""
    Write-Host "Compiling..." -ForegroundColor Cyan

    python -m compileall -q src tests migrations scripts

    if ($LASTEXITCODE -ne 0) {
        throw "Compilation failed."
    }

    Write-Host ""
    Write-Host "Running Ruff..." -ForegroundColor Cyan

    python -m ruff check src tests migrations scripts

    if ($LASTEXITCODE -ne 0) {
        throw "Ruff failed."
    }

    Write-Host ""
    Write-Host "Starting infrastructure..." -ForegroundColor Cyan

    docker compose up -d postgres mlflow

    if ($LASTEXITCODE -ne 0) {
        throw "Infrastructure startup failed."
    }

    Write-Host ""
    Write-Host "Waiting for PostgreSQL..." -ForegroundColor Cyan

    $databaseReady = $false

    for ($attempt = 1; $attempt -le 30; $attempt++) {
        docker compose exec -T postgres pg_isready -U finai -d finai 2>$null

        if ($LASTEXITCODE -eq 0) {
            $databaseReady = $true
            break
        }

        Start-Sleep -Seconds 2
    }

    if (-not $databaseReady) {
        throw "PostgreSQL did not become ready."
    }

    Write-Host ""
    Write-Host "Checking Alembic heads..." -ForegroundColor Cyan

    $heads = @(alembic heads)

    if ($LASTEXITCODE -ne 0) {
        throw "Alembic heads check failed."
    }

    $headCount = @(
        $heads |
        Where-Object {
            $_ -match "\(head\)"
        }
    ).Count

    if ($headCount -ne 1) {
        throw "Expected one Alembic head, found $headCount."
    }

    Write-Host ""
    Write-Host "Applying migrations..." -ForegroundColor Cyan

    alembic upgrade head

    if ($LASTEXITCODE -ne 0) {
        throw "Alembic upgrade failed."
    }

    if (-not (Test-Path $pytestRoot)) {
        New-Item `
            -ItemType Directory `
            -Path $pytestRoot `
            -Force |
            Out-Null
    }

    $unitTemp = Join-Path $pytestRoot "unit"
    $integrationTemp = Join-Path $pytestRoot "integration"

    if (Test-Path $unitTemp) {
        Remove-Item `
            $unitTemp `
            -Recurse `
            -Force `
            -ErrorAction SilentlyContinue
    }

    if (Test-Path $integrationTemp) {
        Remove-Item `
            $integrationTemp `
            -Recurse `
            -Force `
            -ErrorAction SilentlyContinue
    }

    Write-Host ""
    Write-Host "Running unit tests..." -ForegroundColor Cyan

    python -m pytest `
        tests/unit `
        -v `
        --timeout=120 `
        --basetemp="$unitTemp" `
        -p no:cacheprovider

    if ($LASTEXITCODE -ne 0) {
        throw "Unit tests failed."
    }

    Write-Host ""
    Write-Host "Running integration tests..." -ForegroundColor Cyan

    python -m pytest `
        tests/integration `
        -v `
        --timeout=120 `
        --basetemp="$integrationTemp" `
        -p no:cacheprovider

    if ($LASTEXITCODE -ne 0) {
        throw "Integration tests failed."
    }

    Write-Host ""
    Write-Host "Verifying Alpaca stream..." -ForegroundColor Cyan

    python .\scripts\verify_alpaca_v21.py

    if ($LASTEXITCODE -ne 0) {
        throw "Alpaca stream verification failed."
    }

    Write-Host ""
    Write-Host "Verifying Alpaca reconciliation..." -ForegroundColor Cyan

    python .\scripts\verify_alpaca_reconciliation_v22.py

    if ($LASTEXITCODE -ne 0) {
        throw "Alpaca reconciliation verification failed."
    }

    Write-Host ""
    Write-Host "Verifying Alpaca broker discovery..." -ForegroundColor Cyan

    python .\scripts\verify_alpaca_discovery_v23.py

    if ($LASTEXITCODE -ne 0) {
        throw "Alpaca broker discovery verification failed."
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Version 2.3 verification passed." -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Version 2.3 verification failed." -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""

    Write-Host $_.Exception.Message -ForegroundColor Red

    exit 1
}
finally {
    Set-Location $originalLocation
}