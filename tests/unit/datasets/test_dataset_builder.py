from datetime import UTC, datetime

import pandas as pd

from finai.application.services.dataset_builder_service import (
    DatasetBuilderService,
)


def build_test_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "simple_return": [
                0.01,
                0.02,
            ],
            "rolling_mean_20": [
                100.0,
                101.0,
            ],
        },
        index=[
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
        ],
    )


def test_schema_hash_is_deterministic() -> None:
    first = build_test_frame()
    second = build_test_frame()

    first_hash = DatasetBuilderService._calculate_schema_hash(first)

    second_hash = DatasetBuilderService._calculate_schema_hash(second)

    assert first_hash == second_hash


def test_content_hash_is_deterministic() -> None:
    first = build_test_frame()
    second = build_test_frame()

    first_hash = DatasetBuilderService._calculate_content_hash(first)

    second_hash = DatasetBuilderService._calculate_content_hash(second)

    assert first_hash == second_hash


def test_content_hash_changes_with_data() -> None:
    first = build_test_frame()
    second = build_test_frame()

    second.iloc[0, 0] = 999.0

    first_hash = DatasetBuilderService._calculate_content_hash(first)

    second_hash = DatasetBuilderService._calculate_content_hash(second)

    assert first_hash != second_hash
