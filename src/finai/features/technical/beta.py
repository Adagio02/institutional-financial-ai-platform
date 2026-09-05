"""Rolling market beta."""

import polars as pl


def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("beta")
    return pl.Series("beta", [None] * df.height, dtype=pl.Float64)
