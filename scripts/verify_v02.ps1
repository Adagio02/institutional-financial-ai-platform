# scripts/verify_v02.ps1
#
# Version 0.2 production-foundation verification script.
#
# Run from PowerShell with:
# powershell -ExecutionPolicy Bypass -File scripts\verify_v02.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# In PowerShell 7+, make failed native programs behave like PowerShell errors.
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

# Determine the repository root from this script's location.
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$originalLocation = Get-Location

try {
    Set-Location $repositoryRoot

    Write-Host ""
    Write-Host "==============================================" -ForegroundColor DarkCyan
    Write-Host " Institutional Financial AI Platform" -ForegroundColor Cyan
    Write-Host " Version 0.2 Verification" -ForegroundColor Cyan
    Write-Host "==============================================" -ForegroundColor DarkCyan
    Write-Host ""

    # ------------------------------------------------------------
    # 1. Verify required commands
    # ------------------------------------------------------------

    Write-Host "Checking required commands..." -ForegroundColor Cyan

    $requiredCommands = @(
        "git",
        "python",
        "docker",
        "alembic",
        "pytest"
    )

    foreach ($commandName in $requiredCommands) {
        if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
            throw "Required command '$commandName' was not found."
        }
    }

    Write-Host "Required commands are available." -ForegroundColor Green

    # ------------------------------------------------------------
    # 2. Verify Git repository and branch
    # ------------------------------------------------------------

    Write-Host "Checking Git repository..." -ForegroundColor Cyan

    git rev-parse --is-inside-work-tree *> $null

    if ($LASTEXITCODE -ne 0) {
        throw "The current directory is not a Git repository."
    }

    $currentBranch = git branch --show-current

    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine the current Git branch."
    }

    Write-Host "Current branch: $currentBranch"

    if ($currentBranch -ne "feature/v0.2-production-foundation") {
        Write-Warning `
            "Expected branch 'feature/v0.2-production-foundation', but current branch is '$currentBranch'."
    }

    # ------------------------------------------------------------
    # 3. Verify project structure
    # ------------------------------------------------------------

    $requiredPaths = @(
        "src",
        "src\finai",
        "src\finai\core",
        "src\finai\core\config.py",
        "src\finai\api",
        "src\finai\api\main.py",
        "src\finai\infrastructure",
        "src\finai\infrastructure\database",
        "src\finai\infrastructure\database\engine.py",
        "migrations",
        "migrations\env.py",
        "tests",
        "docker-compose.yml",
        "alembic.ini",
        "pyproject.toml"
    )

    Write-Host "Checking project structure..." -ForegroundColor Cyan

    $missingPaths = @()

    foreach ($requiredPath in $requiredPaths) {
        if (-not (Test-Path $requiredPath)) {
            $missingPaths += $requiredPath
        }
    }

    if ($missingPaths.Count -gt 0) {
        $missingText = $missingPaths -join [Environment]::NewLine
        throw "Required project paths are missing:`n$missingText"
    }

    # Run the optional structure script when it exists.
    if (Test-Path "scripts\check_structure.py") {
        Invoke-NativeCommand `
            -Description "Running structure validation..." `
            -Command {
                python scripts\check_structure.py
            }
    }
    else {
        Write-Host "Required project structure exists." -ForegroundColor Green
    }

    # ------------------------------------------------------------
    # 4. Verify application database configuration
    # ------------------------------------------------------------

    Write-Host "Checking database configuration..." -ForegroundColor Cyan

    $databaseUrl = python -c "from finai.core.config import get_settings; print(get_settings().database_url)"

    if ($LASTEXITCODE -ne 0) {
        throw "Unable to load the application database configuration."
    }

    $databaseUrl = "$databaseUrl".Trim()

    if ([string]::IsNullOrWhiteSpace($databaseUrl)) {
        throw "The loaded database URL is empty."
    }

    # Hide the password before displaying the URL.
    $safeDatabaseUrl = $databaseUrl -replace `
        "://([^:]+):([^@]+)@", `
        '://$1:***@'

    Write-Host "Loaded database URL: $safeDatabaseUrl"

    if ($databaseUrl -notmatch "@localhost:5433/finai") {
        throw @"
The host-side DATABASE_URL is incorrect.

Expected a URL using:

localhost:5433/finai

Docker exposes PostgreSQL using:

localhost:5433 -> postgres container port 5432

Loaded value:

$safeDatabaseUrl

Check:
  1. .env
  2. src\finai\core\config.py
  3. A DATABASE_URL PowerShell environment variable
"@
    }

    Write-Host "Database configuration passed." -ForegroundColor Green

    # ------------------------------------------------------------
    # 5. Compile Python source
    # ------------------------------------------------------------

    Invoke-NativeCommand `
        -Description "Compiling Python source..." `
        -Command {
            python -m compileall -q src tests migrations scripts
        }

    Write-Host "Python compilation passed." -ForegroundColor Green

    # ------------------------------------------------------------
    # 6. Run Ruff
    # ------------------------------------------------------------

    Invoke-NativeCommand `
        -Description "Running Ruff..." `
        -Command {
            python -m ruff check src tests migrations scripts
        }

    Write-Host "Ruff validation passed." -ForegroundColor Green

    # ------------------------------------------------------------
    # 7. Validate Docker Compose
    # ------------------------------------------------------------

    Invoke-NativeCommand `
        -Description "Checking Docker Compose configuration..." `
        -Command {
            docker compose config --quiet
        }

    Write-Host "Docker Compose configuration passed." -ForegroundColor Green

    # ------------------------------------------------------------
    # 8. Start PostgreSQL
    # ------------------------------------------------------------

    Invoke-NativeCommand `
        -Description "Starting PostgreSQL..." `
        -Command {
            docker compose up -d postgres
        }

    # ------------------------------------------------------------
    # 9. Wait for PostgreSQL
    # ------------------------------------------------------------

    Write-Host "Waiting for PostgreSQL..." -ForegroundColor Cyan

    $postgresReady = $false
    $maximumAttempts = 30

    for ($attempt = 1; $attempt -le $maximumAttempts; $attempt++) {
        docker compose exec -T postgres `
            pg_isready -U finai -d finai *> $null

        if ($LASTEXITCODE -eq 0) {
            $postgresReady = $true
            break
        }

        Write-Host `
            "PostgreSQL is not ready yet ($attempt/$maximumAttempts)..."

        Start-Sleep -Seconds 2
    }

    if (-not $postgresReady) {
        Write-Host ""
        Write-Host "Recent PostgreSQL logs:" -ForegroundColor Yellow
        docker compose logs --tail 50 postgres

        throw "PostgreSQL did not become ready."
    }

    Write-Host "PostgreSQL is accepting connections." -ForegroundColor Green

    # ------------------------------------------------------------
    # 10. Check SQLAlchemy connectivity
    # ------------------------------------------------------------

    Invoke-NativeCommand `
        -Description "Checking SQLAlchemy connectivity..." `
        -Command {
            python -c "from finai.infrastructure.database.engine import check_database_connection; import sys; result = check_database_connection(); print('Database connection:', result); sys.exit(0 if result else 1)"
        }

    Write-Host "SQLAlchemy connectivity passed." -ForegroundColor Green

    # ------------------------------------------------------------
    # 11. Apply Alembic migrations
    # ------------------------------------------------------------

    Invoke-NativeCommand `
        -Description "Applying migrations..." `
        -Command {
            alembic upgrade head
        }

    Write-Host "Alembic migrations applied." -ForegroundColor Green

    # ------------------------------------------------------------
    # 12. Verify Alembic migration state
    # ------------------------------------------------------------

    Write-Host "Checking migration state..." -ForegroundColor Cyan

    $currentRevisionOutput = alembic current
    $alembicCurrentExitCode = $LASTEXITCODE

    if ($alembicCurrentExitCode -ne 0) {
        throw "Alembic current failed with exit code $alembicCurrentExitCode."
    }

    $currentRevisionText = (
        $currentRevisionOutput |
        Out-String
    ).Trim()

    if ([string]::IsNullOrWhiteSpace($currentRevisionText)) {
        throw "Alembic did not return a current revision."
    }

    Write-Host $currentRevisionText
    Write-Host "Migration-state verification passed." -ForegroundColor Green

    # ------------------------------------------------------------
    # 13. Run the complete test suite
    # ------------------------------------------------------------

    Invoke-NativeCommand `
        -Description "Running test suite..." `
        -Command {
            pytest -v
        }

    Write-Host ""
    Write-Host "==============================================" -ForegroundColor Green
    Write-Host " Version 0.2 verification passed." -ForegroundColor Green
    Write-Host "==============================================" -ForegroundColor Green
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "==============================================" -ForegroundColor Red
    Write-Host " Version 0.2 verification failed." -ForegroundColor Red
    Write-Host "==============================================" -ForegroundColor Red
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""

    exit 1
}
finally {
    Set-Location $originalLocation
}