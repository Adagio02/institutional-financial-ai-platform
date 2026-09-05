from __future__ import annotations
import json
from pathlib import Path
from finai.domain.learning.v47_universe import load_v47_universe

def main() -> None:
    universe = load_v47_universe("config/v47_universe.json")
    payload = {
        "version":"4.7",
        "purpose":"multi-symbol ingestion execution plan",
        "symbols":universe.symbols,
        "symbol_count":len(universe.symbols),
        "interval":"1m",
        "note":(
            "Use the project's current proven market-data ingestion path for these "
            "symbols, then run the V4.7 audit. The package does not replace ingestion "
            "because an earlier project snapshot showed constructor drift in "
            "MarketDataIngestionService."
        ),
    }
    path=Path("artifacts/v47/v47_ingestion_plan.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
if __name__=="__main__":
    main()
