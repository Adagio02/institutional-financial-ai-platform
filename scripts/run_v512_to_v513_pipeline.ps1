$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

$V511Candidates = @(
    "artifacts\v51\v511_normalized_quotes.parquet",
    "artifacts\v51\v511_normalized_quotes.pkl.gz"
)
if (-not ($V511Candidates | Where-Object { Test-Path -LiteralPath $_ })) {
    throw "V5.1.1 artifact missing. Expected v511_normalized_quotes.parquet or .pkl.gz."
}

Write-Host "Running V5.1.2 microstructure signals..." -ForegroundColor Cyan
python .\scripts\run_v512_signals.py
if ($LASTEXITCODE -ne 0) { throw "V5.1.2 failed." }

Write-Host "Running V5.1.3 signal qualification..." -ForegroundColor Cyan
python .\scripts\run_v513_qualification.py
if ($LASTEXITCODE -ne 0) { throw "V5.1.3 failed." }

& .\scripts\verify_v512_v513.ps1
if ($LASTEXITCODE -ne 0) { throw "V5.1.2-V5.1.3 verification failed." }
Write-Host "V5.1.2 and V5.1.3 completed." -ForegroundColor Green

