import pandas as pd


def validate_dataset_frame(
    frame: pd.DataFrame,
) -> None:
    if frame.empty:
        raise ValueError("Dataset cannot be empty.")

    if not frame.index.is_monotonic_increasing:
        raise ValueError("Dataset timestamps must be ordered.")

    if frame.index.has_duplicates:
        raise ValueError("Dataset timestamps must be unique.")


def validate_no_future_columns(
    frame: pd.DataFrame,
) -> None:
    forbidden_tokens = (
        "future",
        "forward_",
        "next_",
    )

    for column in frame.columns:
        normalized_column = column.lower()

        if any(token in normalized_column for token in forbidden_tokens):
            raise ValueError(f"Potential future-data column detected: {column}")
