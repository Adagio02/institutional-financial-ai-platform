import json
from finai.application.services.v563_decision_service import V563DecisionService
if __name__=="__main__": print(json.dumps(V563DecisionService().run(),indent=2,default=str))
