Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$originalLocation = Get-Location

$pytestRoot = "D:\finai-pytest\v20"

try {
    Set-Location $repositoryRoot

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Version 2.0 verification" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    Write-Host ""
    Write-Host "Checking Python..." -ForegroundColor Cyan

    python --version

    if ($LASTEXITCODE -ne 0) {
        throw "Python check failed."
    }

    Write-Host ""
    Write-Host "Compiling project..." -ForegroundColor Cyan

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
    Write-Host "Checking Docker Compose..." -ForegroundColor Cyan

    docker compose config --quiet

    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose config failed."
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

        Write-Host "PostgreSQL attempt $attempt of 30..."

        Start-Sleep -Seconds 2
    }

    if (-not $databaseReady) {
        throw "PostgreSQL did not become ready."
    }

    Write-Host ""
    Write-Host "Applying migrations..." -ForegroundColor Cyan

    alembic upgrade head

    if ($LASTEXITCODE -ne 0) {
        throw "Alembic migration failed."
    }

    Write-Host ""
    Write-Host "Checking Alembic revision..." -ForegroundColor Cyan

    alembic current

    if ($LASTEXITCODE -ne 0) {
        throw "Alembic current failed."
    }

    Write-Host ""
    Write-Host "Verifying Alpaca paper connection..." -ForegroundColor Cyan

    python .\scripts\verify_alpaca_v20.py

    if ($LASTEXITCODE -ne 0) {
        throw "Alpaca paper verification failed."
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
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Version 2.0 verification passed." -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Version 2.0 verification failed." -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""

    Write-Host $_.Exception.Message -ForegroundColor Red

    exit 1
}
finally {
    Set-Location $originalLocation
}