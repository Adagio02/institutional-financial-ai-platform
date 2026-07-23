"""Annual asset growth."""

import polars as pl


def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("investment_asset_growth")
    return pl.Series("investment_asset_growth", [None] * df.height, dtype=pl.Float64)
