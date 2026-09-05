import json
from finai.application.services.v553_qualification_service import V553QualificationService
if __name__ == "__main__": print(json.dumps(V553QualificationService().run(), indent=2, default=str))
