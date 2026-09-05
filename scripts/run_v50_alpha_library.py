from __future__ import annotations

import json

from finai.application.services.v50_alpha_library_factory import (
    build_v50_alpha_library_service,
)


if __name__ == "__main__":
    result = build_v50_alpha_library_service().run()
    print(json.dumps(result, indent=2, default=str))

