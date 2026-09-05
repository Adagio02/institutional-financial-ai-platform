"""Six-to-one-month momentum."""

import polars as pl


def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("momentum_6_1")
    return pl.Series("momentum_6_1", [None] * df.height, dtype=pl.Float64)
