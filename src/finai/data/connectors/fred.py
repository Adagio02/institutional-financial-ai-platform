from __future__ import annotations
import httpx
import polars as pl
from finai.core.config import get_settings
from finai.data.connectors.base import DataConnector


class FredConnector(DataConnector):
    url = "https://api.stlouisfed.org/fred/series/observations"

    def fetch(
        self, series_id: str, observation_start: str = "1900-01-01", **_: object
    ) -> pl.DataFrame:
        settings = get_settings()
        if not settings.fred_api_key:
            raise RuntimeError("FRED_API_KEY is required")
        params = {
            "series_id": series_id,
            "api_key": settings.fred_api_key,
            "file_type": "json",
            "observation_start": observation_start,
        }
        response = httpx.get(self.url, params=params, timeout=60)
        response.raise_for_status()
        rows = response.json()["observations"]
        return pl.DataFrame(
            {
                "series_id": [series_id] * len(rows),
                "date": [r["date"] for r in rows],
                "value": [None if r["value"] == "." else float(r["value"]) for r in rows],
                "realtime_start": [r["realtime_start"] for r in rows],
                "realtime_end": [r["realtime_end"] for r in rows],
            }
        ).with_columns(
            pl.col("date").str.to_date(),
            pl.col("realtime_start").str.to_date(),
            pl.col("realtime_end").str.to_date(),
        )
