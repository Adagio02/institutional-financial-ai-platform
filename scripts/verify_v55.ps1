$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
python -m compileall -q src scripts
if ($LASTEXITCODE -ne 0) { throw "V5.5 compilation failed." }
python -m pytest tests/unit/test_v55_walk_forward.py -q --basetemp="D:\finai-pytest\v55" -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw "V5.5 tests failed." }
$Required = @("artifacts\v55\v551_fold_manifest.json", "artifacts\v55\v552_report.json", "artifacts\v55\v553_qualification.json", "artifacts\v55\v553_champion_contract.json", "artifacts\v55\v553_report.json")
foreach ($Path in $Required) {
 if (-not (Test-Path -LiteralPath $Path)) { throw "Missing V5.5 artifact: $Path" }
 if ((Get-Item -LiteralPath $Path).Length -eq 0) { throw "Empty V5.5 artifact: $Path" }
}
Write-Host "V5.5.x verification passed." -ForegroundColor Green
