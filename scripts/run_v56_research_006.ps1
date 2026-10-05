param(
 [string]$InputPath="data\research\v56-research-005-enriched\model_panel.parquet",
 [string]$OutputPath="artifacts\v56-research-006",
 [int]$MinimumSymbols=30,[double]$TransactionCostBps=5
)
$ErrorActionPreference="Stop";$Root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path;Set-Location $Root
if(-not(Test-Path -LiteralPath $InputPath)){throw "Input panel not found: $InputPath"}
python -m pip install -r requirements-v56-research.txt;if($LASTEXITCODE-ne 0){throw "Dependencies failed"}
$env:PYTHONPATH=(Join-Path $Root "src")
python scripts\run_v56_research_006.py --input $InputPath --output $OutputPath --minimum-symbols $MinimumSymbols --cost-bps $TransactionCostBps
if($LASTEXITCODE-ne 0){throw "V5.6 research 006 failed"}
python -m pytest tests\unit\test_v56_research.py tests\unit\test_v56_research_006.py -q
if($LASTEXITCODE-ne 0){throw "V5.6 research 006 tests failed"}
Write-Host "V5.6 research 006 completed: $OutputPath" -ForegroundColor Green
