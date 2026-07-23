"""One-month reversal signal."""

import polars as pl


def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("short_term_reversal")
    return pl.Series("short_term_reversal", [None] * df.height, dtype=pl.Float64)
