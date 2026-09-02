import json

from finai.application.services.v491_portfolio_factory import build_v491_portfolio_service


result = build_v491_portfolio_service().run()
print(json.dumps(result, indent=2, default=str))
