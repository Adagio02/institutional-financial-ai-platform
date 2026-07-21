import polars as pl

def add_technical_features(df: pl.DataFrame) -> pl.DataFrame:
    ordered = df.sort(["ticker", "date"])
    return (
        ordered.with_columns(
            (pl.col("adjusted_close") / pl.col("adjusted_close").shift(1) - 1)
            .over("ticker").alias("ret_1d"),
            (pl.col("adjusted_close") / pl.col("adjusted_close").shift(5) - 1)
            .over("ticker").alias("mom_5d"),
            (pl.col("adjusted_close") / pl.col("adjusted_close").shift(21) - 1)
            .over("ticker").alias("mom_21d"),
            (pl.col("adjusted_close") / pl.col("adjusted_close").shift(252) - 1)
            .over("ticker").alias("mom_252d"),
        )
        .with_columns(
            pl.col("ret_1d").rolling_std(21).over("ticker").alias("vol_21d"),
            pl.col("ret_1d").rolling_std(63).over("ticker").alias("vol_63d"),
            pl.col("adjusted_close").rolling_mean(20).over("ticker").alias("sma_20"),
            pl.col("adjusted_close").rolling_mean(200).over("ticker").alias("sma_200"),
            pl.col("volume").rolling_mean(20).over("ticker").alias("volume_20d"),
        )
        .with_columns(
            (pl.col("adjusted_close") / pl.col("sma_20") - 1).alias("price_vs_sma20"),
            (pl.col("adjusted_close") / pl.col("sma_200") - 1).alias("price_vs_sma200"),
            (pl.col("volume") / pl.col("volume_20d")).alias("relative_volume"),
        )
    )
