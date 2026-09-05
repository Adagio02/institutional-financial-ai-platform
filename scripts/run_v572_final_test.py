import json
from finai.application.services.v572_execution_service import V572ExecutionService
if __name__=="__main__":print(json.dumps(V572ExecutionService().run(),indent=2,default=str))
