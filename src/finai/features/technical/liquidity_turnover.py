"""Share turnover."""
import polars as pl

def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("liquidity_turnover")
    return pl.Series("liquidity_turnover", [None] * df.height, dtype=pl.Float64)
