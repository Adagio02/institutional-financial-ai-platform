from __future__ import annotations
import json, os
from pathlib import Path
from finai.domain.learning.v48_storage import read_research_frame, write_research_frame
from finai.domain.qualification.v55_walk_forward import simulate_walk_forward


class V552SimulationService:
    VERSION = "5.5.2"
    def run(self):
        output = Path(os.getenv("FINAI_V55_ARTIFACT_DIR", "artifacts/v55"))
        panel = read_research_frame(output / "v551_ensemble_panel")
        manifest = json.loads((output / "v551_fold_manifest.json").read_text(encoding="utf-8"))
        returns, positions = simulate_walk_forward(
            panel, manifest["folds"],
            long_fraction=float(os.getenv("FINAI_V55_LONG_FRACTION", "0.20")),
            transaction_cost_bps=float(os.getenv("FINAI_V55_COST_BPS", "5.0")),
        )
        returns_path = write_research_frame(returns, output / "v552_oos_portfolio_returns")
        positions_path = write_research_frame(positions, output / "v552_oos_positions")
        report = {"version": self.VERSION, "returns_path": str(returns_path), "positions_path": str(positions_path), "rows": len(returns), "research_only": True}
        (output / "v552_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

