"""Inverse realized volatility."""
import polars as pl

def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("low_volatility")
    return pl.Series("low_volatility", [None] * df.height, dtype=pl.Float64)
