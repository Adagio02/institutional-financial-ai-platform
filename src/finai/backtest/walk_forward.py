from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class Fold:
    train: pd.DataFrame
    validation: pd.DataFrame

def expanding_folds(
    frame: pd.DataFrame,
    date_col: str,
    validation_years: list[int],
    embargo_days: int = 5,
):
    dates = pd.to_datetime(frame[date_col])
    for year in validation_years:
        validation_start = pd.Timestamp(year=year, month=1, day=1)
        cutoff = validation_start - pd.Timedelta(days=embargo_days)
        train = frame[dates < cutoff]
        validation = frame[dates.dt.year == year]
        if len(train) and len(validation):
            yield Fold(train=train, validation=validation)
