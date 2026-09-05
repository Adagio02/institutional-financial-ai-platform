from pathlib import Path

import joblib
import pytest
from sklearn.linear_model import LinearRegression

from finai.infrastructure.prediction.artifact_verifier import (
    calculate_file_sha256,
)
from finai.infrastructure.prediction.model_loader import (
    ModelLoader,
)


def test_model_loader_verifies_and_loads(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.joblib"

    model = LinearRegression()
    joblib.dump(model, path)

    loaded = ModelLoader().load(
        artifact_uri=str(path),
        artifact_hash=(calculate_file_sha256(path)),
    )

    assert isinstance(
        loaded,
        LinearRegression,
    )


def test_model_loader_rejects_bad_hash(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.joblib"

    joblib.dump(
        LinearRegression(),
        path,
    )

    with pytest.raises(
        ValueError,
        match="checksum",
    ):
        ModelLoader().load(
            artifact_uri=str(path),
            artifact_hash="0" * 64,
        )
