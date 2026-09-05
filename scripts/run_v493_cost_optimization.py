import json

from finai.application.services.v493_optimization_factory import (
    build_v493_optimization_service,
)


result = build_v493_optimization_service().run()
print(json.dumps(result, indent=2, default=str))
