param(
 [string]$PredictionPath="artifacts\v56-research-006\oos_predictions.parquet",
 [string]$OutputPath="artifacts\v56-research-007",[double]$TransactionCostBps=5
)
$ErrorActionPreference="Stop";$Root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path;Set-Location $Root
if(-not(Test-Path -LiteralPath $PredictionPath)){throw "V006 prediction file not found: $PredictionPath"}
python -m pip install -r requirements-v56-research.txt;if($LASTEXITCODE-ne 0){throw "Dependencies failed"}
$env:PYTHONPATH=(Join-Path $Root "src")
python scripts\run_v56_research_007.py --predictions $PredictionPath --output $OutputPath --cost-bps $TransactionCostBps
if($LASTEXITCODE-ne 0){throw "V5.6 research 007 failed"}
python -m pytest tests\unit\test_v56_research_007.py -q
if($LASTEXITCODE-ne 0){throw "V007 tests failed"}
Write-Host "V5.6 research 007 completed: $OutputPath" -ForegroundColor Green
