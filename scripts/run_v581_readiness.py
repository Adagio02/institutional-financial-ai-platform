import json
from finai.application.services.v581_readiness_service import V581ReadinessService
if __name__=="__main__":print(json.dumps(V581ReadinessService().run(),indent=2,default=str))
