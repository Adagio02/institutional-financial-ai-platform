$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== FINAI V3.5 MARKET UPDATE ===" `
    -ForegroundColor Cyan

Write-Host ""
Write-Host "Starting infrastructure..."

docker compose up -d

if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose failed."
}

Write-Host ""
Write-Host "Waiting for PostgreSQL..."

Start-Sleep -Seconds 5

Write-Host ""
Write-Host "Ingesting AAPL real Alpaca data..."

python .\scripts\ingest_alpaca_history_v30.py `
    --symbol AAPL `
    --interval 1m `
    --days 5

if ($LASTEXITCODE -ne 0) {
    throw "Alpaca ingestion failed."
}

Write-Host ""
Write-Host "Checking V3.5 readiness..."

python .\scripts\check_v35_readiness.py

if ($LASTEXITCODE -ne 0) {
    throw "V3.5 readiness check failed."
}

Write-Host ""
Write-Host "V3.5 market update complete." `
    -ForegroundColor Green