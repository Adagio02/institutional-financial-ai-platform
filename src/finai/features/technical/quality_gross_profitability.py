"""Gross profit divided by assets."""
import polars as pl

def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("quality_gross_profitability")
    return pl.Series("quality_gross_profitability", [None] * df.height, dtype=pl.Float64)
