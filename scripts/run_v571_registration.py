import json
from finai.application.services.v571_registration_service import V571RegistrationService
if __name__=="__main__":print(json.dumps(V571RegistrationService().run(),indent=2,default=str))
