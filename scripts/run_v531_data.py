import json
from finai.application.services.v531_data_service import V531DataService

if __name__ == "__main__":
    print(json.dumps(V531DataService().run(), indent=2, default=str))

