from __future__ import annotations

import numpy as np
import pandas as pd

from finai.domain.learning.v38_features import (
    V38_FEATURE_COLUMNS,
    build_v38_features,
)


def make_bars(
    *,
    scale: float,
    rows: int = 200,
) -> pd.DataFrame:
    timestamp = pd.date_range(
        "2026-01-02 14:30:00+00:00",
        periods=rows,
        freq="min",
    )

    trend = np.linspace(
        100.0,
        105.0,
        rows,
    )

    wave = np.sin(
        np.arange(rows) / 5.0
    )

    close = (
        trend
        + wave * scale
    )

    return pd.DataFrame(
        {
            "timestamp": timestamp,
            "open_price": close - 0.02,
            "high_price": close + 0.05,
            "low_price": close - 0.05,
            "close_price": close,
            "volume": (
                1000.0
                + np.arange(rows)
            ),
        }
    )


def test_v38_builds_features() -> None:
    dataset = build_v38_features(
        target_bars=make_bars(
            scale=1.0
        ),
        spy_bars=make_bars(
            scale=0.5
        ),
        qqq_bars=make_bars(
            scale=0.8
        ),
        forward_horizon_bars=5,
        minimum_edge_bps=2.0,
    )

    assert not dataset.empty

    for column in V38_FEATURE_COLUMNS:
        assert column in dataset.columns


def test_v38_target_classes_valid() -> None:
    dataset = build_v38_features(
        target_bars=make_bars(
            scale=1.5
        ),
        spy_bars=make_bars(
            scale=0.5
        ),
        qqq_bars=make_bars(
            scale=0.8
        ),
        forward_horizon_bars=5,
        minimum_edge_bps=1.0,
    )

    assert set(
        dataset["target"].unique()
    ).issubset(
        {-1, 0, 1}
    )


def test_v38_has_no_feature_nan() -> None:
    dataset = build_v38_features(
        target_bars=make_bars(
            scale=1.0
        ),
        spy_bars=make_bars(
            scale=0.7
        ),
        qqq_bars=make_bars(
            scale=0.9
        ),
        forward_horizon_bars=5,
        minimum_edge_bps=2.0,
    )

    assert not (
        dataset[
            V38_FEATURE_COLUMNS
        ]
        .isna()
        .any()
        .any()
    )