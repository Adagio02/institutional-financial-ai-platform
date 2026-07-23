from __future__ import annotations

import polars as pl


REQUIRED = {
    "ticker",
    "date",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
}


def validate_market_prices(df: pl.DataFrame) -> list[str]:
    """Validate the canonical daily market-price schema."""

    errors: list[str] = []

    missing = REQUIRED.difference(df.columns)

    if missing:
        errors.append(f"missing_columns={sorted(missing)}")
        return errors

    duplicate_rows = df.group_by(["ticker", "date"]).len().filter(pl.col("len") > 1)

    if duplicate_rows.height > 0:
        errors.append("duplicate_ticker_date")

    if df.filter(pl.col("high") < pl.col("low")).height > 0:
        errors.append("high_below_low")

    if df.filter(pl.col("volume") < 0).height > 0:
        errors.append("negative_volume")

    if df.filter(pl.col("adjusted_close") <= 0).height > 0:
        errors.append("nonpositive_adjusted_close")

    return errors
