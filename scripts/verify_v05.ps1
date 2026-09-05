Write-Host ""
Write-Host "============================="
Write-Host "Institutional Financial AI"
Write-Host "Version 0.5 Verification"
Write-Host "============================="
Write-Host ""

python -m pytest tests/unit -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest tests/integration -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m ruff check src tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy src
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Version 0.5 verification passed."