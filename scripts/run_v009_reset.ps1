param(
 [string]$Start="2016-01-01",[string]$ContaminatedThrough="2026-09-07",
 [string]$DataRoot="data\research\v009-reset",[string]$ArtifactRoot="artifacts\v009-reset",
 [int]$MinimumSymbols=80,[double]$TransactionCostBps=5
)
$ErrorActionPreference="Stop";$Root=(Resolve-Path(Join-Path $PSScriptRoot "..")).Path;Set-Location $Root
foreach($Name in @("APCA_API_KEY_ID","APCA_API_SECRET_KEY","SEC_USER_AGENT")){if([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($Name))){throw "$Name is not loaded in this terminal."}}
python -m pip install -r requirements-v56-research.txt;if($LASTEXITCODE-ne 0){throw "Dependencies failed"}
$Universe="config\v009_universe.csv";$Protocol=Join-Path $ArtifactRoot "protocol.json"
if(-not(Test-Path -LiteralPath $Protocol)){python scripts\create_v009_protocol.py --output $Protocol --contaminated-through $ContaminatedThrough --universe $Universe;if($LASTEXITCODE-ne 0){throw "Protocol creation failed"}}
$Bars=Join-Path $DataRoot "bars.parquet";$Sec=Join-Path $DataRoot "sec";$Panel=Join-Path $DataRoot "model_panel.parquet"
python scripts\acquire_v56r005_bars.py --universe $Universe --start $Start --end $ContaminatedThrough --output $Bars
if($LASTEXITCODE-ne 0){throw "Alpaca acquisition failed"}
python scripts\acquire_v009_sec.py --universe $Universe --output $Sec
if($LASTEXITCODE-ne 0){throw "SEC acquisition failed"}
python scripts\build_v009_panel.py --bars $Bars --universe $Universe --fundamentals (Join-Path $Sec "fundamentals.parquet") --events (Join-Path $Sec "filing_events.parquet") --output $Panel --minimum-symbols $MinimumSymbols
if($LASTEXITCODE-ne 0){throw "V009 panel construction failed"}
$env:PYTHONPATH=(Join-Path $Root "src");$ModelOut=Join-Path $ArtifactRoot "model";$PortfolioOut=Join-Path $ArtifactRoot "development"
python scripts\run_v56_research_006.py --input $Panel --output $ModelOut --minimum-symbols $MinimumSymbols --cost-bps $TransactionCostBps
if($LASTEXITCODE-ne 0){throw "V009 walk-forward model failed"}
python scripts\run_v56_research_007.py --predictions (Join-Path $ModelOut "oos_predictions.parquet") --output $PortfolioOut --cost-bps $TransactionCostBps
if($LASTEXITCODE-ne 0){throw "Frozen V007 portfolio evaluation failed"}
Write-Host "V009 research reset complete. This is development-only: $PortfolioOut" -ForegroundColor Green
Write-Host "Prospective lock begins after $ContaminatedThrough; V5.7 remains blocked." -ForegroundColor Yellow
