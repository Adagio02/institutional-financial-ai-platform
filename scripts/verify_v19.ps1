Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$originalLocation = Get-Location
$pytestRoot = "D:\finai-pytest\v19"

try {
    Set-Location $repositoryRoot

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Version 1.9 verification" -ForegroundColor Cyan
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
        throw "Python compilation failed."
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
        throw "Docker Compose configuration check failed."
    }

    Write-Host ""
    Write-Host "Starting PostgreSQL and MLflow..." -ForegroundColor Cyan
    docker compose up -d postgres mlflow

    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose startup failed."
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

    Write-Host "PostgreSQL is ready." -ForegroundColor Green

    Write-Host ""
    Write-Host "Checking PostgreSQL connection..." -ForegroundColor Cyan
    docker compose exec -T postgres psql -U finai -d finai -c "SELECT current_database(), current_user;"

    if ($LASTEXITCODE -ne 0) {
        throw "PostgreSQL connection check failed."
    }

    Write-Host ""
    Write-Host "Checking Alembic heads..." -ForegroundColor Cyan
    alembic heads

    if ($LASTEXITCODE -ne 0) {
        throw "Alembic heads check failed."
    }

    Write-Host ""
    Write-Host "Applying migrations..." -ForegroundColor Cyan
    alembic upgrade head

    if ($LASTEXITCODE -ne 0) {
        throw "Alembic migration failed."
    }

    Write-Host ""
    Write-Host "Checking current Alembic revision..." -ForegroundColor Cyan
    alembic current

    if ($LASTEXITCODE -ne 0) {
        throw "Alembic current check failed."
    }

    Write-Host ""
    Write-Host "Checking Alpaca paper configuration..." -ForegroundColor Cyan

    python .\scripts\verify_alpaca_v19.py

    if ($LASTEXITCODE -ne 0) {
        throw "Alpaca paper verification failed."
    }

    if (-not (Test-Path $pytestRoot)) {
        New-Item -ItemType Directory -Path $pytestRoot -Force | Out-Null
    }

    $unitTemp = Join-Path $pytestRoot "unit"
    $integrationTemp = Join-Path $pytestRoot "integration"

    if (Test-Path $unitTemp) {
        Remove-Item $unitTemp -Recurse -Force -ErrorAction SilentlyContinue
    }

    if (Test-Path $integrationTemp) {
        Remove-Item $integrationTemp -Recurse -Force -ErrorAction SilentlyContinue
    }

    Write-Host ""
    Write-Host "Running unit tests..." -ForegroundColor Cyan

    python -m pytest tests/unit -v --timeout=120 --basetemp="$unitTemp" -p no:cacheprovider

    if ($LASTEXITCODE -ne 0) {
        throw "Unit tests failed."
    }

    Write-Host ""
    Write-Host "Running integration tests..." -ForegroundColor Cyan

    python -m pytest tests/integration -v --timeout=120 --basetemp="$integrationTemp" -p no:cacheprovider

    if ($LASTEXITCODE -ne 0) {
        throw "Integration tests failed."
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Version 1.9 verification passed." -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Version 1.9 verification failed." -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""

    exit 1
}
finally {
    Set-Location $originalLocation
}
