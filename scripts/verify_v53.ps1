$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
python -m compileall -q src scripts
if ($LASTEXITCODE -ne 0) { throw "V5.3 compilation failed." }
python -m pytest tests/unit/test_v53_fundamental_event_news.py -q --basetemp="D:\finai-pytest\v53" -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw "V5.3 tests failed." }
$Required = @(
    "artifacts\v53\v531_dataset_manifest.json",
    "artifacts\v53\v532_report.json",
    "artifacts\v53\v533_signal_qualification.json",
    "artifacts\v53\v533_champion_contract.json",
    "artifacts\v53\v533_report.json"
)
foreach ($Path in $Required) {
    if (-not (Test-Path -LiteralPath $Path)) { throw "Missing V5.3 artifact: $Path" }
    if ((Get-Item -LiteralPath $Path).Length -eq 0) { throw "Empty V5.3 artifact: $Path" }
}
Write-Host "V5.3.x verification passed." -ForegroundColor Green

