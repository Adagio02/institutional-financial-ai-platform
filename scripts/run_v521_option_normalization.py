import json
import os

from finai.application.services.v521_option_normalization_service import (
    V521OptionNormalizationService,
)


if __name__ == "__main__":
    service = V521OptionNormalizationService(
        source_path=os.getenv("FINAI_V52_OPTION_PATH", "data/research/options_chain")
    )
    print(json.dumps(service.run(), indent=2, default=str))

