from __future__ import annotations

import numpy as np
import pandas as pd

from finai.domain.learning.v46_events import (
    EVENT_FAMILIES,
    apply_event_family,
)


def _frame() -> pd.DataFrame:
    rows = 900
    timestamp = pd.date_range(
        "2026-01-05 14:30:00+00:00",
        periods=rows,
        freq="min",
    )
    x = np.arange(rows)

    return pd.DataFrame(
        {
            "timestamp": timestamp,
            "forward_return": np.sin(
                x / 20.0
            ) * 0.002,
            "return_5": np.sin(
                x / 13.0
            ) * 0.003,
            "return_15": np.sin(
                x / 21.0
            ) * 0.004,
            "return_60": np.sin(
                x / 33.0
            ) * 0.006,
            "relative_strength_15": np.sin(
                x / 17.0
            ) * 0.004,
            "price_vs_vwap_20": np.sin(
                x / 19.0
            ) * 0.003,
            "trend_strength": 1.0
            + np.abs(
                np.sin(
                    x / 25.0
                )
            ),
            "ema_gap_10_30": np.sin(
                x / 28.0
            ) * 0.002,
            "range_expansion_20": 1.0
            + np.abs(
                np.sin(
                    x / 11.0
                )
            ),
            "body_pct": np.sin(
                x / 9.0
            ) * 0.002,
            "relative_volume_20_60": 1.0
            + np.abs(
                np.sin(
                    x / 15.0
                )
            ),
            "opening_session": (
                (x % 390) < 60
            ).astype(float),
            "return_since_open": np.sin(
                x / 40.0
            ) * 0.005,
        }
    )


def test_all_event_families_build() -> None:
    frame = _frame()

    for family in EVENT_FAMILIES:
        result = apply_event_family(
            frame,
            family=family,
            round_trip_cost_bps=2.0,
        )

        assert len(result) == len(frame)
        assert (
            "event_direction"
            in result.columns
        )
        assert (
            "event_strength"
            in result.columns
        )
        assert (
            "meta_target"
            in result.columns
        )
        assert set(
            result[
                "event_direction"
            ].unique()
        ).issubset(
            {-1, 0, 1}
        )
