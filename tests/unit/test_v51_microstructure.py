from __future__ import annotations

import json

import numpy as np
import pandas as pd

from finai.application.services.v51_microstructure_service import V51MicrostructureService
from finai.domain.microstructure.v51_quotes import (
    SIGNAL_COLUMNS,
    build_microstructure_signals,
    normalize_quotes,
    qualify_microstructure_signals,
)
from finai.domain.learning.v48_storage import write_research_frame


def _quotes() -> pd.DataFrame:
    rows = []
    for time_index, timestamp in enumerate(
        pd.date_range("2025-01-01 14:30", periods=6, freq="min", tz="UTC")
    ):
        for symbol_index in range(10):
            midpoint = 100.0 + symbol_index + 0.01 * time_index * (symbol_index - 4.5)
            spread = 0.02 + symbol_index * 0.001
            rows.append({
                "timestamp": timestamp,
                "symbol": f"s{symbol_index:02d}",
                "bid_price": midpoint - spread / 2.0,
                "ask_price": midpoint + spread / 2.0,
                "bid_size": 100 + symbol_index * 10 + time_index,
                "ask_size": 180 - symbol_index * 8 + time_index,
            })
    rows.append({
        "timestamp": None, "symbol": "BAD", "bid_price": -1,
        "ask_price": 0, "bid_size": 0, "ask_size": 0,
    })
    return pd.DataFrame(rows)


def test_quote_normalization_signals_and_qualification() -> None:
    normalized, quality = normalize_quotes(_quotes())
    assert quality == {"input_rows": 61, "accepted_rows": 60, "rejected_rows": 1}
    assert normalized["symbol"].str.match(r"S\d{2}").all()
    signals = build_microstructure_signals(normalized)
    assert np.isfinite(signals[SIGNAL_COLUMNS].to_numpy()).all()
    assert signals.groupby("timestamp")[SIGNAL_COLUMNS].mean().abs().to_numpy().max() < 1e-12
    qualification = qualify_microstructure_signals(signals)
    assert len(qualification) == 4
    assert all(item["period_count"] >= 3 for item in qualification)


def test_v51_service_writes_all_stage_artifacts(tmp_path) -> None:
    source = tmp_path / "quotes"
    write_research_frame(_quotes(), source)
    result = V51MicrostructureService(
        quote_path=str(source), artifact_directory=str(tmp_path / "v51")
    ).run()
    assert result["version"] == "5.1.3"
    assert result["signal_count"] == 4
    assert (tmp_path / "v51" / "v51_report.json").exists()
    qualification = json.loads(
        (tmp_path / "v51" / "v513_signal_qualification.json").read_text()
    )
    assert len(qualification) == 4

