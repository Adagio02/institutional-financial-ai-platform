import json
from finai.application.services.v573_decision_service import V573DecisionService
if __name__=="__main__":print(json.dumps(V573DecisionService().run(),indent=2,default=str))
