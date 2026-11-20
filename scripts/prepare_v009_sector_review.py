from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import pandas as pd
import requests

PROJECT = Path(r"D:\Projects\institutional-financial-ai-platform")
UNIVERSE_PATH = PROJECT / "config" / "v009_universe.csv"
CACHE_DIRECTORY = PROJECT / "data" / "cache" / "sec"
OUTPUT_PATH = PROJECT / "config" / "v009_sector_review_prefilled.csv"

TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSION_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
GICS_DEFINITION_URL = "https://www.spglobal.com/spdji/en/landing/topic/gics/"

user_agent = os.environ.get("SEC_USER_AGENT", "").strip()

if "@" not in user_agent:
    raise RuntimeError(
        "SEC_USER_AGENT must contain your name and contact email."
    )

headers = {
    "User-Agent": user_agent,
    "Accept-Encoding": "gzip, deflate",
}

CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)

universe = pd.read_csv(UNIVERSE_PATH)
universe["symbol"] = universe["symbol"].astype(str).str.upper().str.strip()

response = requests.get(
    TICKER_URL,
    headers=headers,
    timeout=60,
)
response.raise_for_status()

ticker_payload = response.json()

ticker_mapping = {
    str(item["ticker"]).upper(): {
        "cik": int(item["cik_str"]),
        "company_name": item["title"],
    }
    for item in ticker_payload.values()
}

rows = []

for number, universe_row in universe.iterrows():
    symbol = universe_row["symbol"]
    proposed_sector = universe_row["sector"]
    ticker_record = ticker_mapping.get(symbol)

    if ticker_record is None:
        rows.append(
            {
                "symbol": symbol,
                "company_name": "",
                "proposed_sector": proposed_sector,
                "verified_sector": "",
                "sec_cik": "",
                "sec_sic": "",
                "sec_sic_description": "",
                "effective_from": "2026-09-08",
                "effective_to": "2099-12-31",
                "source_name": "",
                "source_url_or_snapshot_id": "",
                "source_snapshot_sha256": "",
                "gics_definition_url": GICS_DEFINITION_URL,
                "reviewed_by": "Felipe Taruselli",
                "reviewed_on": "",
                "approved": "false",
                "review_status": "ticker_not_found",
            }
        )
        continue

    cik = ticker_record["cik"]
    submission_url = SUBMISSION_URL.format(cik=cik)
    cache_path = CACHE_DIRECTORY / f"{symbol}_submissions.json"

    try:
        if cache_path.exists():
            payload = json.loads(
                cache_path.read_text(encoding="utf-8-sig")
            )
        else:
            response = requests.get(
                submission_url,
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()

            cache_path.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )

            time.sleep(0.20)

        snapshot_hash = hashlib.sha256(
            cache_path.read_bytes()
        ).hexdigest()

        sic = str(payload.get("sic", "")).strip()
        sic_description = str(
            payload.get("sicDescription", "")
        ).strip()

        status = (
            "ready_for_manual_review"
            if sic and sic_description
            else "missing_sec_sic"
        )

        rows.append(
            {
                "symbol": symbol,
                "company_name": payload.get(
                    "name",
                    ticker_record["company_name"],
                ),
                "proposed_sector": proposed_sector,
                "verified_sector": "",
                "sec_cik": f"{cik:010d}",
                "sec_sic": sic,
                "sec_sic_description": sic_description,
                "effective_from": "2026-09-08",
                "effective_to": "2099-12-31",
                "source_name": "SEC_EDGAR_SIC_snapshot_2026-09-07",
                "source_url_or_snapshot_id": submission_url,
                "source_snapshot_sha256": snapshot_hash,
                "gics_definition_url": GICS_DEFINITION_URL,
                "reviewed_by": "Felipe Taruselli",
                "reviewed_on": "",
                "approved": "false",
                "review_status": status,
            }
        )

        print(
            f"{number + 1}/{len(universe)} "
            f"{symbol}: SIC {sic} — {sic_description}"
        )

    except Exception as exc:
        rows.append(
            {
                "symbol": symbol,
                "company_name": ticker_record["company_name"],
                "proposed_sector": proposed_sector,
                "verified_sector": "",
                "sec_cik": f"{cik:010d}",
                "sec_sic": "",
                "sec_sic_description": "",
                "effective_from": "2026-09-08",
                "effective_to": "2099-12-31",
                "source_name": "",
                "source_url_or_snapshot_id": submission_url,
                "source_snapshot_sha256": "",
                "gics_definition_url": GICS_DEFINITION_URL,
                "reviewed_by": "Felipe Taruselli",
                "reviewed_on": "",
                "approved": "false",
                "review_status": f"error: {exc}",
            }
        )

review = pd.DataFrame(rows)
review.to_csv(OUTPUT_PATH, index=False)

print()
print(f"Saved {len(review)} review rows to:")
print(OUTPUT_PATH)
print()
print(review["review_status"].value_counts(dropna=False))
