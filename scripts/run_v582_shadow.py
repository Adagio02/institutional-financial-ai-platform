import json
from finai.application.services.v582_shadow_service import V582ShadowService
if __name__=="__main__":print(json.dumps(V582ShadowService().run(),indent=2,default=str))
