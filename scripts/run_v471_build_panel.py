from __future__ import annotations
import json
from finai.core.config import get_settings
from finai.application.services.v471_learning_factory import build_v471_learning_service

def main() -> None:
    service = build_v471_learning_service(settings=get_settings())
    result = service.build_panel(interval="1m", minimum_rows_per_symbol=500)
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    main()
