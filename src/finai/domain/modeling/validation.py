import pandas as pd


def validate_training_frame(
    frame: pd.DataFrame,
    *,
    feature_columns: list[str],
    target_column: str,
) -> None:
    if frame.empty:
        raise ValueError("Training dataset cannot be empty.")

    if not frame.index.is_monotonic_increasing:
        raise ValueError("Training data must be ordered by timestamp.")

    if frame.index.has_duplicates:
        raise ValueError("Training timestamps must be unique.")

    missing_columns = sorted(set(feature_columns + [target_column]) - set(frame.columns))

    if missing_columns:
        raise ValueError("Training data is missing columns: " + ", ".join(missing_columns))

    if not feature_columns:
        raise ValueError("At least one feature column is required.")


def validate_walk_forward_settings(
    *,
    number_of_rows: int,
    number_of_splits: int,
    test_size: int,
) -> None:
    if number_of_splits < 1:
        raise ValueError("number_of_splits must be at least one.")

    if test_size < 1:
        raise ValueError("test_size must be at least one.")

    minimum_rows = (number_of_splits * test_size) + test_size

    if number_of_rows < minimum_rows:
        raise ValueError(
            "Dataset does not contain enough rows for the requested walk-forward configuration."
        )
