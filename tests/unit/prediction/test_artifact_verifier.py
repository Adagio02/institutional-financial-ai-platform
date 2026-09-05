from pathlib import Path

import pytest

from finai.infrastructure.prediction.artifact_verifier import (
    calculate_file_sha256,
    verify_artifact_hash,
)


def test_artifact_hash_is_deterministic(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.bin"
    path.write_bytes(b"model-data")

    first = calculate_file_sha256(path)
    second = calculate_file_sha256(path)

    assert first == second
    assert len(first) == 64


def test_verify_artifact_hash_accepts_match(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.bin"
    path.write_bytes(b"model-data")

    expected = calculate_file_sha256(path)

    verify_artifact_hash(
        path=path,
        expected_hash=expected,
    )


def test_verify_artifact_hash_rejects_mismatch(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.bin"
    path.write_bytes(b"model-data")

    with pytest.raises(
        ValueError,
        match="checksum",
    ):
        verify_artifact_hash(
            path=path,
            expected_hash="0" * 64,
        )
