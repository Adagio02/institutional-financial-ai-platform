from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd

from finai.domain.learning.v48_storage import read_research_frame, write_research_frame
from finai.domain.portfolio.v492_neutralization import (
    V492_FACTOR_COLUMNS,
    neutralize_portfolio_section,
)


class V492NeutralizationService:
    VERSION = "4.9.2"

    def __init__(
        self,
        *,
        portfolio_path: str = "artifacts/v491/v491_ranking_portfolios",
        feature_path: str = "artifacts/v481/v481_neutral_target_panel",
        artifact_directory: str = "artifacts/v492",
    ) -> None:
        self._portfolio_path = Path(portfolio_path)
        self._feature_path = Path(feature_path)
        self._artifact_directory = Path(artifact_directory)

    def run(self) -> dict[str, Any]:
        try:
            portfolio = read_research_frame(self._portfolio_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError("Run V4.9.1 before V4.9.2.") from exc
        try:
            features = read_research_frame(self._feature_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError("V4.9.2 requires the V4.8.1 feature/target panel.") from exc

        portfolio["timestamp"] = pd.to_datetime(portfolio["timestamp"], utc=True)
        features["timestamp"] = pd.to_datetime(features["timestamp"], utc=True)
        target_columns = portfolio["target_column"].dropna().astype(str).unique()
        if len(target_columns) != 1:
            raise RuntimeError("V4.9.2 requires exactly one V4.9.1 target column.")
        target_column = str(target_columns[0])
        if target_column not in features.columns:
            raise ValueError(
                f"V4.9.2 feature panel is missing target column: {target_column}"
            )

        # Neutralizing only the selected long/short names can produce an exact
        # zero residual when those weights lie in the sector/factor span. Expand
        # to the eligible cross-section so the projection can introduce hedge
        # positions from names that V4.9.1 initially assigned zero weight.
        join_columns = [
            "timestamp", "symbol", "sector", target_column, *V492_FACTOR_COLUMNS
        ]
        active_timestamps = portfolio["timestamp"].drop_duplicates()
        source = features.loc[
            features["timestamp"].isin(active_timestamps), join_columns
        ].drop_duplicates(["timestamp", "symbol"])
        portfolio_columns = [
            "timestamp", "symbol", "weight", "prediction", "realized_return",
            "model_name", "target_column",
        ]
        selected = portfolio[portfolio_columns].drop_duplicates(
            ["timestamp", "symbol"]
        )
        merged = source.merge(selected, on=["timestamp", "symbol"], how="left")
        if merged.empty:
            raise RuntimeError("V4.9.2 could not join portfolios to factor exposures.")
        selected_rows = int(merged["weight"].notna().sum())
        merged["was_selected"] = merged["weight"].notna()
        merged["weight"] = merged["weight"].fillna(0.0)
        merged["realized_return"] = merged["realized_return"].fillna(
            merged[target_column]
        )
        merged["target_column"] = merged["target_column"].fillna(target_column)
        model_names = portfolio["model_name"].dropna().astype(str).unique()
        model_name = str(model_names[0]) if len(model_names) else "unknown"
        merged["model_name"] = merged["model_name"].fillna(model_name)

        frames: list[pd.DataFrame] = []
        diagnostics: list[dict[str, Any]] = []
        for timestamp, section in merged.groupby("timestamp", sort=True, observed=True):
            neutral, detail = neutralize_portfolio_section(section)
            frames.append(neutral)
            diagnostics.append({"timestamp": timestamp, **detail})
        output = pd.concat(frames, ignore_index=True)
        self._artifact_directory.mkdir(parents=True, exist_ok=True)
        output_path = write_research_frame(
            output, self._artifact_directory / "v492_neutral_portfolios"
        )
        payload = {
            "version": self.VERSION,
            "stage": "risk_and_factor_neutralization",
            "factor_columns": V492_FACTOR_COLUMNS,
            "portfolio_count": len(diagnostics),
            "weight_rows": int(len(output)),
            "selected_weight_rows": selected_rows,
            "expanded_weight_rows": int(len(merged)),
            "hedge_candidate_rows": int(len(merged) - selected_rows),
            "mean_maximum_exposure_before": float(mean(
                item["maximum_absolute_exposure_before"] for item in diagnostics
            )),
            "mean_maximum_exposure_after": float(mean(
                item["maximum_absolute_exposure_after"] for item in diagnostics
            )),
            "output_path": str(output_path),
            "diagnostics": diagnostics,
            "research_only": True,
            "locked_validation_opened": False,
            "champion_promoted": False,
            "next_step": "Run V4.9.3 turnover/cost-aware optimization.",
        }
        (self._artifact_directory / "v492_report.json").write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )
        return payload
