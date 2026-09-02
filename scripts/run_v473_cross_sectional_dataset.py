from __future__ import annotations
import json
from finai.core.config import get_settings
from finai.application.services.v473_learning_factory import build_v473_learning_service

def main() -> None:
    service = build_v473_learning_service(settings=get_settings())
    result = service.build_cross_sectional_dataset(horizon_bars=30)
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    main()
