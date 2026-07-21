from __future__ import annotations
import pandas as pd
from lightgbm import LGBMRanker

def fit_ranker(frame: pd.DataFrame, features: list[str], target: str, date_col: str) -> LGBMRanker:
    ordered = frame.sort_values(date_col)
    groups = ordered.groupby(date_col, sort=True).size().to_numpy()
    labels = pd.qcut(ordered[target], q=5, labels=False, duplicates="drop").astype(int)
    model = LGBMRanker(
        objective="lambdarank",
        n_estimators=500,
        learning_rate=0.03,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    model.fit(ordered[features], labels, group=groups)
    return model
