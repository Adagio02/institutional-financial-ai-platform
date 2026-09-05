from __future__ import annotations
import json
from finai.core.config import get_settings
from finai.application.services.v472_learning_factory import build_v472_learning_service

def main() -> None:
    service = build_v472_learning_service(settings=get_settings())
    result = service.build_relationship_panel()
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    main()
