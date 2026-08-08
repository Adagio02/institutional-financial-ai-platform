from datetime import UTC, datetime
from types import SimpleNamespace

import pandas as pd
import pytest

from finai.application.services.dataset_builder_service import (
    DatasetBuilderService,
)


def test_bars_to_price_frame_uses_close_price() -> None:
    bars = [
        SimpleNamespace(
            timestamp=datetime(
                2026,
                1,
                1,
                tzinfo=UTC,
            ),
            close_price=100.0,
        ),
        SimpleNamespace(
            timestamp=datetime(
                2026,
                1,
                2,
                tzinfo=UTC,
            ),
            close_price=105.0,
        ),
    ]

    frame = DatasetBuilderService._bars_to_price_frame(bars)

    assert list(frame.columns) == ["close"]

    assert frame.iloc[0]["close"] == pytest.approx(100.0)

    assert frame.iloc[1]["close"] == pytest.approx(105.0)


def test_features_and_prices_join_by_timestamp() -> None:
    timestamps = pd.DatetimeIndex(
        [
            datetime(
                2026,
                1,
                1,
                tzinfo=UTC,
            ),
            datetime(
                2026,
                1,
                2,
                tzinfo=UTC,
            ),
        ]
    )

    feature_frame = pd.DataFrame(
        {
            "simple_return": [
                0.01,
                0.02,
            ],
            "momentum_10": [
                1.0,
                2.0,
            ],
        },
        index=timestamps,
    )

    price_frame = pd.DataFrame(
        {
            "close": [
                100.0,
                105.0,
            ],
        },
        index=timestamps,
    )

    result = DatasetBuilderService._combine_features_and_prices(
        feature_frame=feature_frame,
        price_frame=price_frame,
    )

    assert list(result.columns) == [
        "simple_return",
        "momentum_10",
        "close",
    ]

    assert result.iloc[0]["close"] == pytest.approx(100.0)

    assert result.iloc[1]["close"] == pytest.approx(105.0)


def test_price_join_does_not_use_future_timestamp() -> None:
    feature_timestamp = datetime(
        2026,
        1,
        1,
        tzinfo=UTC,
    )

    future_timestamp = datetime(
        2026,
        1,
        2,
        tzinfo=UTC,
    )

    feature_frame = pd.DataFrame(
        {
            "simple_return": [
                0.01,
            ],
        },
        index=pd.DatetimeIndex([feature_timestamp]),
    )

    price_frame = pd.DataFrame(
        {
            "close": [
                999.0,
            ],
        },
        index=pd.DatetimeIndex([future_timestamp]),
    )

    with pytest.raises(
        ValueError,
        match="do not share any timestamps",
    ):
        (
            DatasetBuilderService._combine_features_and_prices(
                feature_frame=feature_frame,
                price_frame=price_frame,
            )
        )
