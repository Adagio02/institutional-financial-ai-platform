import json
from finai.application.services.v583_qualification_service import V583QualificationService
if __name__=="__main__":print(json.dumps(V583QualificationService().run(),indent=2,default=str))
