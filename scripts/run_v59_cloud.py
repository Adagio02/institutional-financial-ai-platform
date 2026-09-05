import json
from finai.application.services.v591_chain_service import V591ChainService
from finai.application.services.v592_eligibility_service import V592EligibilityService
from finai.application.services.v593_registry_service import V593RegistryService
if __name__=="__main__":print(json.dumps({"v591":V591ChainService().run(),"v592":V592EligibilityService().run(),"v593":V593RegistryService().run()},indent=2,default=str))
