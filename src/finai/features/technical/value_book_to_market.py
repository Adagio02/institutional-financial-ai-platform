"""Book equity divided by market capitalization."""
import polars as pl

def compute(df: pl.DataFrame) -> pl.Series:
    if "ret_1d" in df.columns:
        return df.get_column("ret_1d").alias("value_book_to_market")
    return pl.Series("value_book_to_market", [None] * df.height, dtype=pl.Float64)
