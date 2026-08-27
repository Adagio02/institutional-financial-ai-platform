from __future__ import annotations

import numpy as np
import pandas as pd


V41_FEATURE_COLUMNS = [
    # Target-asset momentum
    "return_1",
    "return_3",
    "return_5",
    "return_10",
    "return_15",
    "return_30",
    "return_60",

    # Realized volatility
    "volatility_5",
    "volatility_20",
    "volatility_60",

    # Volatility-normalized momentum
    "normalized_momentum_5",
    "normalized_momentum_15",
    "normalized_momentum_30",

    # Candle/range structure
    "range_pct",
    "body_pct",
    "atr_14_pct",
    "range_expansion_20",

    # Volume/liquidity
    "volume_change",
    "volume_zscore_20",
    "volume_zscore_60",
    "dollar_volume_zscore_20",

    # Trend
    "ema_gap_10_30",
    "ema_gap_20_60",
    "price_vs_ema_20",
    "price_vs_ema_60",
    "trend_strength",
    "trend_persistence_10",

    # VWAP
    "price_vs_vwap_20",
    "price_vs_vwap_60",

    # SPY
    "spy_return_1",
    "spy_return_5",
    "spy_return_15",
    "spy_return_30",
    "spy_return_60",
    "spy_volatility_20",

    # QQQ
    "qqq_return_1",
    "qqq_return_5",
    "qqq_return_15",
    "qqq_return_30",
    "qqq_return_60",
    "qqq_volatility_20",

    # Relative strength
    "relative_spy_1",
    "relative_spy_5",
    "relative_spy_15",
    "relative_spy_30",
    "relative_spy_60",
    "relative_qqq_1",
    "relative_qqq_5",
    "relative_qqq_15",
    "relative_qqq_30",
    "relative_qqq_60",

    # Market relationship
    "rolling_beta_spy_60",
    "rolling_corr_spy_60",
    "rolling_corr_qqq_60",
    "market_dispersion_1",
    "market_momentum",
    "market_volatility",

    # Time/session
    "minute_sin",
    "minute_cos",
    "minutes_from_open",
    "minutes_to_close",
    "opening_session",
    "closing_session",
]


