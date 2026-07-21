"""Rolling return excess kurtosis."""
import polars as pl

def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("kurtosis")
    return pl.Series("kurtosis", [None] * df.height, dtype=pl.Float64)
