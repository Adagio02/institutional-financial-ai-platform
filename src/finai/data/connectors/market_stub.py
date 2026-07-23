from __future__ import annotations
from datetime import date
import polars as pl
from finai.data.connectors.base import DataConnector


class MarketDataConnector(DataConnector):
    def fetch(self, tickers: list[str], start: date, end: date, **_: object) -> pl.DataFrame:
        raise RuntimeError(
            "Configure an approved market-data provider. "
            "The repository intentionally does not scrape restricted exchange feeds."
        )
