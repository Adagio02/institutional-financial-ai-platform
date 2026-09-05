from __future__ import annotations

import json

from finai.application.services.v51_microstructure_factory import (
    build_v51_microstructure_service,
)


if __name__ == "__main__":
    print(json.dumps(build_v51_microstructure_service().run(), indent=2, default=str))

