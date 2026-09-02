import json

from finai.application.services.v513_qualification_service import V513QualificationService


if __name__ == "__main__":
    print(json.dumps(V513QualificationService().run(), indent=2, default=str))

