import json

from finai.application.services.v483_ic_factory import build_v483_ic_service
from finai.core.config import get_settings


result = build_v483_ic_service(settings=get_settings()).run()
print(json.dumps(result, indent=2, default=str))
