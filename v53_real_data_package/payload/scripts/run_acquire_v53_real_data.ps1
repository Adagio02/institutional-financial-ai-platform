param([string]$Symbols="AAPL,MSFT,AMZN,NVDA,META,GOOGL",[string]$Start="2023-01-01",[string]$End=(Get-Date -Format "yyyy-MM-dd"),[string]$Output="data\research\v53")
$ErrorActionPreference="Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
foreach($Name in "APCA_API_KEY_ID","APCA_API_SECRET_KEY","ALPHA_VANTAGE_API_KEY","FINAI_SEC_USER_AGENT") { if([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($Name))){throw "$Name is not loaded."} }
python -m pip install -q requests pandas pyarrow
python .\scripts\acquire_v53_real_data.py --symbols $Symbols --start $Start --end $End --output $Output
if($LASTEXITCODE -ne 0){throw "V5.3 real-data acquisition failed."}
$required="fundamentals.parquet","events.parquet","news.parquet","prices.parquet","source_manifest.json"
foreach($name in $required){$path=Join-Path $Output $name;if(-not(Test-Path -LiteralPath $path)){throw "Missing output: $path"}}
Write-Host "V5.3 real sources acquired and verified." -ForegroundColor Green
