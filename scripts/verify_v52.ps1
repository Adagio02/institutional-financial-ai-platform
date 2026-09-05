$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
python -m compileall -q src tests scripts
if ($LASTEXITCODE -ne 0) { throw "Compilation failed." }
python -m ruff check `
    src/finai/domain/options/v52_volatility.py `
    src/finai/application/services/v521_option_normalization_service.py `
    src/finai/application/services/v522_surface_service.py `
    src/finai/application/services/v523_options_signal_service.py `
    scripts/run_v521_option_normalization.py `
    scripts/run_v522_surface.py `
    scripts/run_v523_options_signals.py `
    tests/unit/test_v52_options_pipeline.py
if ($LASTEXITCODE -ne 0) { throw "Ruff failed." }
python -m pytest tests/unit/test_v52_options_pipeline.py -q `
    --basetemp="D:\finai-pytest\v52-verify" -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw "V5.2.x tests failed." }
foreach ($File in @(
    "artifacts\v52\v521_report.json",
    "artifacts\v52\v522_report.json",
    "artifacts\v52\v523_report.json",
    "artifacts\v52\v523_signal_qualification.json"
)) {
    if (Test-Path "artifacts\v52") {
        if (-not (Test-Path -LiteralPath $File)) { throw "Missing artifact: $File" }
    }
}
Write-Host "V5.2.x verification passed." -ForegroundColor Green

