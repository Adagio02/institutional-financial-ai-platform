$ErrorActionPreference = "Stop"

Write-Host "1. Checking project structure..."
python scripts\check_structure.py

Write-Host "2. Compiling Python..."
python -m compileall -q src apps tests scripts

Write-Host "3. Running Ruff..."
ruff check src apps tests scripts

Write-Host "4. Running tests..."
pytest -q

Write-Host "5. Validating Docker Compose..."
docker compose config | Out-Null

Write-Host "6. Checking expected data directories..."
$requiredDirectories = @(
    "data\bronze\fred",
    "data\bronze\factors",
    "data\bronze\sec",
    "data\bronze\treasury",
    "data\silver",
    "data\gold",
    "data\quarantine"
)

foreach ($directory in $requiredDirectories) {
    if (-not (Test-Path $directory)) {
        throw "Missing directory: $directory"
    }
}

Write-Host "7. Checking expected datasets..."
$requiredFiles = @(
    "data\bronze\fred\DFF.parquet",
    "data\bronze\factors\fama_french_5_daily.parquet",
    "data\bronze\sec\AAPL\submissions.json",
    "data\bronze\sec\AAPL\company_facts.json",
    "data\bronze\treasury\average_interest_rates.parquet"
)

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        throw "Missing dataset: $file"
    }
}

Write-Host ""
Write-Host "Version 0.1 verification passed." -ForegroundColor Green