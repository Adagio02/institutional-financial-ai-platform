# Drop-in step for an EXISTING after-close automation script. Call it from your script:
#     & "D:\Projects\institutional-financial-ai-platform\research_kit\run_daily_step.ps1"
# It returns the research pipeline's exit code: 0 ok, 1 failed/unhealthy, 2 new final verdict.
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
Push-Location $Root
try {
    & $Python -m research_kit daily
    $code = $LASTEXITCODE
} finally {
    Pop-Location
}
switch ($code) {
    0 { Write-Host "Research daily: OK" }
    1 { Write-Warning "Research daily: FAILED or data unhealthy - see research\shadow\run.log" }
    2 { Write-Warning "Research daily: a strategy reached a FINAL verdict - see research\shadow\status.json" }
}
exit $code
