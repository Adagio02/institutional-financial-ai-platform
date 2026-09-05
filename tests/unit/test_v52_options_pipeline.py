from __future__ import annotations

import json

import numpy as np
import pandas as pd

from finai.application.services.v521_option_normalization_service import (
    V521OptionNormalizationService,
)
from finai.application.services.v522_surface_service import V522SurfaceService
from finai.application.services.v523_options_signal_service import V523OptionsSignalService
from finai.domain.options.v52_volatility import (
    SIGNAL_COLUMNS,
    build_options_signals,
    build_volatility_surface,
    normalize_option_chain,
)


def _option_chain() -> pd.DataFrame:
    rows = []
    times = pd.date_range("2025-01-02 15:00", periods=6, freq="D", tz="UTC")
    for time_index, timestamp in enumerate(times):
        for symbol_index in range(7):
            symbol = f"S{symbol_index}"
            spot = 100 + 5 * symbol_index + time_index * (symbol_index - 3) * 0.1
            for days in (30, 90):
                expiration = timestamp + pd.Timedelta(days=days)
                for option_type, delta in (("C", 0.25), ("P", -0.25)):
                    for multiplier in (0.95, 1.0, 1.05):
                        iv = 0.18 + 0.01 * symbol_index + 0.0002 * days
                        if option_type == "P":
                            iv += 0.02
                        rows.append({
                            "timestamp": timestamp,
                            "underlying_symbol": symbol,
                            "expiration": expiration,
                            "strike": spot * multiplier,
                            "option_type": option_type,
                            "bid_price": 1.00,
                            "ask_price": 1.10,
                            "implied_volatility": iv,
                            "delta": delta,
                            "gamma": 0.02 + 0.001 * symbol_index,
                            "open_interest": 100 + 10 * symbol_index,
                            "volume": 20 + symbol_index + (5 if option_type == "P" else 0),
                            "underlying_price": spot,
                        })
    return pd.DataFrame(rows)


def test_domain_options_surface_and_signals() -> None:
    normalized, quality = normalize_option_chain(_option_chain())
    assert quality["rejected_rows"] == 0
    surface = build_volatility_surface(normalized)
    signals = build_options_signals(surface)
    assert len(surface) == 42
    assert np.isfinite(signals[SIGNAL_COLUMNS].to_numpy()).all()
    assert signals.groupby("timestamp")[SIGNAL_COLUMNS].mean().abs().to_numpy().max() < 1e-12


def test_v52_services_write_all_artifacts(tmp_path) -> None:
    source = tmp_path / "options.csv"
    _option_chain().to_csv(source, index=False)
    artifact_directory = tmp_path / "v52"
    first = V521OptionNormalizationService(
        source_path=str(source), artifact_directory=str(artifact_directory)
    ).run()
    second = V522SurfaceService(
        source_path=str(artifact_directory / "v521_normalized_option_chain"),
        artifact_directory=str(artifact_directory),
    ).run()
    third = V523OptionsSignalService(
        source_path=str(artifact_directory / "v522_volatility_surface"),
        artifact_directory=str(artifact_directory),
    ).run()
    assert [first["version"], second["version"], third["version"]] == [
        "5.2.1", "5.2.2", "5.2.3",
    ]
    assert third["signal_count"] == 5
    report = json.loads((artifact_directory / "v523_report.json").read_text())
    assert report["next_step"].endswith("V5.3.")

