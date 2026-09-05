from __future__ import annotations

import pandas as pd

from finai.application.services.v512_signal_service import V512SignalService
from finai.application.services.v513_qualification_service import V513QualificationService
from finai.domain.learning.v48_storage import write_research_frame


def _normalized_quotes() -> pd.DataFrame:
    rows = []
    for time_index, timestamp in enumerate(
        pd.date_range("2025-01-01 14:30", periods=6, freq="min", tz="UTC")
    ):
        for symbol_index in range(8):
            midpoint = 100 + symbol_index + time_index * (symbol_index - 3.5) * 0.01
            rows.append({
                "timestamp": timestamp,
                "symbol": f"S{symbol_index}",
                "bid_price": midpoint - 0.01,
                "ask_price": midpoint + 0.01,
                "bid_size": 100 + 10 * symbol_index,
                "ask_size": 170 - 8 * symbol_index,
            })
    return pd.DataFrame(rows)


def test_v512_and_v513_run_independently(tmp_path) -> None:
    artifact_directory = tmp_path / "v51"
    normalized_path = artifact_directory / "v511_normalized_quotes"
    write_research_frame(_normalized_quotes(), normalized_path)
    second = V512SignalService(
        normalized_path=str(normalized_path),
        artifact_directory=str(artifact_directory),
    ).run()
    third = V513QualificationService(
        signal_path=str(artifact_directory / "v512_microstructure_signals"),
        artifact_directory=str(artifact_directory),
    ).run()
    assert second["version"] == "5.1.2"
    assert second["signal_columns"]
    assert third["version"] == "5.1.3"
    assert third["signal_count"] == 4
    assert (artifact_directory / "v513_report.json").exists()

