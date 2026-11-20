"""Unit tests for the vol_target research engine (H7), on synthetic prices only."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from research_kit import strategies as S

HYPOTHESES = Path(__file__).resolve().parents[2] / "research_kit" / "hypotheses"
SPEC_PATH = HYPOTHESES / "H7_spy_volatility_target.json"


def _spec(**rule) -> dict:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    spec["rule"].update(rule)
    return spec


def _closes(daily_vol: list[float], seed: int = 0) -> pd.DataFrame:
    """SPY with a chosen daily volatility per day; BIL flat."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=len(daily_vol), tz="UTC")
    spy = 100 * np.cumprod(1 + rng.standard_normal(len(daily_vol)) * np.asarray(daily_vol))
    return pd.DataFrame({"BIL": 100.0, "SPY": spy}, index=dates)


@pytest.fixture
def use_closes(monkeypatch):
    def install(closes: pd.DataFrame) -> None:
        monkeypatch.setattr(S, "load_etf_closes", lambda symbols: closes[sorted(symbols)])
    return install


def test_h7_spec_is_registrable_and_wired():
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    from research_kit.registry import REQUIRED
    assert not [k for k in REQUIRED if k not in spec]
    assert spec["strategy_type"] in S.ENGINES
    assert spec["strategy_type"] in S.ETF_KINDS
    assert spec["forward"]["benchmark"] == spec["asset"]


def test_calm_market_is_fully_invested(use_closes):
    use_closes(_closes([0.002] * 300))  # about 3% annualized, far below the 15% target
    result = S.vol_target(_spec(), cost_bps=0.0)
    assert result["stats"]["minimum_exposure"] == pytest.approx(1.0)
    assert result["holdings"].get("SPY") == pytest.approx(1.0, abs=1e-6)


def test_weight_is_target_over_realized_vol(use_closes):
    closes = _closes([0.005] * 150 + [0.03] * 150, seed=3)  # calm, then about 48% annualized
    use_closes(closes)
    result = S.vol_target(_spec(), cost_bps=0.0)
    returns = closes.SPY.pct_change()
    expected = []
    for decided in S.month_ends(closes.index):
        i = closes.index.get_loc(decided)
        if i >= 21:
            realized = returns.iloc[i - 20:i + 1].std(ddof=1) * np.sqrt(252)
            expected.append(min(1.0, 0.15 / realized))
    assert result["stats"]["rebalances"] == len(expected)
    assert result["stats"]["average_exposure"] == pytest.approx(np.mean(expected))
    assert result["stats"]["minimum_exposure"] == pytest.approx(min(expected))
    assert min(expected) < 0.4 and max(expected) == pytest.approx(1.0)


def test_no_lookahead_future_prices_do_not_change_past_returns(use_closes):
    base = _closes([0.01] * 260 + [0.01] * 40, seed=1)
    shocked = base.copy()
    spy = shocked.columns.get_loc("SPY")
    shocked.iloc[260:, spy] *= np.linspace(1.0, 0.3, 40)  # crash after day 260
    use_closes(base)
    a = S.vol_target(_spec(), cost_bps=5.0)["ledger"].net
    use_closes(shocked)
    b = S.vol_target(_spec(), cost_bps=5.0)["ledger"].net
    cutoff = base.index[260]
    pd.testing.assert_series_equal(a[a.index < cutoff], b[b.index < cutoff])


def test_costs_reduce_returns_and_benchmark_is_buy_and_hold(use_closes):
    use_closes(_closes([0.005] * 150 + [0.03] * 150, seed=2))
    cheap = S.vol_target(_spec(), cost_bps=0.0)
    costly = S.vol_target(_spec(), cost_bps=50.0)
    assert costly["ledger"].net.sum() < cheap["ledger"].net.sum()
    assert set(cheap["benchmarks"]) == {"SPY"}


def test_gates_compare_against_spy():
    spec = _spec()
    result = {"metrics": {"months": 100, "total_return": 0.5, "sharpe": 0.8, "max_drawdown": -0.20},
              "benchmarks": {"SPY": {"sharpe": 0.7, "max_drawdown": -0.34}},
              "cost_sensitivity": {"20": {"total_return": 0.4}}}
    checks = S.gates(spec, result)
    assert checks["sharpe_at_least_SPY"] and checks["drawdown_improves_on_SPY"]
    # Only 3 points better than SPY: below the 5-point gate.
    result["metrics"]["max_drawdown"] = -0.31
    assert not S.gates(spec, result)["drawdown_improves_on_SPY"]
