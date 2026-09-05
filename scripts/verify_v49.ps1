$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

Write-Host "Verifying V4.9 package..." -ForegroundColor Cyan
python --version
if ($LASTEXITCODE -ne 0) { throw "Python failed." }

python -m compileall -q src tests scripts
if ($LASTEXITCODE -ne 0) { throw "Compilation failed." }

python -m ruff check `
    src/finai/domain/portfolio/__init__.py `
    src/finai/domain/portfolio/v49_construction.py `
    src/finai/application/services/v49_portfolio_construction_service.py `
    src/finai/application/services/v49_portfolio_construction_factory.py `
    scripts/run_v49_portfolio_engine.py `
    tests/unit/test_v49_portfolio_construction.py
if ($LASTEXITCODE -ne 0) { throw "Ruff failed." }

python -m pytest `
    tests/unit/test_v49_portfolio_construction.py `
    -q `
    --basetemp="D:\finai-pytest\v49-verify" `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw "V4.9 tests failed." }

python -c "from finai.domain.portfolio.v49_construction import PortfolioConstructionEngine; from finai.application.services.v49_portfolio_construction_service import V49PortfolioConstructionService; print('V4.9 imports passed.')"
if ($LASTEXITCODE -ne 0) { throw "V4.9 import check failed." }

Write-Host "V4.9 package verification passed." -ForegroundColor Green
