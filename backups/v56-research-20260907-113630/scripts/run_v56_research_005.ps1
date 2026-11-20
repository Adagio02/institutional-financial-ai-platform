param(
 [string]$Start="2018-01-01",[string]$End=(Get-Date -Format "yyyy-MM-dd"),
 [string]$OutputRoot="data\research\v56-research-005",
 [string]$ArtifactRoot="artifacts\v56-research-005",
 [int]$MinimumSymbols=30,[double]$TransactionCostBps=5,
 [string]$FundamentalPath="",[string]$EventPath="",[string]$NewsPath=""
)
$ErrorActionPreference="Stop";$Root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path;Set-Location $Root
$Universe="config\v56r005_universe.csv";$Bars=Join-Path $OutputRoot "bars.parquet";$Panel=Join-Path $OutputRoot "model_panel.parquet"
python -m pip install -r requirements-v56-research.txt;if($LASTEXITCODE-ne 0){throw "Dependency installation failed"}
python scripts\acquire_v56r005_bars.py --universe $Universe --start $Start --end $End --output $Bars
if($LASTEXITCODE-ne 0){throw "Historical bar acquisition failed"}
$Arguments=@("scripts\build_v56r005_panel.py","--bars",$Bars,"--universe",$Universe,"--output",$Panel,"--minimum-symbols",$MinimumSymbols)
if($FundamentalPath){$Arguments+=@("--fundamentals",$FundamentalPath)};if($EventPath){$Arguments+=@("--events",$EventPath)};if($NewsPath){$Arguments+=@("--news",$NewsPath)}
python @Arguments;if($LASTEXITCODE-ne 0){throw "Panel construction failed"}
$env:PYTHONPATH=(Join-Path $Root "src")
python scripts\run_v56_research_005.py --input $Panel --output $ArtifactRoot --minimum-symbols $MinimumSymbols --cost-bps $TransactionCostBps
if($LASTEXITCODE-ne 0){throw "V5.6 research 005 failed"}
python -m pytest tests\unit\test_v56_research.py -q;if($LASTEXITCODE-ne 0){throw "Tests failed"}
Write-Host "V5.6 research 005 completed: $ArtifactRoot" -ForegroundColor Green
