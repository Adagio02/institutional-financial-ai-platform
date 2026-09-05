$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
python -m compileall -q src tests scripts
if ($LASTEXITCODE -ne 0) { throw "Compilation failed." }
python -m ruff check `
    src/finai/domain/microstructure/v51_quotes.py `
    src/finai/application/services/v51_microstructure_service.py `
    src/finai/application/services/v51_microstructure_factory.py `
    scripts/run_v51_microstructure.py `
    tests/unit/test_v51_microstructure.py
if ($LASTEXITCODE -ne 0) { throw "Ruff failed." }
python -m pytest tests/unit/test_v51_microstructure.py -q `
    --basetemp="D:\finai-pytest\v51-verify" -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw "V5.1.x tests failed." }
if (Test-Path "artifacts\v51\v51_report.json") {
    $Report = Get-Content "artifacts\v51\v51_report.json" -Raw | ConvertFrom-Json
    if ($Report.version -ne "5.1.3") { throw "Unexpected V5.1 report version." }
    if ($Report.signal_count -ne 4) { throw "V5.1 signal catalog is incomplete." }
}
Write-Host "V5.1.x verification passed." -ForegroundColor Green

