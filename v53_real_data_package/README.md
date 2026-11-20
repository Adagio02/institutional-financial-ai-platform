# V5.3 real external-data acquisition

Installs a guarded downloader producing the exact four Parquet schemas required by the existing V5.3 pipeline. Sources: Alpaca IEX adjusted daily bars, SEC EDGAR Company Facts, Alpha Vantage Earnings, and Alpha Vantage News Sentiment. It never labels generated/demo observations as real.

From the project root, run the installer, keep the four credential environment variables loaded, then execute:

```powershell
& ".\scripts\run_acquire_v53_real_data.ps1" -Symbols "AAPL,MSFT,AMZN,NVDA,META,GOOGL" -Start "2023-01-01"
```

Alpha Vantage free-tier throttling is handled conservatively through `FINAI_AV_DELAY_SECONDS` (default 12 seconds). API access and historical coverage remain subject to provider entitlements. Inspect `data/research/v53/source_manifest.json` before qualification.
