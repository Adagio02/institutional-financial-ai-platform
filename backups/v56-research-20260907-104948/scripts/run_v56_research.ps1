param(
    [Parameter(Mandatory=$true)][string]$InputPath,
    [string]$OutputPath = "artifacts\v56-research-003",
    [int]$MinimumSymbols = 8,
    [double]$TransactionCostBps = 5.0,
    [int]$Horizon = 5
)
$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
if (-not (Test-Path -LiteralPath $InputPath)) { throw "Input file does not exist: $InputPath" }
python -m pip install -r ".\requirements-v56-research.txt"
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
$env:PYTHONPATH = (Join-Path $ProjectRoot "src")
python ".\scripts\run_v56_research.py" --input $InputPath --output $OutputPath --min-symbols $MinimumSymbols --cost-bps $TransactionCostBps --horizon $Horizon
if ($LASTEXITCODE -ne 0) { throw "V5.6 research pipeline failed." }
python -m pytest ".\tests\unit\test_v56_research.py" -q
if ($LASTEXITCODE -ne 0) { throw "V5.6 research tests failed." }
Write-Host "V5.6 research candidate completed: $OutputPath" -ForegroundColor Green

