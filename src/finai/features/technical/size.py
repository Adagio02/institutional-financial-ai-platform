"""Log market capitalization."""

import polars as pl


def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("size")
    return pl.Series("size", [None] * df.height, dtype=pl.Float64)
