from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from finai.domain.learning.v48_storage import read_research_frame, write_research_frame
from finai.domain.portfolio.v493_cost_optimization import optimize_portfolio_path
from finai.domain.portfolio.v49_construction import (
    PortfolioConstraints,
    PortfolioConstructionEngine,
)


class V493OptimizationService:
    VERSION = "4.9.3"

    def __init__(
        self,
        *,
        portfolio_path: str = "artifacts/v492/v492_neutral_portfolios",
        artifact_directory: str = "artifacts/v493",
        maximum_turnover: float = 0.20,
        one_way_cost_bps: float = 1.0,
    ) -> None:
        self._portfolio_path = Path(portfolio_path)
        self._artifact_directory = Path(artifact_directory)
        self._maximum_turnover = float(maximum_turnover)
        self._one_way_cost_bps = float(one_way_cost_bps)
        self._engine = PortfolioConstructionEngine(
            PortfolioConstraints(maximum_absolute_weight=0.20)
        )

    def run(self) -> dict[str, Any]:
        try:
            portfolio = read_research_frame(self._portfolio_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError("Run V4.9.2 before V4.9.3.") from exc
        optimized, diagnostics = optimize_portfolio_path(
            portfolio,
            engine=self._engine,
            maximum_turnover=self._maximum_turnover,
            one_way_cost_bps=self._one_way_cost_bps,
        )
        self._artifact_directory.mkdir(parents=True, exist_ok=True)
        output_path = write_research_frame(
            optimized, self._artifact_directory / "v493_optimized_portfolios"
        )
        payload = {
            "version": self.VERSION,
            "stage": "turnover_and_cost_aware_optimization",
            "maximum_turnover": self._maximum_turnover,
            "one_way_cost_bps": self._one_way_cost_bps,
            "portfolio_count": len(diagnostics),
            "weight_rows": int(len(optimized)),
            "mean_turnover": float(mean(item["turnover"] for item in diagnostics)),
            "mean_gross_return": float(mean(item["gross_return"] for item in diagnostics)),
            "mean_estimated_cost": float(mean(item["estimated_cost"] for item in diagnostics)),
            "mean_net_return": float(mean(item["net_return"] for item in diagnostics)),
            "output_path": str(output_path),
            "diagnostics": diagnostics,
            "research_only": True,
            "locked_validation_opened": False,
            "champion_promoted": False,
            "next_step": "V4.9 series complete. Proceed to V5.0 multi-strategy alpha library.",
        }
        (self._artifact_directory / "v493_report.json").write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )
        return payload
