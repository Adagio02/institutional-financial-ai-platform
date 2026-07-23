import polars as pl


def add_cross_sectional_target(df: pl.DataFrame, horizon: int = 5) -> pl.DataFrame:
    name = f"forward_return_{horizon}d"
    ranked = (
        df.sort(["ticker", "date"])
        .with_columns(
            (
                pl.col("adjusted_close").shift(-horizon).over("ticker") / pl.col("adjusted_close")
                - 1
            ).alias(name)
        )
        .with_columns(pl.col(name).rank("average").over("date").alias("target_rank"))
    )
    return ranked
