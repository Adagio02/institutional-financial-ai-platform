from __future__ import annotations

import json

import numpy as np
import pandas as pd

from finai.application.services.v50_alpha_library_service import V50AlphaLibraryService
from finai.domain.alpha.v50_alpha_library import (
    BUILTIN_ALPHAS,
    build_alpha_signal_panel,
    qualify_alpha_library,
)
from finai.domain.learning.v48_storage import write_research_frame


def _panel() -> pd.DataFrame:
    rows = []
    for time_index, timestamp in enumerate(pd.date_range("2025-01-01", periods=6, tz="UTC")):
        for symbol_index in range(12):
            momentum = (symbol_index - 5.5) * 0.01 + time_index * 0.0001
            rows.append({
                "timestamp": timestamp,
                "symbol": f"S{symbol_index:02d}",
                "sector": f"sector-{symbol_index % 3}",
                "market_excess_return_1": -momentum * 0.1,
                "market_excess_return_15": momentum,
                "volatility_60": 0.10 + symbol_index * 0.002,
                "relative_volume_20": 1.0 + symbol_index * 0.05,
                "target_market_neutral_return": momentum * 0.2,
            })
    return pd.DataFrame(rows)


def test_registry_builds_finite_cross_sectional_signals() -> None:
    panel = _panel()
    signals = build_alpha_signal_panel(panel)
    columns = [column for column in signals if column.startswith("alpha__")]
    assert len(columns) == len(BUILTIN_ALPHAS) == 5
    assert np.isfinite(signals[columns].to_numpy()).all()
    assert signals.groupby("timestamp")[columns].mean().abs().to_numpy().max() < 1e-12
    catalog = qualify_alpha_library(signals, panel)
    assert len(catalog) == 5
    assert catalog[0]["mean_rank_ic"] != 0.0


def test_service_writes_complete_v50_catalog(tmp_path) -> None:
    source = tmp_path / "v481_neutral_target_panel"
    write_research_frame(_panel(), source)
    result = V50AlphaLibraryService(
        feature_path=str(source), artifact_directory=str(tmp_path / "v50")
    ).run()
    assert result["version"] == "5.0.3"
    assert result["alpha_count"] == 5
    assert (tmp_path / "v50" / "v50_report.json").exists()
    catalog = json.loads((tmp_path / "v50" / "v50_alpha_catalog.json").read_text())
    assert len(catalog) == 5

