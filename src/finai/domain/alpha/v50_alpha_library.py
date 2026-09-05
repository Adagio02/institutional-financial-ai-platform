from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AlphaDefinition:
    name: str
    family: str
    description: str
    required_columns: tuple[str, ...]
    builder: Callable[[pd.DataFrame], pd.Series]

    def metadata(self) -> dict[str, object]:
        result = asdict(self)
        result.pop("builder")
        return result


def _number(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan)


def _rank(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    ranked = values.groupby(frame["timestamp"]).rank(pct=True, method="average")
    return ranked - ranked.groupby(frame["timestamp"]).transform("mean")


def _momentum(frame: pd.DataFrame) -> pd.Series:
    return _rank(frame, _number(frame, "market_excess_return_15"))


def _short_term_reversal(frame: pd.DataFrame) -> pd.Series:
    return -_rank(frame, _number(frame, "market_excess_return_1"))


def _defensive(frame: pd.DataFrame) -> pd.Series:
    return -_rank(frame, _number(frame, "volatility_60"))


def _liquidity(frame: pd.DataFrame) -> pd.Series:
    return _rank(frame, _number(frame, "relative_volume_20"))


def _momentum_quality(frame: pd.DataFrame) -> pd.Series:
    momentum = _rank(frame, _number(frame, "market_excess_return_15"))
    defensive = -_rank(frame, _number(frame, "volatility_60"))
    liquidity = _rank(frame, _number(frame, "relative_volume_20"))
    return 0.50 * momentum + 0.30 * defensive + 0.20 * liquidity


BUILTIN_ALPHAS: tuple[AlphaDefinition, ...] = (
    AlphaDefinition(
        "medium_term_momentum", "price", "15-period market-relative momentum",
        ("market_excess_return_15",), _momentum,
    ),
    AlphaDefinition(
        "short_term_reversal", "price", "One-period market-relative mean reversion",
        ("market_excess_return_1",), _short_term_reversal,
    ),
    AlphaDefinition(
        "low_volatility", "risk", "Preference for lower 60-period realized volatility",
        ("volatility_60",), _defensive,
    ),
    AlphaDefinition(
        "relative_volume", "liquidity", "Cross-sectional relative-volume strength",
        ("relative_volume_20",), _liquidity,
    ),
    AlphaDefinition(
        "momentum_quality", "composite",
        "Momentum combined with defensive and liquidity quality",
        ("market_excess_return_15", "volatility_60", "relative_volume_20"),
        _momentum_quality,
    ),
)


def build_alpha_signal_panel(
    frame: pd.DataFrame,
    definitions: tuple[AlphaDefinition, ...] = BUILTIN_ALPHAS,
) -> pd.DataFrame:
    required = {"timestamp", "symbol", "sector"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError("V5.0 alpha source missing: " + ", ".join(missing))
    output = frame[["timestamp", "symbol", "sector"]].copy()
    for definition in definitions:
        absent = sorted(set(definition.required_columns).difference(frame.columns))
        if absent:
            raise ValueError(f"Alpha {definition.name} missing: " + ", ".join(absent))
        signal = definition.builder(frame).astype(float)
        output[f"alpha__{definition.name}"] = signal.groupby(frame["timestamp"]).transform(
            lambda values: values.fillna(values.median()).fillna(0.0)
        )
    return output.sort_values(["timestamp", "symbol"]).reset_index(drop=True)


def qualify_alpha_library(
    signal_panel: pd.DataFrame,
    target_frame: pd.DataFrame,
    *,
    target_column: str = "target_market_neutral_return",
) -> list[dict[str, object]]:
    if target_column not in target_frame.columns:
        raise ValueError(f"V5.0 target missing: {target_column}")
    joined = signal_panel.merge(
        target_frame[["timestamp", "symbol", target_column]],
        on=["timestamp", "symbol"],
        how="inner",
    )
    results: list[dict[str, object]] = []
    for definition in BUILTIN_ALPHAS:
        column = f"alpha__{definition.name}"
        daily_ic = joined.groupby("timestamp", observed=True).apply(
            lambda section: section[column].corr(section[target_column], method="spearman"),
            include_groups=False,
        ).dropna()
        ranks = joined.pivot(index="timestamp", columns="symbol", values=column).sort_index()
        turnover = ranks.diff().abs().mean(axis=1).dropna()
        mean_ic = float(daily_ic.mean()) if len(daily_ic) else 0.0
        std_ic = float(daily_ic.std(ddof=0)) if len(daily_ic) else 0.0
        results.append({
            **definition.metadata(),
            "signal_column": column,
            "observation_count": int(joined[column].notna().sum()),
            "period_count": int(len(daily_ic)),
            "mean_rank_ic": mean_ic,
            "rank_ic_information_ratio": float(mean_ic / std_ic) if std_ic > 0 else 0.0,
            "positive_rank_ic_fraction": float((daily_ic > 0).mean()) if len(daily_ic) else 0.0,
            "mean_signal_turnover": float(turnover.mean()) if len(turnover) else 0.0,
            "eligible_for_v51_research": bool(len(daily_ic) >= 3 and np.isfinite(mean_ic)),
        })
    return sorted(results, key=lambda item: abs(float(item["mean_rank_ic"])), reverse=True)