def _prepare(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    result = frame.copy()

    result["timestamp"] = pd.to_datetime(
        result["timestamp"],
        utc=True,
    )

    result = (
        result
        .sort_values("timestamp")
        .drop_duplicates(
            subset=["timestamp"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    return result


def _returns(
    close: pd.Series,
    periods: int,
) -> pd.Series:
    return close.pct_change(
        periods=periods,
        fill_method=None,
    )


def _safe_divide(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    return (
        numerator
        / denominator.replace(
            0.0,
            np.nan,
        )
    )


def _zscore(
    series: pd.Series,
    window: int,
) -> pd.Series:
    rolling = series.rolling(
        window
    )

    return (
        (series - rolling.mean())
        / rolling.std()
    )


def build_v41_features(
    *,
    target_bars: pd.DataFrame,
    spy_bars: pd.DataFrame,
    qqq_bars: pd.DataFrame,
    forward_horizon_bars: int,
    minimum_edge_bps: float,
    round_trip_cost_bps: float = 0.0,
    include_target: bool = True,
) -> pd.DataFrame:
    if forward_horizon_bars <= 0:
        raise ValueError(
            "forward_horizon_bars must be positive."
        )

    if minimum_edge_bps < 0.0:
        raise ValueError(
            "minimum_edge_bps cannot be negative."
        )

    if round_trip_cost_bps < 0.0:
        raise ValueError(
            "round_trip_cost_bps cannot be negative."
        )

    target = _prepare(
        target_bars
    )

    spy = _prepare(
        spy_bars
    )

    qqq = _prepare(
        qqq_bars
    )

    spy = spy[
        [
            "timestamp",
            "close_price",
        ]
    ].rename(
        columns={
            "close_price": "spy_close",
        }
    )

    qqq = qqq[
        [
            "timestamp",
            "close_price",
        ]
    ].rename(
        columns={
            "close_price": "qqq_close",
        }
    )

    result = target.merge(
        spy,
        on="timestamp",
        how="inner",
        validate="one_to_one",
    )

    result = result.merge(
        qqq,
        on="timestamp",
        how="inner",
        validate="one_to_one",
    )

    close = result[
        "close_price"
    ].astype(float)

    open_price = result[
        "open_price"
    ].astype(float)

    high = result[
        "high_price"
    ].astype(float)

    low = result[
        "low_price"
    ].astype(float)

    volume = result[
        "volume"
    ].astype(float)

    spy_close = result[
        "spy_close"
    ].astype(float)

    qqq_close = result[
        "qqq_close"
    ].astype(float)

    #
    # Returns
    #

    for periods in (
        1,
        3,
        5,
        10,
        15,
        30,
        60,
    ):
        result[
            f"return_{periods}"
        ] = _returns(
            close,
            periods,
        )

    return_1 = result[
        "return_1"
    ]

    #
    # Volatility
    #

    result["volatility_5"] = (
        return_1
        .rolling(5)
        .std()
    )

    result["volatility_20"] = (
        return_1
        .rolling(20)
        .std()
    )

    result["volatility_60"] = (
        return_1
        .rolling(60)
        .std()
    )

    #
    # Volatility-normalized momentum
    #

    result[
        "normalized_momentum_5"
    ] = _safe_divide(
        result["return_5"],
        result["volatility_20"],
    )

    result[
        "normalized_momentum_15"
    ] = _safe_divide(
        result["return_15"],
        result["volatility_20"],
    )

    result[
        "normalized_momentum_30"
    ] = _safe_divide(
        result["return_30"],
        result["volatility_60"],
    )

    #
    # Candle/range features
    #

    result["range_pct"] = (
        _safe_divide(
            high - low,
            close,
        )
    )

    result["body_pct"] = (
        _safe_divide(
            close - open_price,
            open_price,
        )
    )

    previous_close = close.shift(
        1
    )

    true_range = pd.concat(
        [
            high - low,
            (
                high
                - previous_close
            ).abs(),
            (
                low
                - previous_close
            ).abs(),
        ],
        axis=1,
    ).max(
        axis=1
    )

    atr_14 = (
        true_range
        .rolling(14)
        .mean()
    )

    result[
        "atr_14_pct"
    ] = _safe_divide(
        atr_14,
        close,
    )

    average_range_20 = (
        result[
            "range_pct"
        ]
        .rolling(20)
        .mean()
    )

    result[
        "range_expansion_20"
    ] = _safe_divide(
        result["range_pct"],
        average_range_20,
    )

    #
    # Volume features
    #

    result[
        "volume_change"
    ] = volume.pct_change(
        fill_method=None
    )

    result[
        "volume_zscore_20"
    ] = _zscore(
        volume,
        20,
    )

    result[
        "volume_zscore_60"
    ] = _zscore(
        volume,
        60,
    )

    dollar_volume = (
        close
        * volume
    )

    result[
        "dollar_volume_zscore_20"
    ] = _zscore(
        dollar_volume,
        20,
    )

    #
    # Trend features
    #

    ema_10 = close.ewm(
        span=10,
        adjust=False,
    ).mean()

    ema_20 = close.ewm(
        span=20,
        adjust=False,
    ).mean()

    ema_30 = close.ewm(
        span=30,
        adjust=False,
    ).mean()

    ema_60 = close.ewm(
        span=60,
        adjust=False,
    ).mean()

    result[
        "ema_gap_10_30"
    ] = _safe_divide(
        ema_10 - ema_30,
        close,
    )

    result[
        "ema_gap_20_60"
    ] = _safe_divide(
        ema_20 - ema_60,
        close,
    )

    result[
        "price_vs_ema_20"
    ] = _safe_divide(
        close - ema_20,
        ema_20,
    )

    result[
        "price_vs_ema_60"
    ] = _safe_divide(
        close - ema_60,
        ema_60,
    )

    result[
        "trend_strength"
    ] = _safe_divide(
        (
            ema_10
            - ema_60
        ).abs(),
        atr_14,
    )

    direction = np.sign(
        return_1
    )

    result[
        "trend_persistence_10"
    ] = (
        direction
        .rolling(10)
        .mean()
    )

    #
    # Rolling VWAP approximation
    #

    typical_price = (
        high
        + low
        + close
    ) / 3.0

    price_volume = (
        typical_price
        * volume
    )

    for window in (
        20,
        60,
    ):
        rolling_vwap = (
            price_volume
            .rolling(window)
            .sum()
            / volume
            .rolling(window)
            .sum()
            .replace(
                0.0,
                np.nan,
            )
        )

        result[
            f"price_vs_vwap_{window}"
        ] = _safe_divide(
            close - rolling_vwap,
            rolling_vwap,
        )

    #
    # Market features
    #

    for periods in (
        1,
        5,
        15,
        30,
        60,
    ):
        result[
            f"spy_return_{periods}"
        ] = _returns(
            spy_close,
            periods,
        )

        result[
            f"qqq_return_{periods}"
        ] = _returns(
            qqq_close,
            periods,
        )

    spy_return_1 = result[
        "spy_return_1"
    ]

    qqq_return_1 = result[
        "qqq_return_1"
    ]

    result[
        "spy_volatility_20"
    ] = (
        spy_return_1
        .rolling(20)
        .std()
    )

    result[
        "qqq_volatility_20"
    ] = (
        qqq_return_1
        .rolling(20)
        .std()
    )

    for periods in (
        1,
        5,
        15,
        30,
        60,
    ):
        result[
            f"relative_spy_{periods}"
        ] = (
            result[
                f"return_{periods}"
            ]
            - result[
                f"spy_return_{periods}"
            ]
        )

        result[
            f"relative_qqq_{periods}"
        ] = (
            result[
                f"return_{periods}"
            ]
            - result[
                f"qqq_return_{periods}"
            ]
        )

    rolling_covariance = (
        return_1
        .rolling(60)
        .cov(
            spy_return_1
        )
    )

    rolling_spy_variance = (
        spy_return_1
        .rolling(60)
        .var()
    )

    result[
        "rolling_beta_spy_60"
    ] = _safe_divide(
        rolling_covariance,
        rolling_spy_variance,
    )

    result[
        "rolling_corr_spy_60"
    ] = (
        return_1
        .rolling(60)
        .corr(
            spy_return_1
        )
    )

    result[
        "rolling_corr_qqq_60"
    ] = (
        return_1
        .rolling(60)
        .corr(
            qqq_return_1
        )
    )

    result[
        "market_dispersion_1"
    ] = (
        spy_return_1
        - qqq_return_1
    ).abs()

    result[
        "market_momentum"
    ] = (
        result["spy_return_15"]
        + result["qqq_return_15"]
    ) / 2.0

    result[
        "market_volatility"
    ] = (
        result["spy_volatility_20"]
        + result["qqq_volatility_20"]
    ) / 2.0

    #
    # Session/time features
    #
    # Timestamps are UTC.
    #
    # 13:30-20:00 UTC approximates the regular
    # U.S. session while EDT is in effect.
    #
    # We deliberately keep cyclical time features
    # as the universally valid component and use
    # session-relative features as additional signals.
    #

    timestamp = result[
        "timestamp"
    ]

    minute_of_day = (
        timestamp.dt.hour
        * 60
        + timestamp.dt.minute
    )

    angle = (
        2.0
        * np.pi
        * minute_of_day
        / 1440.0
    )

    result[
        "minute_sin"
    ] = np.sin(
        angle
    )

    result[
        "minute_cos"
    ] = np.cos(
        angle
    )

    market_open_minute = (
        13 * 60
        + 30
    )

    market_close_minute = (
        20 * 60
    )

    result[
        "minutes_from_open"
    ] = (
        minute_of_day
        - market_open_minute
    )

    result[
        "minutes_to_close"
    ] = (
        market_close_minute
        - minute_of_day
    )

    result[
        "opening_session"
    ] = (
        (
            result[
                "minutes_from_open"
            ]
            >= 0
        )
        & (
            result[
                "minutes_from_open"
            ]
            < 60
        )
    ).astype(float)

    result[
        "closing_session"
    ] = (
        (
            result[
                "minutes_to_close"
            ]
            >= 0
        )
        & (
            result[
                "minutes_to_close"
            ]
            < 60
        )
    ).astype(float)

    #
    # Cost-aware target
    #

    if include_target:
        future_close = close.shift(
            -forward_horizon_bars
        )

        result[
            "forward_return"
        ] = (
            future_close
            / close
            - 1.0
        )

        required_edge_bps = (
            minimum_edge_bps
            + round_trip_cost_bps
        )

        required_edge = (
            required_edge_bps
            / 10_000.0
        )

        result[
            "target"
        ] = np.select(
            [
                result[
                    "forward_return"
                ]
                > required_edge,

                result[
                    "forward_return"
                ]
                < -required_edge,
            ],
            [
                1,
                -1,
            ],
            default=0,
        )

    required = list(
        V41_FEATURE_COLUMNS
    )

    if include_target:
        required.extend(
            [
                "forward_return",
                "target",
            ]
        )

    result = result.replace(
        [
            np.inf,
            -np.inf,
        ],
        np.nan,
    )

    result = result.dropna(
        subset=required
    )

    if include_target:
        result[
            "target"
        ] = (
            result[
                "target"
            ]
            .astype(int)
        )

    return result.reset_index(
        drop=True
    )