import numpy as np
import pandas as pd

from finai.domain.ensemble.v54_ensemble import align_signal_families, build_expanding_ensemble, qualify_ensemble


def test_v54_alignment_expanding_weights_and_qualification():
    symbols = list("ABCDEF")
    dates = pd.date_range("2026-01-01", periods=8, tz="UTC")
    target_rows, a_rows, b_rows = [], [], []
    for t, date in enumerate(dates):
        for i, symbol in enumerate(symbols):
            target_rows.append({"timestamp": date, "symbol": symbol, "close": 100 + i * 3 + t * (i + 1) / 10})
            a_rows.append({"timestamp": date, "symbol": symbol, "alpha__a": i + t / 20})
            b_rows.append({"timestamp": date, "symbol": symbol, "alpha__b": np.sin(i + t)})
    panel, diagnostics = align_signal_families(
        {"price": pd.DataFrame(a_rows), "event": pd.DataFrame(b_rows)}, pd.DataFrame(target_rows)
    )
    assert diagnostics["periods"] == 8
    ensemble, weights = build_expanding_ensemble(panel)
    assert ensemble["alpha__ensemble"].notna().all()
    assert np.allclose(weights.filter(like="alpha__").abs().sum(axis=1), 1.0)
    result = qualify_ensemble(ensemble, weights)
    assert result["period_count"] >= 3

