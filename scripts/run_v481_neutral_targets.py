import json

from finai.application.services.v481_target_factory import build_v481_target_service
from finai.core.config import get_settings


result = build_v481_target_service(settings=get_settings()).run()
print(json.dumps(result, indent=2, default=str))
