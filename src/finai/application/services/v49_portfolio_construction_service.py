from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from finai.domain.portfolio.v49_construction import (
    PortfolioConstraints,
    PortfolioConstructionEngine,
)


class V49PortfolioConstructionService:
    VERSION = "4.9"

    def __init__(
        self,
        *,
        ic_report_path: str = "artifacts/v483/v483_ic_report.json",
        artifact_directory: str = "artifacts/v49",
        constraints: PortfolioConstraints | None = None,
    ) -> None:
        self._ic_report_path = Path(ic_report_path)
        self._artifact_directory = Path(artifact_directory)
        self._engine = PortfolioConstructionEngine(constraints)

    def run(self) -> dict[str, Any]:
        report = self._load_ic_report()
        smoke_input = {
            "L01": 6.0,
            "L02": 5.0,
            "L03": 4.0,
            "L04": 3.0,
            "L05": 2.0,
            "L06": 1.0,
            "S01": -6.0,
            "S02": -5.0,
            "S03": -4.0,
            "S04": -3.0,
            "S05": -2.0,
            "S06": -1.0,
        }
        smoke_result = self._engine.construct(smoke_input)
        self._artifact_directory.mkdir(parents=True, exist_ok=True)
        smoke_path = self._artifact_directory / "v49_engine_smoke_portfolio.json"
        smoke_path.write_text(
            json.dumps(asdict(smoke_result), indent=2, default=str), encoding="utf-8"
        )
        payload = {
            "version": self.VERSION,
            "stage": "portfolio_construction_engine",
            "upstream_version": report["version"],
            "upstream_ic_report": str(self._ic_report_path),
            "registered_research_signal": report["research_leader"],
            "engine_contract": {
                "input": "symbol-to-proposed-weight mapping",
                "output": "constraint-compliant target weights and exposure diagnostics",
                "constraints": smoke_result.constraints,
            },
            "smoke_portfolio_path": str(smoke_path),
            "smoke_portfolio": asdict(smoke_result),
            "portfolio_strategy_created": False,
            "risk_factor_neutralization_applied": False,
            "turnover_optimization_applied": False,
            "locked_validation_opened": False,
            "champion_promoted": False,
            "next_step": "Proceed to V4.9.1 long/short ranking portfolio.",
        }
        manifest_path = self._artifact_directory / "v49_engine_manifest.json"
        manifest_path.write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )
        return payload

    def _load_ic_report(self) -> dict[str, Any]:
        if not self._ic_report_path.exists():
            raise FileNotFoundError("Run V4.8.3 before V4.9.")
        report = json.loads(self._ic_report_path.read_text(encoding="utf-8"))
        if report.get("version") != "4.8.3":
            raise ValueError("V4.9 requires a V4.8.3 IC report.")
        if not report.get("research_leader"):
            raise ValueError("V4.8.3 IC report has no research leader.")
        return report
