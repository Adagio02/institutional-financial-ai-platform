import json
from finai.application.services.v581_readiness_service import V581ReadinessService
from finai.application.services.v582_shadow_service import V582ShadowService
from finai.application.services.v583_qualification_service import V583QualificationService
if __name__=="__main__":
    result={"v581":V581ReadinessService().run(),"v582":V582ShadowService().run(),"v583":V583QualificationService().run()}
    print(json.dumps(result,indent=2,default=str))
