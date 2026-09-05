import json
from finai.application.services.v591_chain_service import V591ChainService
if __name__=="__main__":print(json.dumps(V591ChainService().run(),indent=2,default=str))
