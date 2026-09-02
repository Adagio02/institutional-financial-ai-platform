$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

Write-Host "Verifying V4.9.2..." -ForegroundColor Cyan
python -m compileall -q src tests scripts
if ($LASTEXITCODE -ne 0) { throw "Compilation failed." }

python -m ruff check `
    src/finai/domain/portfolio/v492_neutralization.py `
    src/finai/application/services/v492_neutralization_service.py `
    src/finai/application/services/v492_neutralization_factory.py `
    scripts/run_v492_neutralization.py `
    tests/unit/test_v49x_portfolio_pipeline.py
if ($LASTEXITCODE -ne 0) { throw "Ruff failed." }

python -m pytest tests/unit/test_v49x_portfolio_pipeline.py -q `
    --basetemp="D:\finai-pytest\v492-verify" -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw "V4.9.2 tests failed." }

Write-Host "V4.9.2 verification passed." -ForegroundColor Green
