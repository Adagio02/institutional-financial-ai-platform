from datetime import (
    UTC,
    datetime,
    timedelta,
)

import pandas as pd

from finai.application.services.adaptive_learning_service import (
    FEATURE_COLUMNS,
    AdaptiveLearningService,
)


def make_frame(
    *,
    rows: int = 40,
) -> pd.DataFrame:
    start = datetime(
        2026,
        1,
        1,
        tzinfo=UTC,
    )

    records = []

    for index in range(rows):
        close = (
            100.0
            + index
            + (
                0.5
                if index % 2 == 0
                else -0.25
            )
        )

        records.append(
            {
                "timestamp": (
                    start
                    + timedelta(
                        minutes=index
                    )
                ),
                "open_price": (
                    close
                    - 0.25
                ),
                "high_price": (
                    close
                    + 0.50
                ),
                "low_price": (
                    close
                    - 0.50
                ),
                "close_price": close,
                "volume": (
                    1000
                    + index * 10
                ),
                "provider": "test",
            }
        )

    return pd.DataFrame(
        records
    )


def test_training_features_are_created() -> None:
    result = (
        AdaptiveLearningService
        .build_features(
            make_frame(),
            include_target=True,
        )
    )

    assert not result.empty

    for column in FEATURE_COLUMNS:
        assert column in result.columns

    assert "target" in result.columns


def test_signal_features_do_not_require_target() -> None:
    result = (
        AdaptiveLearningService
        .build_features(
            make_frame(),
            include_target=False,
        )
    )

    assert not result.empty

    assert "target" not in result.columns