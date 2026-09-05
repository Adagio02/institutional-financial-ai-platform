import json
from finai.application.services.v562_execution_service import V562ExecutionService
if __name__=="__main__": print(json.dumps(V562ExecutionService().run(),indent=2,default=str))
