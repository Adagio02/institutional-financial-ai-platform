# Verifies the installation: runs the V5.6 tests (including the V007 fix) and the kit itself.
# Usage (from the project root, virtual environment active):  .\research_kit\setup_check.ps1
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root
$env:PYTHONPATH = Join-Path $Root "src"
python -m pytest tests/unit/test_v56_research.py tests/unit/test_v56_research_007.py `
    tests/unit/test_v56_research_008.py tests/unit/test_v56_fixes.py tests/unit/test_v56_v007_turnover_fix.py -q
if ($LASTEXITCODE -ne 0) { throw "Tests failed - paste the output above into the chat." }
python -m research_kit list
if ($LASTEXITCODE -ne 0) { throw "research_kit failed to start - paste the output above into the chat." }
Write-Host "Installation OK." -ForegroundColor Green
