from datetime import (
    UTC,
    datetime,
    timedelta,
)

import pandas as pd

from finai.application.services.v31_learning_service import (
    BUY,
    HOLD,
    SELL,
    FEATURE_COLUMNS,
    V31LearningService,
)


def make_service() -> V31LearningService:
    return V31LearningService(
        database_url=(
            "sqlite+pysqlite:///:memory:"
        ),
        artifact_directory=(
            "artifacts/test-v31"
        ),
        minimum_rows=500,
        forward_horizon_bars=5,
        target_minimum_edge_bps=8.0,
        round_trip_cost_bps=4.0,
        walk_forward_folds=5,
        minimum_balanced_accuracy=0.34,
        minimum_macro_f1=0.30,
        minimum_net_return=0.0,
        minimum_trades=20,
        minimum_promotion_improvement=0.0025,
        signal_probability_threshold=0.55,
        require_non_mock_data=True,
    )


def make_frame(
    *,
    rows: int = 200,
) -> pd.DataFrame:
    start = datetime(
        2026,
        1,
        1,
        14,
        30,
        tzinfo=UTC,
    )

    records = []

    close = 100.0

    for index in range(rows):
        drift = (
            0.08
            if index % 11 < 6
            else -0.06
        )

        close += drift

        records.append(
            {
                "timestamp": (
                    start
                    + timedelta(
                        minutes=index
                    )
                ),
                "open_price": (
                    close - 0.02
                ),
                "high_price": (
                    close + 0.08
                ),
                "low_price": (
                    close - 0.08
                ),
                "close_price": close,
                "volume": (
                    1000
                    + index * 7
                ),
                "provider": "alpaca",
            }
        )

    return pd.DataFrame(
        records
    )


def test_v31_features_are_created() -> None:
    service = make_service()

    result = service.build_features(
        make_frame(),
        include_target=True,
    )

    assert not result.empty

    for column in FEATURE_COLUMNS:
        assert column in result.columns

    assert "forward_return" in result.columns
    assert "target" in result.columns


def test_v31_target_values_are_valid() -> None:
    service = make_service()

    result = service.build_features(
        make_frame(),
        include_target=True,
    )

    assert set(
        result["target"].unique()
    ).issubset(
        {
            SELL,
            HOLD,
            BUY,
        }
    )