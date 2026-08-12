Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"


function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Description,

        [Parameter(Mandatory = $true)]
        [scriptblock] $Command
    )

    Write-Host $Description -ForegroundColor Cyan

    & $Command

    if ($LASTEXITCODE -ne 0) {
        throw (
            "$Description failed with exit code " +
            "$LASTEXITCODE."
        )
    }
}


$repositoryRoot = Split-Path -Parent $PSScriptRoot
$originalLocation = Get-Location


try {
    Set-Location $repositoryRoot

    Write-Host ""
    Write-Host "Version 1.1 verification" -ForegroundColor Cyan
    Write-Host ""

    Invoke-Checked `
        -Description "Compiling source..." `
        -Command {
            python -m compileall -q src tests migrations
        }

    Invoke-Checked `
        -Description "Running Ruff..." `
        -Command {
            python -m ruff check src tests migrations
        }

    Invoke-Checked `
        -Description "Checking Docker Compose..." `
        -Command {
            docker compose config --quiet
        }

    Invoke-Checked `
        -Description "Starting infrastructure..." `
        -Command {
            docker compose up -d postgres mlflow
        }

    Write-Host "Waiting for PostgreSQL..." -ForegroundColor Cyan

    $databaseReady = $false

    for ($attempt = 1; $attempt -le 20; $attempt++) {
        docker compose exec `
            -T `
            postgres `
            pg_isready `
            -U finai `
            -d finai *> $null

        if ($LASTEXITCODE -eq 0) {
            $databaseReady = $true
            break
        }

        Start-Sleep -Seconds 2
    }

    if (-not $databaseReady) {
        throw "PostgreSQL did not become ready."
    }

    Invoke-Checked `
        -Description "Applying migrations..." `
        -Command {
            alembic upgrade head
        }

    Invoke-Checked `
        -Description "Running unit tests..." `
        -Command {
            python -m pytest `
                tests\unit `
                -v `
                --timeout=120
        }

    Invoke-Checked `
        -Description "Running integration tests..." `
        -Command {
            python -m pytest `
                tests\integration `
                -v `
                --timeout=120
        }

    Write-Host ""
    Write-Host "Version 1.1 verification passed." -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "Version 1.1 verification failed." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red

    exit 1
}
finally {
    Set-Location $originalLocation
}