"""Return on equity."""
import polars as pl

def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("quality_roe")
    return pl.Series("quality_roe", [None] * df.height, dtype=pl.Float64)
