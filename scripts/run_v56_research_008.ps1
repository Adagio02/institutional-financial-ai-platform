param([string]$InputPath="data\research\v56-research-005-enriched\model_panel.parquet",[string]$OutputPath="artifacts\v56-research-008",[double]$TransactionCostBps=5)
$ErrorActionPreference="Stop";$Root=(Resolve-Path(Join-Path $PSScriptRoot "..")).Path;Set-Location $Root
if(-not(Test-Path -LiteralPath $InputPath)){throw "Input panel not found: $InputPath"}
python -m pip install -r requirements-v56-research.txt;if($LASTEXITCODE-ne 0){throw "Dependencies failed"}
$env:PYTHONPATH=(Join-Path $Root "src")
python scripts\run_v56_research_008.py --input $InputPath --output $OutputPath --cost-bps $TransactionCostBps
if($LASTEXITCODE-ne 0){throw "V008 failed"}
python -m pytest tests\unit\test_v56_research_008.py -q;if($LASTEXITCODE-ne 0){throw "V008 tests failed"}
Write-Host "V008 completed: $OutputPath" -ForegroundColor Green
