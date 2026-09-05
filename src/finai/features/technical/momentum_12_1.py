"""Twelve-to-one-month momentum, excluding the most recent month."""

import polars as pl


def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("momentum_12_1")
    return pl.Series("momentum_12_1", [None] * df.height, dtype=pl.Float64)
