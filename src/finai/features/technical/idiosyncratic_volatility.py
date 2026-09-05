"""Residual volatility after factor adjustment."""

import polars as pl


def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("idiosyncratic_volatility")
    return pl.Series("idiosyncratic_volatility", [None] * df.height, dtype=pl.Float64)
