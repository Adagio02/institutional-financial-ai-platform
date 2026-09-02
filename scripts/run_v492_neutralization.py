import json

from finai.application.services.v492_neutralization_factory import (
    build_v492_neutralization_service,
)


result = build_v492_neutralization_service().run()
print(json.dumps(result, indent=2, default=str))
