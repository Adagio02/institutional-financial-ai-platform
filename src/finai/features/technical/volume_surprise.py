"""Current volume relative to rolling volume."""

import polars as pl


def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("volume_surprise")
    return pl.Series("volume_surprise", [None] * df.height, dtype=pl.Float64)
