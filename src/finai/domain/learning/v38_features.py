from __future__ import annotations

import numpy as np
import pandas as pd


V38_FEATURE_COLUMNS = [
    "return_1",
    "return_3",
    "return_5",
    "return_10",
    "return_30",
    "volatility_5",
    "volatility_20",
    "volatility_60",
    "range_pct",
    "body_pct",
    "volume_change",
    "volume_zscore_20",
    "ema_gap_10_30",
    "price_vs_ema_20",
    "spy_return_1",
    "spy_return_5",
    "spy_return_30",
    "spy_volatility_20",
    "qqq_return_1",
    "qqq_return_5",
    "qqq_return_30",
    "qqq_volatility_20",
    "relative_spy_1",
    "relative_spy_5",
    "relative_spy_30",
    "relative_qqq_1",
    "relative_qqq_5",
    "relative_qqq_30",
    "market_dispersion_1",
    "market_momentum",
    "market_volatility",
    "minute_sin",
    "minute_cos",
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


def build_v38_features(
    *,
    target_bars: pd.DataFrame,
    spy_bars: pd.DataFrame,
    qqq_bars: pd.DataFrame,
    forward_horizon_bars: int,
    minimum_edge_bps: float,
    include_target: bool = True,
) -> pd.DataFrame:
    if forward_horizon_bars <= 0:
        raise ValueError(
            "forward_horizon_bars must be positive."
        )

    target = _prepare(target_bars)
    spy = _prepare(spy_bars)
    qqq = _prepare(qqq_bars)

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

    for periods in (
        1,
        3,
        5,
        10,
        30,
    ):
        result[
            f"return_{periods}"
        ] = _returns(
            close,
            periods,
        )

    base_return = _returns(
        close,
        1,
    )

    result["volatility_5"] = (
        base_return
        .rolling(5)
        .std()
    )

    result["volatility_20"] = (
        base_return
        .rolling(20)
        .std()
    )

    result["volatility_60"] = (
        base_return
        .rolling(60)
        .std()
    )

    result["range_pct"] = (
        (high - low)
        / close.replace(0.0, np.nan)
    )

    result["body_pct"] = (
        (close - open_price)
        / open_price.replace(
            0.0,
            np.nan,
        )
    )

    result["volume_change"] = (
        volume.pct_change(
            fill_method=None
        )
    )

    rolling_volume = (
        volume
        .rolling(20)
    )

    result["volume_zscore_20"] = (
        (
            volume
            - rolling_volume.mean()
        )
        / rolling_volume.std()
    )

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

    result["ema_gap_10_30"] = (
        (ema_10 - ema_30)
        / close.replace(
            0.0,
            np.nan,
        )
    )

    result["price_vs_ema_20"] = (
        (close - ema_20)
        / ema_20.replace(
            0.0,
            np.nan,
        )
    )

    for periods in (
        1,
        5,
        30,
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

    spy_return_1 = _returns(
        spy_close,
        1,
    )

    qqq_return_1 = _returns(
        qqq_close,
        1,
    )

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
        30,
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

    result[
        "market_dispersion_1"
    ] = (
        spy_return_1
        - qqq_return_1
    ).abs()

    result[
        "market_momentum"
    ] = (
        (
            result["spy_return_5"]
            + result["qqq_return_5"]
        )
        / 2.0
    )

    result[
        "market_volatility"
    ] = (
        (
            result["spy_volatility_20"]
            + result["qqq_volatility_20"]
        )
        / 2.0
    )

    timestamp = result[
        "timestamp"
    ]

    minute_of_day = (
        timestamp.dt.hour * 60
        + timestamp.dt.minute
    )

    angle = (
        2.0
        * np.pi
        * minute_of_day
        / 1440.0
    )

    result["minute_sin"] = (
        np.sin(angle)
    )

    result["minute_cos"] = (
        np.cos(angle)
    )

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

        edge = (
            minimum_edge_bps
            / 10_000.0
        )

        result["target"] = np.select(
            [
                result[
                    "forward_return"
                ] > edge,
                result[
                    "forward_return"
                ] < -edge,
            ],
            [
                1,
                -1,
            ],
            default=0,
        )

    required = list(
        V38_FEATURE_COLUMNS
    )

    if include_target:
        required.extend(
            [
                "forward_return",
                "target",
            ]
        )

    result = result.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    result = result.dropna(
        subset=required
    )

    if include_target:
        result["target"] = (
            result["target"]
            .astype(int)
        )

    return result.reset_index(
        drop=True
    )