"""Price relative to long moving average."""

import polars as pl


def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("trend_sma")
    return pl.Series("trend_sma", [None] * df.height, dtype=pl.Float64)
