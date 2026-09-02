$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

Write-Host "Verifying V4.9.1..." -ForegroundColor Cyan
python -m compileall -q src tests scripts
if ($LASTEXITCODE -ne 0) { throw "Compilation failed." }

python -m ruff check `
    src/finai/domain/portfolio/v491_ranking.py `
    src/finai/application/services/v491_portfolio_service.py `
    src/finai/application/services/v491_portfolio_factory.py `
    scripts/run_v491_ranking_portfolio.py `
    tests/unit/test_v49x_portfolio_pipeline.py
if ($LASTEXITCODE -ne 0) { throw "Ruff failed." }

python -m pytest tests/unit/test_v49x_portfolio_pipeline.py -q `
    --basetemp="D:\finai-pytest\v491-verify" -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw "V4.9.1 tests failed." }

Write-Host "V4.9.1 verification passed." -ForegroundColor Green
