$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

Write-Host "Verifying V4.9.1 through V4.9.3..." -ForegroundColor Cyan
python --version
if ($LASTEXITCODE -ne 0) { throw "Python failed." }

python -m compileall -q src tests scripts
if ($LASTEXITCODE -ne 0) { throw "Compilation failed." }

python -m ruff check `
    src/finai/domain/portfolio/v491_ranking.py `
    src/finai/domain/portfolio/v492_neutralization.py `
    src/finai/domain/portfolio/v493_cost_optimization.py `
    src/finai/application/services/v491_portfolio_service.py `
    src/finai/application/services/v491_portfolio_factory.py `
    src/finai/application/services/v492_neutralization_service.py `
    src/finai/application/services/v492_neutralization_factory.py `
    src/finai/application/services/v493_optimization_service.py `
    src/finai/application/services/v493_optimization_factory.py `
    scripts/run_v491_ranking_portfolio.py `
    scripts/run_v492_neutralization.py `
    scripts/run_v493_cost_optimization.py `
    tests/unit/test_v49x_portfolio_pipeline.py
if ($LASTEXITCODE -ne 0) { throw "Ruff failed." }

python -m pytest `
    tests/unit/test_v49_portfolio_construction.py `
    tests/unit/test_v49x_portfolio_pipeline.py `
    -q `
    --basetemp="D:\finai-pytest\v493-verify" `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw "V4.9.x tests failed." }

Write-Host "V4.9.1 through V4.9.3 verification passed." -ForegroundColor Green
