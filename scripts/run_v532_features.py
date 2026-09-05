import json
from finai.application.services.v532_feature_service import V532FeatureService

if __name__ == "__main__":
    print(json.dumps(V532FeatureService().run(), indent=2, default=str))

