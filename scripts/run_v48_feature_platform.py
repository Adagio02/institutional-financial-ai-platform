import json

from finai.application.services.v48_feature_factory import build_v48_feature_service
from finai.core.config import get_settings


result = build_v48_feature_service(settings=get_settings()).run()
print(json.dumps(result, indent=2, default=str))
