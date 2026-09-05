from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_research_frame(frame: pd.DataFrame, base_path: Path) -> Path:
    """Prefer compressed Parquet and fall back to compressed pickle."""
    base_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path = base_path.with_suffix(".parquet")
    try:
        frame.to_parquet(parquet_path, index=False, compression="zstd")
        return parquet_path
    except ImportError:
        pickle_path = base_path.with_suffix(".pkl.gz")
        frame.to_pickle(pickle_path, compression="gzip")
        return pickle_path


def resolve_research_frame(base_path: Path) -> Path:
    candidates = [base_path, base_path.with_suffix(".parquet"), base_path.with_suffix(".pkl.gz")]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Research frame does not exist: {base_path}")


def read_research_frame(base_path: Path) -> pd.DataFrame:
    path = resolve_research_frame(base_path)
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_pickle(path)
