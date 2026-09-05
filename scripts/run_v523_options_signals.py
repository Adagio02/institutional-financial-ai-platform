import json

from finai.application.services.v523_options_signal_service import V523OptionsSignalService


if __name__ == "__main__":
    print(json.dumps(V523OptionsSignalService().run(), indent=2, default=str))

