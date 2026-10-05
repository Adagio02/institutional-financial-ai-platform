# V009 research reset and prospective qualification

This package does not guarantee investment success. It separates research development from eligibility and blocks V5.7 until a new real, one-shot V5.6 lock passes.

## Included

- 110-symbol, 11-sector seed universe
- Alpaca adjusted daily OHLCV acquisition
- SEC company-facts and submissions acquisition with filing timestamps
- value, profitability, quality, investment, stability, filing-event, regime, relative, liquidity and risk features
- local FRED macro integration when `data/bronze/fred/*.parquet` exists
- V006 raw-rank modeling plus unchanged V007 portfolio architecture
- immutable protocol and SHA-256
- prospective-lock readiness counter and V5.7 unlock guard
- V5.7-V5.9 ineligible software dry-run

The included sector taxonomy is marked `seed_unverified`. Verify and effective-date it against a dated authoritative source **before the first protocol is created**. Replace each provenance value only after verification, then create an attestation:

```powershell
python ".\scripts\attest_v009_sector_history.py" `
 --universe ".\config\v009_universe.csv" `
 --source "DATED AUTHORITATIVE SOURCE OR INTERNAL SNAPSHOT ID" `
 --verified-by "YOUR NAME" `
 --output ".\artifacts\v009-reset\sector_attestation.json"
```

The script refuses to attest while any row still contains `seed` or `unverified`.

## Load credentials

```powershell
$env:APCA_API_KEY_ID=Read-Host "Alpaca key ID"
$S=Read-Host "Alpaca secret" -AsSecureString
$env:APCA_API_SECRET_KEY=[System.Net.NetworkCredential]::new("",$S).Password
Remove-Variable S
$env:SEC_USER_AGENT=Read-Host "SEC user agent (Your Name your-email@example.com)"
```

## Run the development reset

The cutoff below records that V005-V008 used data through September 7, 2026.

```powershell
Set-Location "D:\Projects\institutional-financial-ai-platform"
& ".\.venv\Scripts\Activate.ps1"
& ".\scripts\run_v009_reset.ps1" `
 -Start "2016-01-01" `
 -ContaminatedThrough "2026-09-07" `
 -DataRoot ".\data\research\v009-reset" `
 -ArtifactRoot ".\artifacts\v009-reset" `
 -MinimumSymbols 80 `
 -TransactionCostBps 5
```

SEC retrieval takes time because requests are deliberately paced. Failures are written to `data/research/v009-reset/sec/acquisition_errors.json`.

## Inspect development only

```powershell
$R=Get-Content ".\artifacts\v009-reset\development\research_report.json" -Raw|ConvertFrom-Json
$R.metrics|Format-List;$R.checks|Format-List
Get-Content ".\artifacts\v009-reset\protocol.json" -Raw
```

## Check prospective readiness

```powershell
python ".\scripts\collect_v009_prospective.py" --protocol ".\artifacts\v009-reset\protocol.json"
```

Refresh prospective data without evaluating performance:

```powershell
& ".\scripts\run_v009_prospective_collect.ps1" `
 -ProtocolPath ".\artifacts\v009-reset\protocol.json" `
 -DataRoot ".\data\research\v009-prospective" `
 -MinimumSymbols 80
```

The collector downloads a lookback buffer for feature construction but exports only rows on or after the immutable prospective start. Do not run performance reports on partial prospective data.

## Guard V5.7 after a future one-shot lock

```powershell
python ".\scripts\check_v009_unlock.py" --protocol ".\artifacts\v009-reset\protocol.json" --locked-report ".\artifacts\v009-locked\v563_report.json" --sector-attestation ".\artifacts\v009-reset\sector_attestation.json"
if($LASTEXITCODE-ne 0){throw "V5.7 remains locked."}
```

## Finish software without claiming qualification

```powershell
& ".\scripts\run_v57_to_v59_software_dry_run.ps1"
```

## Git

```powershell
git switch -c v5.6-research-reset-v009
git add config/v009_universe.csv scripts/acquire_v009_sec.py scripts/build_v009_panel.py scripts/create_v009_protocol.py scripts/check_v009_unlock.py scripts/collect_v009_prospective.py scripts/attest_v009_sector_history.py scripts/run_v009_reset.ps1 scripts/run_v009_prospective_collect.ps1 scripts/run_v57_to_v59_software_dry_run.ps1 tests/unit/test_v009_reset.py README-V009-RESET.md
git commit -m "Add V009 point-in-time research reset and qualification guard"
git push -u origin v5.6-research-reset-v009
```
