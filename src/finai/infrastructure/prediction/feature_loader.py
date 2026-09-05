from datetime import datetime
from pathlib import Path

import pandas as pd


class FeatureLoader:
    def load_latest_row(
        self,
        *,
        dataset_uri: str,
        feature_columns: list[str],
        prediction_timestamp: datetime | None = None,
    ) -> tuple[datetime, pd.DataFrame]:
        path = Path(dataset_uri)

        if not path.exists():
            raise FileNotFoundError(f"Dataset file does not exist: {path}")

        frame = pd.read_parquet(path).sort_index()

        if prediction_timestamp is not None:
            frame = frame.loc[frame.index <= prediction_timestamp]

        if frame.empty:
            raise ValueError(
                "No feature observations exist at or before the requested prediction timestamp."
            )

        selected = frame[feature_columns].dropna()

        if selected.empty:
            raise ValueError("No complete feature row is available.")

        timestamp = selected.index[-1]
        row = selected.iloc[[-1]].copy()

        normalized_timestamp = timestamp

        if hasattr(timestamp, "to_pydatetime"):
            normalized_timestamp = timestamp.to_pydatetime()

        return normalized_timestamp, row
