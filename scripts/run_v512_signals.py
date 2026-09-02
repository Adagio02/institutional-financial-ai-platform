import json

from finai.application.services.v512_signal_service import V512SignalService


if __name__ == "__main__":
    print(json.dumps(V512SignalService().run(), indent=2, default=str))

