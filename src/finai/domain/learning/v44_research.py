from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class V44ResearchConfig:
    horizon_bars: int
    edge_bps: float
    training_window: str = "expanding"

    @property
    def key(self) -> str:
        return (
            f"h{self.horizon_bars}_"
            f"e{str(self.edge_bps).replace('.', 'p')}_"
            f"{self.training_window}"
        )


V44_HORIZON_GRID = (5, 15, 30, 60)
V44_EDGE_GRID = (3.0, 5.0, 8.0, 10.0)
V44_TRAINING_WINDOWS = ("expanding",)


FEATURE_FAMILIES: dict[str, tuple[str, ...]] = {
    "momentum": (
        "return_1",
        "return_5",
        "return_15",
        "return_30",
        "return_60",
    ),
    "volatility": (
        "volatility_5",
        "volatility_15",
        "volatility_30",
        "volatility_60",
        "market_volatility",
    ),
    "trend": (
        "ema_gap_10_30",
        "ema_gap_20_60",
        "price_vs_ema_20",
        "price_vs_ema_60",
        "trend_strength",
        "trend_persistence_10",
    ),
    "market_relative": (
        "relative_spy_1",
        "relative_spy_5",
        "relative_spy_15",
        "relative_spy_30",
        "relative_spy_60",
        "relative_qqq_1",
        "relative_qqq_5",
        "relative_qqq_15",
        "relative_qqq_30",
        "relative_qqq_60",
        "rolling_beta_spy_60",
        "rolling_corr_spy_60",
        "rolling_corr_qqq_60",
        "market_dispersion_1",
        "market_momentum",
    ),
    "session": (
        "minute_sin",
        "minute_cos",
        "minutes_from_open",
        "minutes_to_close",
        "opening_session",
        "closing_session",
    ),
}


def research_configs() -> tuple[V44ResearchConfig, ...]:
    return tuple(
        V44ResearchConfig(
            horizon_bars=horizon,
            edge_bps=edge,
            training_window=window,
        )
        for horizon in V44_HORIZON_GRID
        for edge in V44_EDGE_GRID
        for window in V44_TRAINING_WINDOWS
    )


def split_discovery_locked_final(
    frame: pd.DataFrame,
    *,
    locked_fraction: float = 0.10,
    final_fraction: float = 0.20,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not 0.0 < locked_fraction < 0.5:
        raise ValueError("locked_fraction must be between 0 and 0.5.")
    if not 0.0 < final_fraction < 0.5:
        raise ValueError("final_fraction must be between 0 and 0.5.")
    if locked_fraction + final_fraction >= 0.5:
        raise ValueError(
            "locked_fraction + final_fraction must be below 0.5."
        )

    total = len(frame)
    if total < 100:
        raise ValueError("Insufficient rows for V4.4 research partitions.")

    final_rows = max(1, int(total * final_fraction))
    locked_rows = max(1, int(total * locked_fraction))
    discovery_end = total - locked_rows - final_rows
    locked_end = total - final_rows

    discovery = frame.iloc[:discovery_end].copy()
    locked = frame.iloc[discovery_end:locked_end].copy()
    final = frame.iloc[locked_end:].copy()

    return discovery, locked, final


def purge_and_embargo(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    *,
    horizon_bars: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if horizon_bars <= 0:
        raise ValueError("horizon_bars must be positive.")

    purge = min(horizon_bars, max(0, len(train) - 1))
    embargo = min(horizon_bars, max(0, len(validation) - 1))

    purged_train = (
        train.iloc[:-purge].copy()
        if purge > 0
        else train.copy()
    )
    embargoed_validation = validation.iloc[embargo:].copy()

    return purged_train, embargoed_validation


def selection_penalized_fold_score(
    fold_returns: list[float],
    *,
    trial_count: int,
) -> dict[str, float]:
    if not fold_returns:
        return {
            "mean_fold_return": 0.0,
            "fold_std": 0.0,
            "selection_penalty": 0.0,
            "penalized_mean_fold_return": 0.0,
        }

    mu = float(mean(fold_returns))
    sigma = float(pstdev(fold_returns)) if len(fold_returns) > 1 else 0.0
    trials = max(2, int(trial_count))

    penalty = (
        sigma
        * math.sqrt(2.0 * math.log(trials))
        / math.sqrt(max(1, len(fold_returns)))
    )

    return {
        "mean_fold_return": mu,
        "fold_std": sigma,
        "selection_penalty": float(penalty),
        "penalized_mean_fold_return": float(mu - penalty),
    }


def freeze_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")

    digest = hashlib.sha256(canonical).hexdigest()

    return {
        "candidate": payload,
        "sha256": digest,
    }


def verify_frozen_payload(
    frozen: dict[str, Any],
) -> bool:
    expected = freeze_payload(
        frozen["candidate"]
    )["sha256"]
    return expected == frozen["sha256"]


def write_json(
    path: Path,
    payload: Any,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
