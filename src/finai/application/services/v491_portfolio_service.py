from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from finai.domain.learning.v48_storage import read_research_frame, write_research_frame
from finai.domain.portfolio.v491_ranking import build_long_short_ranking_portfolios
from finai.domain.portfolio.v49_construction import (
    PortfolioConstraints,
    PortfolioConstructionEngine,
)


class V491PortfolioService:
    VERSION = "4.9.1"

    def __init__(
        self,
        *,
        prediction_path: str = "artifacts/v482/v482_oos_predictions",
        ic_report_path: str = "artifacts/v483/v483_ic_report.json",
        artifact_directory: str = "artifacts/v491",
        quantile_fraction: float = 0.20,
    ) -> None:
        self._prediction_path = Path(prediction_path)
        self._ic_report_path = Path(ic_report_path)
        self._artifact_directory = Path(artifact_directory)
        self._quantile_fraction = float(quantile_fraction)
        self._engine = PortfolioConstructionEngine(
            PortfolioConstraints(maximum_absolute_weight=0.10)
        )

    def run(self) -> dict[str, Any]:
        try:
            predictions = read_research_frame(self._prediction_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError("Run V4.8.2 before V4.9.1.") from exc
        if not self._ic_report_path.exists():
            raise FileNotFoundError("Run V4.8.3 before V4.9.1.")
        ic_report = json.loads(self._ic_report_path.read_text(encoding="utf-8"))
        leader = ic_report.get("research_leader")
        if ic_report.get("version") != "4.8.3" or not leader:
            raise ValueError("V4.9.1 requires a valid V4.8.3 research leader.")

        weights, diagnostics = build_long_short_ranking_portfolios(
            predictions,
            model_name=str(leader["model_name"]),
            target_column=str(leader["target_column"]),
            engine=self._engine,
            quantile_fraction=self._quantile_fraction,
        )
        self._artifact_directory.mkdir(parents=True, exist_ok=True)
        output_path = write_research_frame(
            weights, self._artifact_directory / "v491_ranking_portfolios"
        )
        returns = [float(item["portfolio_return"]) for item in diagnostics]
        payload = {
            "version": self.VERSION,
            "stage": "long_short_ranking_portfolio",
            "model_name": leader["model_name"],
            "target_column": leader["target_column"],
            "quantile_fraction": self._quantile_fraction,
            "portfolio_count": len(diagnostics),
            "weight_rows": int(len(weights)),
            "mean_portfolio_return": float(mean(returns)),
            "positive_portfolio_fraction": float(
                sum(value > 0.0 for value in returns) / len(returns)
            ),
            "output_path": str(output_path),
            "diagnostics": diagnostics,
            "research_only": True,
            "locked_validation_opened": False,
            "champion_promoted": False,
            "next_step": "Run V4.9.2 risk/factor neutralization.",
        }
        (self._artifact_directory / "v491_report.json").write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )
        return payload
