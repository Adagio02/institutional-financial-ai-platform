from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import pandas as pd


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json_atomic(path: str | Path, value: dict[str, Any], *, exclusive: bool = False) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if exclusive and target.exists():
        raise FileExistsError(f"Sealed artifact already exists: {target}")
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")
    if exclusive and target.exists():
        temporary.unlink(missing_ok=True)
        raise FileExistsError(f"Sealed artifact already exists: {target}")
    os.replace(temporary, target)
    return target


def protocol_start(protocol: dict[str, Any]) -> pd.Timestamp:
    return pd.Timestamp(protocol["prospective_lock_start"]).tz_convert("UTC")


def qualified_dates(panel: pd.DataFrame, protocol: dict[str, Any], minimum_symbols: int) -> list[pd.Timestamp]:
    required = {"timestamp", "symbol"}
    missing = required.difference(panel.columns)
    if missing:
        raise ValueError(f"Prospective panel missing columns: {sorted(missing)}")
    work = panel[["timestamp", "symbol"]].copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"], utc=True)
    work = work[work["timestamp"] >= protocol_start(protocol)]
    counts = work.groupby("timestamp", observed=True)["symbol"].nunique().sort_index()
    return list(counts[counts >= minimum_symbols].index)


def completed_rebalance_periods(date_count: int, horizon: int = 5, rebalance_every: int = 5) -> int:
    mature_dates = max(0, date_count - horizon)
    return math.ceil(mature_dates / rebalance_every) if mature_dates else 0


def status_for(periods: int) -> tuple[str, int]:
    if periods >= 52:
        return "official_lock_ready", 52
    if periods >= 26:
        return "validated_shadow_monitoring", 52
    if periods >= 13:
        return "provisional_shadow_champion", 26
    return "collecting", 13


def seal(path: Path) -> str:
    digest = sha256(path)
    checksum = path.with_suffix(path.suffix + ".sha256")
    checksum.write_text(f"{digest}  {path.name}\n", encoding="ascii")
    try:
        path.chmod(0o444)
        checksum.chmod(0o444)
    except OSError:
        pass
    return digest
