from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


V492_FACTOR_COLUMNS = [
    "market_excess_return_60",
    "volatility_60",
    "cross_sectional_rank_volume",
]


def _design_matrix(
    frame: pd.DataFrame,
    *,
    sector_column: str,
    factor_columns: list[str],
) -> tuple[np.ndarray, list[str]]:
    sector = pd.get_dummies(
        frame[sector_column].fillna("UNKNOWN").astype(str),
        prefix="sector",
        dtype=float,
    )
    factors = frame[factor_columns].apply(pd.to_numeric, errors="coerce")
    factors = factors.fillna(factors.median()).fillna(0.0)
    standard_deviation = factors.std(ddof=0).replace(0.0, 1.0)
    factors = (factors - factors.mean()) / standard_deviation
    design = pd.concat([sector.reset_index(drop=True), factors.reset_index(drop=True)], axis=1)
    return design.to_numpy(dtype=float), list(design.columns)


def neutralize_portfolio_section(
    frame: pd.DataFrame,
    *,
    weight_column: str = "weight",
    sector_column: str = "sector",
    factor_columns: list[str] | None = None,
    target_gross_exposure: float = 1.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    factors = list(factor_columns or V492_FACTOR_COLUMNS)
    required = {"symbol", weight_column, sector_column, *factors}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError("V4.9.2 portfolio frame missing: " + ", ".join(missing))
    if frame.empty:
        raise ValueError("V4.9.2 portfolio section is empty.")

    output = frame.copy().reset_index(drop=True)
    original = output[weight_column].to_numpy(dtype=float)
    design, exposure_names = _design_matrix(
        output, sector_column=sector_column, factor_columns=factors
    )
    coefficients, *_ = np.linalg.lstsq(design, original, rcond=None)
    neutral = original - design @ coefficients
    neutral -= neutral.mean()
    gross = float(np.abs(neutral).sum())
    if gross <= 1e-12:
        raise RuntimeError("V4.9.2 neutralization removed the entire portfolio.")
    neutral *= float(target_gross_exposure) / gross
    output["pre_neutral_weight"] = original
    output["weight"] = neutral

    before = design.T @ original
    after = design.T @ neutral
    diagnostics = {
        "position_count": int(len(output)),
        "gross_exposure": float(np.abs(neutral).sum()),
        "net_exposure": float(neutral.sum()),
        "maximum_absolute_exposure_before": float(np.abs(before).max(initial=0.0)),
        "maximum_absolute_exposure_after": float(np.abs(after).max(initial=0.0)),
        "exposure_names": exposure_names,
        "exposures_before": {
            name: float(value) for name, value in zip(exposure_names, before, strict=True)
        },
        "exposures_after": {
            name: float(value) for name, value in zip(exposure_names, after, strict=True)
        },
    }
    return output, diagnostics
