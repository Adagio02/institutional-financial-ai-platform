from pathlib import Path
from typing import Any

import joblib

from finai.infrastructure.prediction.artifact_verifier import (
    verify_artifact_hash,
)


class ModelLoader:
    def load(
        self,
        *,
        artifact_uri: str,
        artifact_hash: str,
    ) -> Any:
        path = Path(artifact_uri)

        if not path.exists():
            raise FileNotFoundError(f"Model artifact does not exist: {path}")

        verify_artifact_hash(
            path=path,
            expected_hash=artifact_hash,
        )

        return joblib.load(path)
