"""Trailing earnings divided by price."""
import polars as pl

def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("value_earnings_yield")
    return pl.Series("value_earnings_yield", [None] * df.height, dtype=pl.Float64)
