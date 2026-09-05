import json
from finai.application.services.v561_lock_service import V561LockService
if __name__=="__main__": print(json.dumps(V561LockService().run(),indent=2,default=str))
