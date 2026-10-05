from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

KEYS = ["timestamp", "symbol"]


@dataclass(frozen=True)
class Config:
    horizon: int = 5
    train_periods: int = 504
    test_periods: int = 21
    embargo_periods: int = 5
    min_train_periods: int = 252
    min_symbols: int = 8
    long_fraction: float = 0.20
    gross_limit: float = 1.0
    position_limit: float = 0.10
    turnover_penalty: float = 0.002
    risk_penalty: float = 8.0
    cost_bps: float = 5.0
    ic_lookback: int = 126
    ic_floor: float = 0.005
    seed: int = 17
    rebalance_every: int = 1


def read_frame(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p)
    if p.name.lower().endswith(".pkl.gz"):
        return pd.read_pickle(p)
    return pd.read_parquet(p)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def write_frame(frame: pd.DataFrame, path: Path) -> Path:
    try:
        frame.to_parquet(path, index=False)
        return path
    except (ImportError, ModuleNotFoundError):
        fallback = path.with_suffix(".pkl.gz")
        frame.to_pickle(fallback, compression="gzip")
        return fallback


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize(frame: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    required = set(KEYS + ["close"])
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Input is missing required columns: {sorted(missing)}")
    out = frame.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
    out["symbol"] = out["symbol"].astype(str).str.upper().str.strip()
    out = out.sort_values(KEYS).drop_duplicates(KEYS, keep="last")
    out["forward_return"] = out.groupby("symbol", observed=True)["close"].transform(
        lambda s: s.shift(-cfg.horizon) / s - 1.0
    )
    counts = out.groupby("timestamp", observed=True)["symbol"].transform("nunique")
    out = out.loc[counts >= cfg.min_symbols].copy()
    if out.empty:
        raise ValueError(f"No dates have at least {cfg.min_symbols} symbols")
    return out


def numeric_features(frame: pd.DataFrame) -> list[str]:
    forbidden = {
        "timestamp", "symbol", "close", "forward_return", "target", "label",
        "future_return", "next_return", "ensemble_signal", "weight", "return",
    }
    result = []
    for column in frame.select_dtypes(include=[np.number]).columns:
        lower = column.lower()
        if lower in forbidden or "forward" in lower or "future" in lower:
            continue
        if frame[column].notna().sum() > 50 and frame[column].nunique(dropna=True) > 2:
            result.append(column)
    if not result:
        raise ValueError("No usable numeric features remain after leakage filtering")
    return result


def config_dict(cfg: Config) -> dict:
    return asdict(cfg)
