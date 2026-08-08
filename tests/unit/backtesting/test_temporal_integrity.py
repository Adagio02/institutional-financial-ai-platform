import pandas as pd


def test_prediction_at_row_t_cannot_use_row_t_plus_one() -> None:
    frame = pd.DataFrame(
        {
            "feature": [
                1.0,
                2.0,
                3.0,
                9999.0,
            ]
        }
    )

    original_past = frame.iloc[:3].copy()

    modified = frame.copy()
    modified.iloc[3, 0] = -9999.0

    pd.testing.assert_frame_equal(
        original_past,
        modified.iloc[:3],
    )


def test_backtest_indices_are_monotonic() -> None:
    timestamps = pd.date_range(
        "2026-01-01",
        periods=10,
        freq="D",
        tz="UTC",
    )

    assert timestamps.is_monotonic_increasing
