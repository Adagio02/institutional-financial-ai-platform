from __future__ import annotations
import pandas as pd
from finai.domain.learning.v471_panel import build_point_in_time_panel
from finai.domain.learning.v472_relationships import add_relationship_features
from finai.domain.learning.v473_cross_sectional import add_cross_sectional_targets
from finai.domain.learning.v47_universe import V47Instrument, V47Universe

def _bars(scale: float) -> pd.DataFrame:
    ts=pd.date_range("2026-01-02 14:30:00+00:00", periods=120, freq="min")
    return pd.DataFrame({
        "timestamp":ts,
        "open_price":[100+scale*i/100 for i in range(120)],
        "high_price":[101+scale*i/100 for i in range(120)],
        "low_price":[99+scale*i/100 for i in range(120)],
        "close_price":[100+scale*i/100 for i in range(120)],
        "volume":[1000+i for i in range(120)],
    })

def test_panel_relationships_and_targets() -> None:
    u=V47Universe(
        instruments=(
            V47Instrument("AAA","AAA","equity","US","Technology","XLK"),
            V47Instrument("SPY","SPY","equity","US","ETF","SPY"),
            V47Instrument("QQQ","QQQ","equity","US","ETF","SPY"),
            V47Instrument("XLK","XLK","equity","US","ETF","SPY"),
        ),
        benchmarks=("SPY","QQQ"), sector_etfs={"Technology":"XLK"}
    )
    panel=build_point_in_time_panel({"AAA":_bars(1.2),"SPY":_bars(0.7),"QQQ":_bars(0.9),"XLK":_bars(1.0)})
    rel=add_relationship_features(panel,u)
    ds=add_cross_sectional_targets(rel,horizon_bars=5)
    assert {"sector","benchmark","benchmark_excess_return_1","future_benchmark_excess_return",
            "target_cross_sectional_rank"}.issubset(ds.columns)
    assert len(ds)>0
