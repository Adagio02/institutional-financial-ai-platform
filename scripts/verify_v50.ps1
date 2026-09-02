$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

python -m compileall -q src tests scripts
if ($LASTEXITCODE -ne 0) { throw "Compilation failed." }

python -m ruff check `
    src/finai/domain/alpha/v50_alpha_library.py `
    src/finai/application/services/v50_alpha_library_service.py `
    src/finai/application/services/v50_alpha_library_factory.py `
    scripts/run_v50_alpha_library.py `
    tests/unit/test_v50_alpha_library.py
if ($LASTEXITCODE -ne 0) { throw "Ruff failed." }

python -m pytest tests/unit/test_v50_alpha_library.py -q `
    --basetemp="D:\finai-pytest\v50-verify" -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw "V5.0.x tests failed." }

$Report = "artifacts\v50\v50_report.json"
if (Test-Path $Report) {
    $Data = Get-Content $Report -Raw | ConvertFrom-Json
    if ($Data.version -ne "5.0.3") { throw "Unexpected V5.0 report version." }
    if ($Data.alpha_count -lt 5) { throw "V5.0 alpha catalog is incomplete." }
}
Write-Host "V5.0.x verification passed." -ForegroundColor Green

