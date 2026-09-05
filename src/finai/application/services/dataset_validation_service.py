import pandas as pd

from finai.domain.datasets.validation import (
    validate_dataset_frame,
    validate_no_future_columns,
)


class DatasetValidationService:
    def validate(
        self,
        frame: pd.DataFrame,
    ) -> None:
        validate_dataset_frame(frame)
        validate_no_future_columns(frame)
