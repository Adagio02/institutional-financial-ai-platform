import json
from finai.application.services.v543_qualification_service import V543QualificationService

if __name__ == "__main__":
    print(json.dumps(V543QualificationService().run(), indent=2, default=str))

