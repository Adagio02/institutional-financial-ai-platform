from __future__ import annotations

import json

import numpy as np
import pandas as pd

from finai.application.services.v491_portfolio_service import V491PortfolioService
from finai.application.services.v492_neutralization_service import (
    V492NeutralizationService,
)
from finai.application.services.v493_optimization_service import V493OptimizationService
from finai.domain.learning.v48_storage import write_research_frame
from finai.domain.portfolio.v491_ranking import build_long_short_ranking_portfolios
from finai.domain.portfolio.v492_neutralization import neutralize_portfolio_section
from finai.domain.portfolio.v493_cost_optimization import optimize_portfolio_path
from finai.domain.portfolio.v49_construction import (
    PortfolioConstraints,
    PortfolioConstructionEngine,
)


def _research_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    prediction_rows = []
    feature_rows = []
    for time_index, timestamp in enumerate(
        pd.date_range("2025-01-01", periods=8, freq="D", tz="UTC")
    ):
        for symbol_index in range(20):
            symbol = f"S{symbol_index:02d}"
            score = float(symbol_index - 9.5 + 0.1 * time_index)
            realized = score * 0.001
            prediction_rows.append({
                "timestamp": timestamp,
                "symbol": symbol,
                "sector": f"sector-{symbol_index % 4}",
                "model_name": "leader",
                "target_column": "target_market_neutral_return",
                "prediction": score,
                "target_market_neutral_return": realized,
            })
            feature_rows.append({
                "timestamp": timestamp,
                "symbol": symbol,
                "sector": f"sector-{symbol_index % 4}",
                "market_excess_return_60": np.sin(symbol_index),
                "volatility_60": 0.1 + symbol_index * 0.001,
                "cross_sectional_rank_volume": symbol_index / 20.0,
                "target_market_neutral_return": realized,
            })
    return pd.DataFrame(prediction_rows), pd.DataFrame(feature_rows)


def test_domain_pipeline_constraints_and_costs() -> None:
    predictions, features = _research_frames()
    engine = PortfolioConstructionEngine(
        PortfolioConstraints(maximum_absolute_weight=0.10)
    )
    ranked, rank_diagnostics = build_long_short_ranking_portfolios(
        predictions,
        model_name="leader",
        target_column="target_market_neutral_return",
        engine=engine,
    )
    assert len(rank_diagnostics) == 8
    assert np.allclose(
        ranked.groupby("timestamp")["weight"].sum().to_numpy(), 0.0
    )

    merged = ranked.merge(features, on=["timestamp", "symbol"], how="inner")
    neutral_frames = []
    exposure_after = []
    for _, section in merged.groupby("timestamp"):
        neutral, diagnostics = neutralize_portfolio_section(section)
        neutral_frames.append(neutral)
        exposure_after.append(diagnostics["maximum_absolute_exposure_after"])
    neutral = pd.concat(neutral_frames, ignore_index=True)
    assert max(exposure_after) < 1e-8

    optimized, cost_diagnostics = optimize_portfolio_path(
        neutral,
        engine=PortfolioConstructionEngine(
            PortfolioConstraints(maximum_absolute_weight=0.20)
        ),
        maximum_turnover=0.20,
        one_way_cost_bps=1.0,
    )
    assert not optimized.empty
    assert all(item["turnover"] <= 0.20 + 1e-8 for item in cost_diagnostics[1:])
    assert all(item["estimated_cost"] >= 0.0 for item in cost_diagnostics)


def test_service_pipeline_writes_final_report(tmp_path) -> None:
    predictions, features = _research_frames()
    prediction_base = tmp_path / "v482_oos_predictions"
    feature_base = tmp_path / "v481_neutral_target_panel"
    write_research_frame(predictions, prediction_base)
    write_research_frame(features, feature_base)
    ic_report = tmp_path / "v483_ic_report.json"
    ic_report.write_text(json.dumps({
        "version": "4.8.3",
        "research_leader": {
            "model_name": "leader",
            "target_column": "target_market_neutral_return",
        },
    }), encoding="utf-8")

    first = V491PortfolioService(
        prediction_path=str(prediction_base),
        ic_report_path=str(ic_report),
        artifact_directory=str(tmp_path / "v491"),
    ).run()
    second = V492NeutralizationService(
        portfolio_path=str(tmp_path / "v491" / "v491_ranking_portfolios"),
        feature_path=str(feature_base),
        artifact_directory=str(tmp_path / "v492"),
    ).run()
    third = V493OptimizationService(
        portfolio_path=str(tmp_path / "v492" / "v492_neutral_portfolios"),
        artifact_directory=str(tmp_path / "v493"),
    ).run()
    assert [first["version"], second["version"], third["version"]] == [
        "4.9.1",
        "4.9.2",
        "4.9.3",
    ]
    assert second["expanded_weight_rows"] > second["selected_weight_rows"]
    assert third["next_step"].startswith("V4.9 series complete")
    assert (tmp_path / "v493" / "v493_report.json").exists()


def test_full_cross_section_prevents_exact_neutralization_collapse() -> None:
    selected = pd.DataFrame({
        "symbol": ["A", "B", "C", "D"],
        "sector": ["s1", "s2", "s3", "s4"],
        "weight": [0.25, 0.25, -0.25, -0.25],
        "market_excess_return_60": 0.0,
        "volatility_60": 0.1,
        "cross_sectional_rank_volume": 0.5,
    })
    try:
        neutralize_portfolio_section(selected)
    except RuntimeError as exc:
        assert "removed the entire portfolio" in str(exc)
    else:
        raise AssertionError("Selected-only regression fixture should collapse.")

    hedge_candidates = selected.copy()
    hedge_candidates["symbol"] = ["E", "F", "G", "H"]
    hedge_candidates["weight"] = 0.0
    expanded = pd.concat([selected, hedge_candidates], ignore_index=True)
    neutral, diagnostics = neutralize_portfolio_section(expanded)
    assert np.isclose(neutral["weight"].abs().sum(), 1.0)
    assert diagnostics["maximum_absolute_exposure_after"] < 1e-8
