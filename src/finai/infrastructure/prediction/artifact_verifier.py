import hashlib
from pathlib import Path


def calculate_file_sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file_handle:
        for chunk in iter(
            lambda: file_handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def verify_artifact_hash(
    *,
    path: Path,
    expected_hash: str,
) -> None:
    actual_hash = calculate_file_sha256(path)

    if actual_hash != expected_hash:
        raise ValueError("Model artifact checksum verification failed.")
