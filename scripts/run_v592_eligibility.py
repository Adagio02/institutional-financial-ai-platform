import json
from finai.application.services.v592_eligibility_service import V592EligibilityService
if __name__=="__main__":print(json.dumps(V592EligibilityService().run(),indent=2,default=str))
