from __future__ import annotations
import httpx
import polars as pl


class TreasuryFiscalConnector:
    endpoint = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates"

    def fetch(self, page_size: int = 1000) -> pl.DataFrame:
        response = httpx.get(
            self.endpoint,
            params={"page[size]": page_size, "sort": "-record_date"},
            timeout=60,
        )
        response.raise_for_status()
        return pl.DataFrame(response.json()["data"])
