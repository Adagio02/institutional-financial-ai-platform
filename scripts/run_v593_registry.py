import json
from finai.application.services.v593_registry_service import V593RegistryService
if __name__=="__main__":print(json.dumps(V593RegistryService().run(),indent=2,default=str))
