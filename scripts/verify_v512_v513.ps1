$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
python -m compileall -q src tests scripts
if ($LASTEXITCODE -ne 0) { throw "Compilation failed." }
python -m pytest tests/unit/test_v512_v513_stages.py -q `
    --basetemp="D:\finai-pytest\v512-v513" -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw "V5.1.2-V5.1.3 tests failed." }
foreach ($File in @(
    "artifacts\v51\v512_report.json",
    "artifacts\v51\v513_report.json",
    "artifacts\v51\v513_signal_qualification.json"
)) {
    if (-not (Test-Path -LiteralPath $File)) { throw "Missing artifact: $File" }
}
Write-Host "V5.1.2-V5.1.3 verification passed." -ForegroundColor Green

