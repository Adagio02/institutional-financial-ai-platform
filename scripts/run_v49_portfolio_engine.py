import json

from finai.application.services.v49_portfolio_construction_factory import (
    build_v49_portfolio_construction_service,
)
result = build_v49_portfolio_construction_service().run()
print(json.dumps(result, indent=2, default=str))
