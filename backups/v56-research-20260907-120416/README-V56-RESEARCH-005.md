# V5.6 Research 005: multi-sector, point-in-time, cost-aware candidate

This is research code, not a profit guarantee and not authorization to trade. It never modifies an existing V5.6 lock or V5.7 input.

## What it implements

- 50 intended liquid US equities across 10 sectors plus SPY as benchmark
- split/dividend-adjusted Alpaca daily OHLCV acquisition with pagination
- effective-dated universe membership
- lagged beta, liquidity, Amihud illiquidity, range, volume, momentum, residual momentum and volatility-scaled momentum
- optional backward-only as-of joins for fundamentals, events and news
- Elastic Net plus shallow gradient boosting
- purged/embargoed walk-forward evaluation
- five-day targets with five-day non-overlapping rebalancing
- market-, beta- and sector-neutral constrained optimization when the columns are available
- position caps, risk penalty, turnover penalty and explicit transaction costs
- honest research gates and SHA-256 artifact hashes

The bundled sector history is a starting taxonomy with broad effective dates. Review it against a dated authoritative classification source before claiming verified point-in-time sector provenance.

## Install

```powershell
Set-Location "D:\Projects\institutional-financial-ai-platform"
& ".\.venv\Scripts\Activate.ps1"
& "D:\PATH\TO\v56_research_package\scripts\install_v56_research.ps1" -ProjectRoot (Get-Location).Path
```

## Credentials for the current PowerShell process

```powershell
$env:APCA_API_KEY_ID = Read-Host "Alpaca key ID"
$Secret = Read-Host "Alpaca secret" -AsSecureString
$env:APCA_API_SECRET_KEY = [Net.NetworkCredential]::new("",$Secret).Password
Remove-Variable Secret
```

Verify without printing secrets:

```powershell
[PSCustomObject]@{
 KeyLoaded = -not [string]::IsNullOrWhiteSpace($env:APCA_API_KEY_ID)
 SecretLoaded = -not [string]::IsNullOrWhiteSpace($env:APCA_API_SECRET_KEY)
}
```

## Execute with price/volume data only

```powershell
& ".\scripts\run_v56_research_005.ps1" `
 -Start "2018-01-01" `
 -End (Get-Date -Format "yyyy-MM-dd") `
 -MinimumSymbols 30 `
 -TransactionCostBps 5
```

## Execute with verified point-in-time V5.3 inputs

Only pass a dataset if it contains `symbol` and an availability field named `available_at`, `published_at`, `filed_at`, or `timestamp`.

```powershell
& ".\scripts\run_v56_research_005.ps1" `
 -Start "2018-01-01" `
 -End (Get-Date -Format "yyyy-MM-dd") `
 -MinimumSymbols 30 `
 -TransactionCostBps 5 `
 -FundamentalPath ".\data\research\v53-expanded\fundamentals.parquet" `
 -EventPath ".\data\research\v53-expanded\events.parquet" `
 -NewsPath ".\data\research\v53-expanded\news.parquet"
```

If the optional files cover only a subset of symbols, unmatched rows remain missing and the model imputer handles them. Never backfill a later filing into an earlier date.

## Inspect

```powershell
$R=Get-Content ".\artifacts\v56-research-005\research_report.json" -Raw|ConvertFrom-Json
$R.metrics|Format-List
$R.checks|Format-List
$R.blocking_reasons
```

Research eligibility allows you to freeze a new candidate. It does not itself pass locked V5.6. A new genuinely untouched interval must then be run once through the existing V5.6 lock pipeline. Only a real, immutable, passing locked contract can progress to V5.7.

## Git

```powershell
git switch -c v5.6-research-005
git add requirements-v56-research.txt config/v56r005_universe.csv scripts/acquire_v56r005_bars.py scripts/build_v56r005_panel.py scripts/run_v56_research_005.py scripts/run_v56_research_005.ps1 src/finai/research/v56 tests/unit/test_v56_research.py README-V56-RESEARCH-005.md
git commit -m "Add multi-sector cost-aware V5.6 research candidate"
git push -u origin v5.6-research-005
```
