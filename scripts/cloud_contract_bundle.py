from __future__ import annotations

import argparse
import hashlib
import hmac
import io
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


CONTRACTS = {
    "v53": "v533_champion_contract.json",
    "v54": "v543_champion_contract.json",
    "v55": "v553_champion_contract.json",
    "v56": "v563_champion_contract.json",
    "v57": "v573_champion_contract.json",
    "v58": "v583_champion_contract.json",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def signing_key() -> bytes:
    value = os.environ.get("FINAI_CONTRACT_SIGNING_KEY", "")
    if len(value) < 32:
        raise RuntimeError("FINAI_CONTRACT_SIGNING_KEY must contain at least 32 characters.")
    return value.encode("utf-8")


def locate_contract(root: Path, stage: str, name: str) -> Path:
    override = os.environ.get(f"FINAI_{stage.upper()}_CONTRACT")
    candidates = [Path(override)] if override else [root / stage / name, root / f"{stage}-real-candidate-001" / name]
    matches = [path for path in candidates if path.is_file()]
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected exactly one real {stage} contract; found {len(matches)} among: {candidates}")
    return matches[0]


def create_bundle(contract_root: Path, output_zip: Path) -> dict:
    files: dict[str, bytes] = {}
    for stage, name in CONTRACTS.items():
        source = locate_contract(contract_root, stage, name)
        payload = json.loads(source.read_text(encoding="utf-8"))
        if payload.get("synthetic_data") is True or payload.get("verified_real_data") is False:
            raise RuntimeError(f"Refusing to sign non-real contract: {source}")
        files[f"{stage}/{name}"] = canonical_json(payload)
    manifest = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contracts": {name: {"sha256": sha256_bytes(data), "size": len(data)} for name, data in sorted(files.items())},
    }
    manifest_bytes = canonical_json(manifest)
    signature = hmac.new(signing_key(), manifest_bytes, hashlib.sha256).hexdigest().encode("ascii")
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_zip.with_suffix(".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
        archive.writestr("manifest.json", manifest_bytes)
        archive.writestr("manifest.hmac-sha256", signature)
    temporary.replace(output_zip)
    return {"bundle": str(output_zip), "bundle_sha256": sha256_bytes(output_zip.read_bytes()), "contracts": len(files)}


def verify_and_extract(bundle: Path, destination: Path) -> dict:
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError(f"Unsafe bundle member: {name}")
        manifest_bytes = archive.read("manifest.json")
        supplied = archive.read("manifest.hmac-sha256").decode("ascii").strip()
        expected = hmac.new(signing_key(), manifest_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(supplied, expected):
            raise RuntimeError("Contract bundle signature verification failed.")
        manifest = json.loads(manifest_bytes)
        for name, metadata in manifest["contracts"].items():
            data = archive.read(name)
            if sha256_bytes(data) != metadata["sha256"] or len(data) != metadata["size"]:
                raise RuntimeError(f"Contract hash/size mismatch: {name}")
        temp = Path(tempfile.mkdtemp(prefix="finai-contracts-", dir=destination.parent if destination.parent.exists() else None))
        try:
            for name in manifest["contracts"]:
                target = temp / Path(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
            if destination.exists():
                backup = destination.with_name(destination.name + ".previous")
                if backup.exists():
                    shutil.rmtree(backup)
                destination.replace(backup)
            temp.replace(destination)
        except Exception:
            shutil.rmtree(temp, ignore_errors=True)
            raise
    return {"destination": str(destination), "contracts": len(manifest["contracts"]), "signature_verified": True}


def s3_client():
    import boto3
    kwargs = {"region_name": os.environ.get("AWS_REGION", "us-east-1")}
    endpoint = os.environ.get("FINAI_S3_ENDPOINT_URL", "").strip()
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.client("s3", **kwargs)


def upload(bundle: Path, bucket: str, key: str) -> dict:
    if not bundle.is_file():
        raise FileNotFoundError(bundle)
    s3_client().upload_file(str(bundle), bucket, key, ExtraArgs={"ContentType": "application/zip", "Metadata": {"sha256": sha256_bytes(bundle.read_bytes())}})
    return {"bucket": bucket, "key": key, "bundle_sha256": sha256_bytes(bundle.read_bytes())}


def download(bucket: str, key: str, output: Path) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".part")
    s3_client().download_file(bucket, key, str(temporary))
    temporary.replace(output)
    return {"bucket": bucket, "key": key, "output": str(output), "bundle_sha256": sha256_bytes(output.read_bytes())}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create"); create.add_argument("--contract-root", required=True); create.add_argument("--output", required=True)
    up = sub.add_parser("upload"); up.add_argument("--bundle", required=True); up.add_argument("--bucket", required=True); up.add_argument("--key", required=True)
    fetch = sub.add_parser("download-verify"); fetch.add_argument("--bucket", required=True); fetch.add_argument("--key", required=True); fetch.add_argument("--bundle", required=True); fetch.add_argument("--destination", required=True)
    verify = sub.add_parser("verify"); verify.add_argument("--bundle", required=True); verify.add_argument("--destination", required=True)
    args = parser.parse_args()
    if args.command == "create": result = create_bundle(Path(args.contract_root), Path(args.output))
    elif args.command == "upload": result = upload(Path(args.bundle), args.bucket, args.key)
    elif args.command == "download-verify":
        result = {"download": download(args.bucket, args.key, Path(args.bundle)), "verification": verify_and_extract(Path(args.bundle), Path(args.destination))}
    else: result = verify_and_extract(Path(args.bundle), Path(args.destination))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

