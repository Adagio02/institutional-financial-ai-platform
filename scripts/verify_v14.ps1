Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$originalLocation = Get-Location

$originalTemp = $env:TEMP
$originalTmp = $env:TMP

try {
    Set-Location $repositoryRoot

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Version 1.4 verification" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    # ---------------------------------------------------------
    # Controlled pytest / Windows temporary directories
    # ---------------------------------------------------------

    $testTempRoot = Join-Path $repositoryRoot "pytest-temp"
    $systemTempRoot = Join-Path $testTempRoot "system"
    $unitTemp = Join-Path $testTempRoot "unit"
    $integrationTemp = Join-Path $testTempRoot "integration"

    Write-Host ""
    Write-Host "Preparing temporary directories..." -ForegroundColor Cyan

    if (-not (Test-Path $testTempRoot)) {
        New-Item -ItemType Directory -Path $testTempRoot -Force | Out-Null
    }

    if (-not (Test-Path $systemTempRoot)) {
        New-Item -ItemType Directory -Path $systemTempRoot -Force | Out-Null
    }

    if (Test-Path $unitTemp) {
        Remove-Item -Path $unitTemp -Recurse -Force -ErrorAction SilentlyContinue
    }

    if (Test-Path $integrationTemp) {
        Remove-Item -Path $integrationTemp -Recurse -Force -ErrorAction SilentlyContinue
    }

    $env:TEMP = $systemTempRoot
    $env:TMP = $systemTempRoot

    Write-Host "TEMP = $env:TEMP" -ForegroundColor DarkGray
    Write-Host "TMP  = $env:TMP" -ForegroundColor DarkGray

    # ---------------------------------------------------------
    # Python
    # ---------------------------------------------------------

    Write-Host ""
    Write-Host "Checking Python..." -ForegroundColor Cyan

    python --version

    if ($LASTEXITCODE -ne 0) {
        throw "Python check failed."
    }

    # ---------------------------------------------------------
    # Compile
    # ---------------------------------------------------------

    Write-Host ""
    Write-Host "Compiling source..." -ForegroundColor Cyan

    python -m compileall -q src tests migrations

    if ($LASTEXITCODE -ne 0) {
        throw "Python compilation failed."
    }

    # ---------------------------------------------------------
    # Ruff
    # ---------------------------------------------------------

    Write-Host ""
    Write-Host "Running Ruff..." -ForegroundColor Cyan

    python -m ruff check src tests migrations

    if ($LASTEXITCODE -ne 0) {
        throw "Ruff failed."
    }

    # ---------------------------------------------------------
    # Docker Compose
    # ---------------------------------------------------------

    Write-Host ""
    Write-Host "Checking Docker Compose..." -ForegroundColor Cyan

    docker compose config --quiet

    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose configuration check failed."
    }

    # ---------------------------------------------------------
    # Start infrastructure
    # ---------------------------------------------------------

    Write-Host ""
    Write-Host "Starting PostgreSQL and MLflow..." -ForegroundColor Cyan

    docker compose up -d postgres mlflow

    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose startup failed."
    }

    # ---------------------------------------------------------
    # Wait for PostgreSQL
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # PostgreSQL connection
    # ---------------------------------------------------------

    Write-Host ""
    Write-Host "Checking PostgreSQL connection..." -ForegroundColor Cyan

    docker compose exec -T postgres psql -U finai -d finai -c "SELECT current_database(), current_user;"

    if ($LASTEXITCODE -ne 0) {
        throw "PostgreSQL connection check failed."
    }

    # ---------------------------------------------------------
    # Alembic heads
    # ---------------------------------------------------------

    Write-Host ""
    Write-Host "Checking Alembic heads..." -ForegroundColor Cyan

    alembic heads

    if ($LASTEXITCODE -ne 0) {
        throw "Alembic heads check failed."
    }

    # ---------------------------------------------------------
    # Migrations
    # ---------------------------------------------------------

    Write-Host ""
    Write-Host "Applying migrations..." -ForegroundColor Cyan

    alembic upgrade head

    if ($LASTEXITCODE -ne 0) {
        throw "Alembic migration failed."
    }

    # ---------------------------------------------------------
    # Current Alembic revision
    # ---------------------------------------------------------

    Write-Host ""
    Write-Host "Checking current Alembic revision..." -ForegroundColor Cyan

    alembic current

    if ($LASTEXITCODE -ne 0) {
        throw "Alembic current check failed."
    }

    # ---------------------------------------------------------
    # Unit tests
    # ---------------------------------------------------------

    Write-Host ""
    Write-Host "Running unit tests..." -ForegroundColor Cyan

    python -m pytest tests/unit -v --timeout=120 --basetemp="$unitTemp" -p no:cacheprovider

    if ($LASTEXITCODE -ne 0) {
        throw "Unit tests failed."
    }

    # ---------------------------------------------------------
    # Integration tests
    # ---------------------------------------------------------

    Write-Host ""
    Write-Host "Running integration tests..." -ForegroundColor Cyan

    python -m pytest tests/integration -v --timeout=120 --basetemp="$integrationTemp" -p no:cacheprovider

    if ($LASTEXITCODE -ne 0) {
        throw "Integration tests failed."
    }

    # ---------------------------------------------------------
    # Success
    # ---------------------------------------------------------

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Version 1.4 verification passed." -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Version 1.4 verification failed." -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""

    exit 1
}
finally {
    $env:TEMP = $originalTemp
    $env:TMP = $originalTmp

    Set-Location $originalLocation
}