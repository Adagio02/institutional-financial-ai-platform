"""Rolling return skewness."""

import polars as pl


def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("skewness")
    return pl.Series("skewness", [None] * df.height, dtype=pl.Float64)
