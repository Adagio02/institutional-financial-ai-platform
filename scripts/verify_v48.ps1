$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

Write-Host "Verifying V4.8 package..." -ForegroundColor Cyan
python --version
if ($LASTEXITCODE -ne 0) { throw "Python failed." }

python -m compileall -q src tests scripts
if ($LASTEXITCODE -ne 0) { throw "Compilation failed." }

python -m ruff check `
    src/finai/domain/learning/v48_features.py `
    src/finai/domain/learning/v481_targets.py `
    src/finai/domain/learning/v482_ranking.py `
    src/finai/domain/learning/v483_ic.py `
    src/finai/domain/learning/v48_storage.py `
    src/finai/domain/learning/v48_models.py `
    src/finai/domain/learning/v48_research.py `
    src/finai/domain/learning/v48_cross_sectional_research.py `
    src/finai/application/services/v48_feature_service.py `
    src/finai/application/services/v48_feature_factory.py `
    src/finai/application/services/v481_target_service.py `
    src/finai/application/services/v481_target_factory.py `
    src/finai/application/services/v482_ranking_service.py `
    src/finai/application/services/v482_ranking_factory.py `
    src/finai/application/services/v483_ic_service.py `
    src/finai/application/services/v483_ic_factory.py `
    src/finai/application/services/v48_learning_service.py `
    src/finai/application/services/v48_learning_factory.py `
    src/finai/application/services/v483_locked_validation_service.py `
    src/finai/application/services/v483_locked_validation_factory.py `
    tests/unit/test_v48_research.py `
    tests/unit/test_v48_models.py
if ($LASTEXITCODE -ne 0) { throw "Ruff failed." }

python -m pytest `
    tests/unit/test_v48_research.py `
    tests/unit/test_v48_models.py `
    -q `
    --basetemp="D:\finai-pytest\v48-verify" `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw "V4.8 tests failed." }

python -c "from finai.application.services.v48_feature_service import V48FeatureService; from finai.application.services.v481_target_service import V481TargetService; from finai.application.services.v482_ranking_service import V482RankingService; from finai.application.services.v483_ic_service import V483ICAnalysisService; print('V4.8 imports passed.')"
if ($LASTEXITCODE -ne 0) { throw "V4.8 import check failed." }

Write-Host "V4.8 package verification passed." -ForegroundColor Green
