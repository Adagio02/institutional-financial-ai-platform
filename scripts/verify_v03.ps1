# scripts/verify_v03.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($PSVersionTable.PSVersion.Major -ge 7) {
    $PSNativeCommandUseErrorActionPreference = $true
}

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Description,

        [Parameter(Mandatory = $true)]
        [scriptblock] $Command
    )

    Write-Host $Description -ForegroundColor Cyan

    & $Command
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        throw "$Description failed with exit code $exitCode."
    }
}

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$originalLocation = Get-Location

try {
    Set-Location $repositoryRoot

    Write-Host ""
    Write-Host "==============================================" `
        -ForegroundColor DarkCyan
    Write-Host " Version 0.3 Market Data Verification" `
        -ForegroundColor Cyan
    Write-Host "==============================================" `
        -ForegroundColor DarkCyan
    Write-Host ""

    $expectedBranch = "feature/v0.3-market-data-foundation"
    $currentBranch = git branch --show-current

    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine the current Git branch."
    }

    Write-Host "Current branch: $currentBranch"

    if ($currentBranch -ne $expectedBranch) {
        Write-Warning `
            "Expected '$expectedBranch', but current branch is '$currentBranch'."
    }

    $requiredPaths = @(
        "src\finai\domain\market_data\entities.py",
        "src\finai\domain\market_data\enums.py",
        "src\finai\domain\market_data\validation.py",
        "src\finai\application\market_data\ingestion_service.py",
        "src\finai\infrastructure\database\models\instrument.py",
        "src\finai\infrastructure\database\models\market_bar.py",
        "src\finai\infrastructure\database\repositories\instrument_repository.py",
        "src\finai\infrastructure\database\repositories\market_bar_repository.py",
        "src\finai\infrastructure\market_data\provider.py",
        "src\finai\infrastructure\market_data\mock_provider.py",
        "src\finai\api\routes\instruments.py",
        "src\finai\api\routes\market_data.py",
        "src\finai\api\schemas\instrument.py",
        "src\finai\api\schemas\market_data.py",
        "tests\integration\test_instruments.py",
        "tests\integration\test_market_data.py"
    )

    Write-Host "Checking Version 0.3 structure..." `
        -ForegroundColor Cyan

    $missingPaths = @()

    foreach ($requiredPath in $requiredPaths) {
        if (-not (Test-Path $requiredPath)) {
            $missingPaths += $requiredPath
        }
    }

    if ($missingPaths.Count -gt 0) {
        throw (
            "Missing Version 0.3 paths:`n" +
            ($missingPaths -join "`n")
        )
    }

    Write-Host "Version 0.3 structure passed." `
        -ForegroundColor Green

    Invoke-NativeCommand `
        -Description "Compiling Python source..." `
        -Command {
            python -m compileall -q src tests migrations scripts
        }

    Invoke-NativeCommand `
        -Description "Running Ruff..." `
        -Command {
            python -m ruff check src tests migrations scripts
        }

    Invoke-NativeCommand `
        -Description "Checking Docker Compose..." `
        -Command {
            docker compose config --quiet
        }

    Invoke-NativeCommand `
        -Description "Starting PostgreSQL..." `
        -Command {
            docker compose up -d postgres
        }

    Write-Host "Waiting for PostgreSQL..." `
        -ForegroundColor Cyan

    $postgresReady = $false

    for ($attempt = 1; $attempt -le 30; $attempt++) {
        docker compose exec -T postgres `
            pg_isready -U finai -d finai *> $null

        if ($LASTEXITCODE -eq 0) {
            $postgresReady = $true
            break
        }

        Start-Sleep -Seconds 2
    }

    if (-not $postgresReady) {
        docker compose logs --tail 50 postgres
        throw "PostgreSQL did not become ready."
    }

    Write-Host "PostgreSQL is accepting connections." `
        -ForegroundColor Green

    Invoke-NativeCommand `
        -Description "Checking SQLAlchemy connectivity..." `
        -Command {
            python -c "from finai.infrastructure.database.engine import check_database_connection; import sys; result = check_database_connection(); print('Database connection:', result); sys.exit(0 if result else 1)"
        }

    Invoke-NativeCommand `
        -Description "Applying Alembic migrations..." `
        -Command {
            alembic upgrade head
        }

    Write-Host "Checking required database tables..." `
        -ForegroundColor Cyan

    $tableCheck = docker compose exec -T postgres `
        psql -U finai -d finai -tAc `
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('instruments', 'market_bars');"

    if ($LASTEXITCODE -ne 0) {
        throw "Unable to inspect PostgreSQL tables."
    }

    if ("$tableCheck".Trim() -ne "2") {
        throw "The instruments and market_bars tables were not found."
    }

    Write-Host "Version 0.3 database tables passed." `
        -ForegroundColor Green

    Invoke-NativeCommand `
        -Description "Running unit tests..." `
        -Command {
            pytest tests\unit -v
        }

    Invoke-NativeCommand `
        -Description "Running integration tests..." `
        -Command {
            pytest tests\integration -v
        }

    Invoke-NativeCommand `
        -Description "Running complete test suite..." `
        -Command {
            pytest -v
        }

    Write-Host ""
    Write-Host "==============================================" `
        -ForegroundColor Green
    Write-Host " Version 0.3 verification passed." `
        -ForegroundColor Green
    Write-Host "==============================================" `
        -ForegroundColor Green
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "==============================================" `
        -ForegroundColor Red
    Write-Host " Version 0.3 verification failed." `
        -ForegroundColor Red
    Write-Host "==============================================" `
        -ForegroundColor Red
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""

    exit 1
}
finally {
    Set-Location $originalLocation
}