import json
from finai.application.services.v533_signal_service import V533SignalService

if __name__ == "__main__":
    print(json.dumps(V533SignalService().run(), indent=2, default=str))

