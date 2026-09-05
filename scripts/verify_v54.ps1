$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
python -m compileall -q src scripts
if ($LASTEXITCODE -ne 0) { throw "V5.4 compilation failed." }
python -m pytest tests/unit/test_v54_ensemble.py -q --basetemp="D:\finai-pytest\v54" -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw "V5.4 tests failed." }
$Required = @(
    "artifacts\v54\v541_report.json", "artifacts\v54\v542_report.json",
    "artifacts\v54\v543_qualification.json", "artifacts\v54\v543_champion_contract.json",
    "artifacts\v54\v543_report.json"
)
foreach ($Path in $Required) {
    if (-not (Test-Path -LiteralPath $Path)) { throw "Missing V5.4 artifact: $Path" }
    if ((Get-Item -LiteralPath $Path).Length -eq 0) { throw "Empty V5.4 artifact: $Path" }
}
Write-Host "V5.4.x verification passed." -ForegroundColor Green

