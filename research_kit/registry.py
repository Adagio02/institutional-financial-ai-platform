"""Experiment registry: an append-only log of every hypothesis and every test.

research/registry.jsonl is meant to be committed to git. Each hypothesis is registered
BEFORE it is tested; its spec is hashed, so changing it afterwards is detectable, and
each hypothesis gets exactly one historical test.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import RESEARCH

REGISTRY = RESEARCH / "registry.jsonl"
POLICY = RESEARCH / "policy.json"
REQUIRED = ["id", "hypothesis", "rationale", "signal", "horizon", "panel", "window", "decision_rule"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None
    except Exception:
        return None


def spec_hash(spec: dict) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:16]


def events(hypothesis_id: str | None = None) -> list[dict]:
    if not REGISTRY.exists():
        return []
    rows = [json.loads(line) for line in REGISTRY.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in rows if hypothesis_id is None or r["id"] == hypothesis_id]


def append(event: dict) -> None:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRY.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, default=str) + "\n")


def policy() -> dict:
    if not POLICY.exists():
        return {"closed_features": []}
    return json.loads(POLICY.read_text(encoding="utf-8"))


def registered_spec(hypothesis_id: str) -> dict:
    found = [e for e in events(hypothesis_id) if e["event"] == "registered"]
    if not found:
        raise SystemExit(f"'{hypothesis_id}' is not registered. Run: python -m research_kit register <spec.json>")
    return found[-1]["spec"]


def register(path: str) -> None:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if k not in spec]
    if missing:
        raise SystemExit(f"Spec is missing required fields: {missing}")
    existing = [e for e in events(spec["id"]) if e["event"] == "registered"]
    if existing:
        if existing[-1]["hash"] == spec_hash(spec):
            print(f"'{spec['id']}' is already registered with this exact spec.")
            return
        raise SystemExit(f"'{spec['id']}' is already registered with a DIFFERENT spec. Changing a hypothesis after "
                         "registration defeats pre-registration; register it under a new id instead.")
    closed = set(policy().get("closed_features", []))
    columns = set(spec["signal"]["columns"])
    if columns and columns <= closed:
        print("Note: every signal column is in the closed feature set, so this hypothesis can only be "
              "tested forward (freeze --exploratory), not historically.")
    append({"event": "registered", "id": spec["id"], "hash": spec_hash(spec), "spec": spec,
            "timestamp": now(), "git_commit": git_commit()})
    print(f"Registered '{spec['id']}' (spec hash {spec_hash(spec)}).")


def require_testable(hypothesis_id: str, force_reason: str | None) -> dict:
    spec = registered_spec(hypothesis_id)
    previous = [e for e in events(hypothesis_id) if e["event"] == "tested"]
    if previous and not force_reason:
        last = previous[-1]
        raise SystemExit(f"'{hypothesis_id}' was already tested on {last['timestamp']} "
                         f"(passed={last['passed']}). Each hypothesis gets ONE historical test. "
                         "If the earlier run was broken by a bug, rerun with --force-reason \"what was wrong\"; "
                         "the reason is recorded permanently.")
    closed = set(policy().get("closed_features", []))
    if set(spec["signal"]["columns"]) <= closed:
        raise SystemExit("All signal columns are closed for historical testing (see research/policy.json). "
                         "Test this idea forward instead: python -m research_kit freeze "
                         f"{hypothesis_id} --exploratory")
    return spec


def list_hypotheses() -> None:
    rows = events()
    if not rows:
        print("Registry is empty. Register a hypothesis with: python -m research_kit register <spec.json>")
        return
    ids = sorted({r["id"] for r in rows})
    print(f"{'id':28s} {'registered':20s} {'tested':8s} {'passed':7s} {'frozen':8s} shadow rebalances")
    for hid in ids:
        ev = events(hid)
        reg = next((e["timestamp"][:19] for e in ev if e["event"] == "registered"), "-")
        tests = [e for e in ev if e["event"] == "tested"]
        frozen = next((e for e in reversed(ev) if e["event"] == "frozen"), None)
        shadow = sum(1 for e in ev if e["event"] == "shadow_rebalance")
        print(f"{hid:28s} {reg:20s} {len(tests):<8d} {str(tests[-1]['passed']) if tests else '-':7s} "
              f"{(frozen['status'] if frozen else '-'):8s} {shadow}")
    print(f"\nTotal historical tests on record: {sum(1 for r in rows if r['event'] == 'tested')}")
