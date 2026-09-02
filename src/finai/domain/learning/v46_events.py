from __future__ import annotations

import numpy as np
import pandas as pd

from finai.domain.learning.v45_features import V45_FEATURE_COLUMNS


EVENT_FAMILIES = (
    "volume_momentum_breakout",
    "relative_strength_breakout",
    "vwap_displacement_reversion",
    "trend_continuation",
    "range_expansion",
    "opening_drive",
)

META_FEATURE_COLUMNS = list(V45_FEATURE_COLUMNS) + [
    "event_direction_feature",
    "event_strength",
]


def _safe_divide(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    return numerator / denominator.replace(0.0, np.nan)


def _rolling_quantile(
    series: pd.Series,
    *,
    window: int,
    quantile: float,
) -> pd.Series:
    return (
        series.shift(1)
        .rolling(
            window=window,
            min_periods=max(30, window // 4),
        )
        .quantile(quantile)
    )


def _normalized_strength(
    value: pd.Series,
    reference: pd.Series,
) -> pd.Series:
    return _safe_divide(
        value.abs(),
        reference.abs(),
    ).clip(
        lower=0.0,
        upper=10.0,
    )


def apply_event_family(
    frame: pd.DataFrame,
    *,
    family: str,
    round_trip_cost_bps: float,
) -> pd.DataFrame:
    if family not in EVENT_FAMILIES:
        raise ValueError(
            f"Unknown V4.6 event family: {family}"
        )

    result = frame.copy()

    required = (
        "forward_return",
        "return_5",
        "return_15",
        "return_60",
        "relative_strength_15",
        "price_vs_vwap_20",
        "trend_strength",
        "ema_gap_10_30",
        "range_expansion_20",
        "body_pct",
        "relative_volume_20_60",
        "opening_session",
        "return_since_open",
    )
    for column in required:
        if column not in result.columns:
            raise ValueError(
                f"V4.6 requires column: {column}"
            )

    direction = np.zeros(
        len(result),
        dtype=int,
    )
    strength = pd.Series(
        np.zeros(len(result), dtype=float),
        index=result.index,
    )

    if family == "volume_momentum_breakout":
        signal = result["return_5"].astype(float)
        gate = _rolling_quantile(
            signal.abs(),
            window=390,
            quantile=0.80,
        )
        volume = result[
            "relative_volume_20_60"
        ].astype(float)
        mask = (
            (signal.abs() > gate)
            & (volume > 1.05)
        )
        direction[mask.to_numpy()] = (
            np.sign(signal[mask])
            .astype(int)
            .to_numpy()
        )
        strength = (
            _normalized_strength(signal, gate)
            * volume.clip(0.0, 5.0)
        )

    elif family == "relative_strength_breakout":
        signal = result[
            "relative_strength_15"
        ].astype(float)
        gate = _rolling_quantile(
            signal.abs(),
            window=390,
            quantile=0.80,
        )
        mask = signal.abs() > gate
        direction[mask.to_numpy()] = (
            np.sign(signal[mask])
            .astype(int)
            .to_numpy()
        )
        strength = _normalized_strength(
            signal,
            gate,
        )

    elif family == "vwap_displacement_reversion":
        signal = result[
            "price_vs_vwap_20"
        ].astype(float)
        gate = _rolling_quantile(
            signal.abs(),
            window=390,
            quantile=0.85,
        )
        mask = signal.abs() > gate
        direction[mask.to_numpy()] = (
            -np.sign(signal[mask])
            .astype(int)
            .to_numpy()
        )
        strength = _normalized_strength(
            signal,
            gate,
        )

    elif family == "trend_continuation":
        trend = result[
            "trend_strength"
        ].astype(float)
        gate = _rolling_quantile(
            trend,
            window=390,
            quantile=0.70,
        )
        signed_gap = result[
            "ema_gap_10_30"
        ].astype(float)
        volume = result[
            "relative_volume_20_60"
        ].astype(float)
        mask = (
            (trend > gate)
            & (signed_gap != 0.0)
            & (volume >= 0.90)
        )
        direction[mask.to_numpy()] = (
            np.sign(signed_gap[mask])
            .astype(int)
            .to_numpy()
        )
        strength = (
            _normalized_strength(trend, gate)
            * volume.clip(0.0, 5.0)
        )

    elif family == "range_expansion":
        expansion = result[
            "range_expansion_20"
        ].astype(float)
        body = result[
            "body_pct"
        ].astype(float)
        gate = _rolling_quantile(
            expansion,
            window=390,
            quantile=0.80,
        )
        mask = (
            (expansion > gate)
            & (body != 0.0)
        )
        direction[mask.to_numpy()] = (
            np.sign(body[mask])
            .astype(int)
            .to_numpy()
        )
        strength = _normalized_strength(
            expansion,
            gate,
        )

    elif family == "opening_drive":
        signal = result[
            "return_since_open"
        ].astype(float)
        opening = (
            result["opening_session"]
            .astype(float)
            > 0.5
        )
        gate = _rolling_quantile(
            signal.abs(),
            window=390,
            quantile=0.70,
        )
        volume = result[
            "relative_volume_20_60"
        ].astype(float)
        mask = (
            opening
            & (signal.abs() > gate)
            & (volume > 1.0)
        )
        direction[mask.to_numpy()] = (
            np.sign(signal[mask])
            .astype(int)
            .to_numpy()
        )
        strength = (
            _normalized_strength(signal, gate)
            * volume.clip(0.0, 5.0)
        )

    result["event_direction"] = direction
    result[
        "event_direction_feature"
    ] = direction.astype(float)
    result["event_strength"] = (
        strength.replace(
            [np.inf, -np.inf],
            np.nan,
        )
        .fillna(0.0)
        .astype(float)
    )

    cost_rate = (
        float(round_trip_cost_bps)
        / 10_000.0
    )
    result["meta_net_return"] = (
        result[
            "event_direction"
        ].astype(float)
        * result[
            "forward_return"
        ].astype(float)
        - cost_rate
    )
    result["meta_target"] = (
        result["meta_net_return"] > 0.0
    ).astype(int)
    result.loc[
        result["event_direction"] == 0,
        "meta_target",
    ] = -1

    return result
