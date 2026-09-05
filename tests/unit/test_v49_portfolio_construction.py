from __future__ import annotations

import json

import numpy as np
import pytest

from finai.application.services.v49_portfolio_construction_service import (
    V49PortfolioConstructionService,
)
from finai.domain.portfolio.v49_construction import (
    PortfolioConstraints,
    PortfolioConstructionEngine,
)


def _proposal() -> dict[str, float]:
    return {
        **{f"L{index}": float(7 - index) for index in range(1, 7)},
        **{f"S{index}": float(index - 7) for index in range(1, 7)},
    }


def test_engine_satisfies_gross_net_and_cap() -> None:
    engine = PortfolioConstructionEngine(
        PortfolioConstraints(maximum_absolute_weight=0.10)
    )
    result = engine.construct(_proposal())
    assert np.isclose(result.gross_exposure, 1.0)
    assert np.isclose(result.net_exposure, 0.0)
    assert result.maximum_absolute_weight <= 0.10 + 1e-12
    assert result.position_count == 12


def test_engine_reports_turnover_without_optimizing_it() -> None:
    result = PortfolioConstructionEngine().construct(
        _proposal(), current_weights={"L1": 0.05, "S1": -0.05}
    )
    assert result.turnover_from_current is not None
    assert result.turnover_from_current > 0.0


def test_engine_rejects_infeasible_cap() -> None:
    engine = PortfolioConstructionEngine(
        PortfolioConstraints(maximum_absolute_weight=0.05)
    )
    with pytest.raises(ValueError, match="infeasible"):
        engine.construct(_proposal())


def test_service_requires_v483_and_writes_manifest(tmp_path) -> None:
    report_path = tmp_path / "v483_ic_report.json"
    report_path.write_text(
        json.dumps({
            "version": "4.8.3",
            "research_leader": {
                "model_name": "v482_ridge_ranker",
                "target_column": "target_market_neutral_return",
                "mean_rank_ic": 0.03,
            },
        }),
        encoding="utf-8",
    )
    service = V49PortfolioConstructionService(
        ic_report_path=str(report_path),
        artifact_directory=str(tmp_path / "v49"),
    )
    result = service.run()
    assert result["version"] == "4.9"
    assert result["portfolio_strategy_created"] is False
    assert result["next_step"].startswith("Proceed to V4.9.1")
    assert (tmp_path / "v49" / "v49_engine_manifest.json").exists()
