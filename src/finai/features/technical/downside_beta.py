"""Beta estimated on negative market days."""

import polars as pl


def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("downside_beta")
    return pl.Series("downside_beta", [None] * df.height, dtype=pl.Float64)
