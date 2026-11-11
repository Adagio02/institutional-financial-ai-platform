"""Read-only views of the FinAI project that Ask FinAI can use as tools.

Safety rules enforced here (not just in the prompt):
- Only files inside the project's allowed folders can be read.
- Secrets are never readable: .env files, credential/secret/key files and .git are blocked.
- Anything that looks like an API key or password is redacted from returned text.
- Outputs are size-capped.
"""

from __future__ import annotations

import csv
import json
import os
import re
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(
    os.getenv("FINAI_PROJECT_ROOT", Path(__file__).resolve().parents[3])
).resolve()

ALLOWED_TOP_LEVEL = ("artifacts", "research", "logs", "docs", "config", "research_kit")
ALLOWED_SUFFIXES = (".json", ".jsonl", ".csv", ".md", ".txt", ".log", ".yml", ".yaml")
BLOCKED_NAME = re.compile(r"(^\.env)|credential|secret|password|\.key$|\.pem$|token", re.I)
MAX_CHARS = 20_000

RESEARCH_VERSIONS = ("005", "006", "007", "008")

_REDACTIONS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"), "[REDACTED_ANTHROPIC_KEY]"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"), "[REDACTED_KEY]"),
    (re.compile(r"\b(?:PK|AK)[A-Z0-9]{16,}\b"), "[REDACTED_ALPACA_KEY]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    (
        re.compile(
            r"(?i)((?:api[_-]?key|secret[_-]?key|secret|password|passwd|token)\s*[\"']?\s*[=:]\s*[\"']?)"
            r"[^\s\"',}]+"
        ),
        r"\1[REDACTED]",
    ),
]


class AccessDenied(ValueError):
    """Raised when a path is outside what Ask FinAI may read."""


def redact(text: str) -> str:
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def _age(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    seconds = time.time() - path.stat().st_mtime
    return {
        "exists": True,
        "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(path.stat().st_mtime)),
        "age_days": round(seconds / 86400, 2),
    }


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def resolve_allowed(relative_path: str) -> Path:
    """Resolve a project-relative path and refuse anything not allowed."""
    cleaned = relative_path.strip().replace("\\", "/").lstrip("/")
    candidate = (PROJECT_ROOT / cleaned).resolve()
    try:
        parts = candidate.relative_to(PROJECT_ROOT).parts
    except ValueError as exc:
        raise AccessDenied("Path is outside the FinAI project.") from exc
    if not parts:
        raise AccessDenied("Give a file or folder inside the project.")
    if any(p == ".git" or BLOCKED_NAME.search(p) for p in parts):
        raise AccessDenied("That file may contain secrets, so Ask FinAI cannot read it.")
    is_root_readme = len(parts) == 1 and parts[0].upper().startswith("README") and parts[0].endswith(".md")
    if parts[0] not in ALLOWED_TOP_LEVEL and not is_root_readme:
        raise AccessDenied(
            "Ask FinAI can read: " + ", ".join(ALLOWED_TOP_LEVEL) + " and README*.md files."
        )
    return candidate


# ----------------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------------


def get_v009_status() -> dict[str, Any]:
    path = PROJECT_ROOT / "artifacts" / "v009-shadow-monitoring" / "latest_status.json"
    status = _read_json(path)
    if status is None:
        return {"source": _rel(path), "available": False}
    done = int(status.get("completed_non_overlapping_periods") or 0)
    return {
        "source": _rel(path),
        "file": _age(path),
        "status": status,
        "milestones": {
            str(target): {"completed": done, "target": target, "reached": done >= target}
            for target in (13, 26, 52)
        },
        "note": (
            "V009 is performance-blind: this report intentionally contains no returns, "
            "Sharpe or IC. Do not estimate or infer its performance."
        ),
    }


def get_shadow_strategies() -> dict[str, Any]:
    path = PROJECT_ROOT / "research" / "shadow" / "status.json"
    status = _read_json(path)
    if status is None:
        return {"source": _rel(path), "available": False}
    return {"source": _rel(path), "file": _age(path), "status": status}


def get_research_history() -> dict[str, Any]:
    rows = []
    for version in RESEARCH_VERSIONS:
        path = PROJECT_ROOT / "artifacts" / f"v56-research-{version}" / "research_report.json"
        report = _read_json(path)
        if not report:
            continue
        metrics = report.get("metrics", {})
        rows.append(
            {
                "version": f"V{version}",
                "source": _rel(path),
                "net_return": metrics.get("cumulative_net_return"),
                "annualized_sharpe": metrics.get("annualized_sharpe"),
                "maximum_drawdown": metrics.get("maximum_drawdown"),
                "rank_ic": report.get("mean_rebalance_rank_ic",
                                      report.get("mean_oos_rank_ic",
                                                 report.get("mean_rebalance_residual_rank_ic"))),
                "checks": report.get("checks"),
                "blocking_reasons": report.get("blocking_reasons"),
                "required_next_step": report.get("required_next_step"),
            }
        )
    ledger_path = PROJECT_ROOT / "artifacts" / "v56_research_attempt_ledger.csv"
    ledger = []
    if ledger_path.exists():
        with ledger_path.open(encoding="utf-8-sig", newline="") as handle:
            ledger = list(csv.DictReader(handle))
    return {
        "reports": rows,
        "attempt_ledger": ledger,
        "ledger_source": _rel(ledger_path),
        "note": (
            "These ran on an already-observed development window. Passing there only allows "
            "freezing a candidate; it must then face genuinely unseen data once."
        ),
    }


def get_research_report(version: str) -> dict[str, Any]:
    version = version.strip().lstrip("vV").zfill(3)
    if version not in RESEARCH_VERSIONS:
        return {"error": f"Unknown version. Available: {', '.join(RESEARCH_VERSIONS)}"}
    path = PROJECT_ROOT / "artifacts" / f"v56-research-{version}" / "research_report.json"
    report = _read_json(path)
    if report is None:
        return {"source": _rel(path), "available": False}
    for noisy in ("hashes", "artifacts"):
        report.pop(noisy, None)
    return {"source": _rel(path), "report": report}


def get_legacy_learning_cycle() -> dict[str, Any]:
    path = PROJECT_ROOT / "artifacts" / "v41" / "latest_learning_cycle.json"
    cycle = _read_json(path)
    return {
        "source": _rel(path),
        "file": _age(path),
        "track": "LEGACY",
        "track_note": (
            "V4.1 is the legacy intraday loop: AAPL, 1-minute bars, 5-bar horizon. "
            "See docs/LEGACY-V41-INTRADAY.md. It is not the primary research program."
        ),
        "latest_cycle": cycle,
    }


def get_recent_events(limit: int = 15) -> dict[str, Any]:
    limit = max(1, min(int(limit), 50))
    path = PROJECT_ROOT / "artifacts" / "v37" / "events.jsonl"
    events = []
    if path.exists():
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        for line in lines:
            try:
                events.append(json.loads(line))
            except ValueError:
                events.append({"raw": redact(line[:500])})
    return {"source": _rel(path), "file": _age(path), "events": events}


def get_collection_health() -> dict[str, Any]:
    folder = PROJECT_ROOT / "logs" / "v009-prospective"
    logs = sorted(folder.glob("collection-*.log"), key=lambda p: p.stat().st_mtime) if folder.exists() else []
    if not logs:
        return {"source": _rel(folder), "available": False}

    def verdict(path: Path) -> str:
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"Traceback|failed\.|Error:", text):
            return "FAILED"
        if "Saved" in text:
            return "OK"
        return "UNKNOWN"

    latest = logs[-1]
    recent = [{"log": p.name, "result": verdict(p)} for p in logs[-10:]]
    tail = latest.read_text(encoding="utf-8", errors="replace").splitlines()[-25:]
    return {
        "source": _rel(latest),
        "file": _age(latest),
        "latest_result": recent[-1]["result"],
        "recent_runs": recent,
        "latest_log_tail": redact("\n".join(tail)),
    }


def list_files(folder: str) -> dict[str, Any]:
    path = resolve_allowed(folder)
    if not path.is_dir():
        return {"error": "Not a folder."}
    entries = []
    for child in sorted(path.iterdir(), key=lambda p: p.name)[:150]:
        if BLOCKED_NAME.search(child.name):
            continue
        info = {"name": child.name, "type": "folder" if child.is_dir() else "file"}
        if child.is_file():
            info["bytes"] = child.stat().st_size
            info.update(_age(child))
        entries.append(info)
    return {"folder": _rel(path), "entries": entries}


def read_file(path: str) -> dict[str, Any]:
    target = resolve_allowed(path)
    if not target.is_file():
        return {"error": "File not found."}
    if target.suffix.lower() not in ALLOWED_SUFFIXES:
        return {"error": "Only text files can be read: " + ", ".join(ALLOWED_SUFFIXES)}
    text = target.read_text(encoding="utf-8", errors="replace")
    truncated = len(text) > MAX_CHARS
    if truncated:
        # Logs and event streams are most useful at the end.
        text = text[-MAX_CHARS:] if target.suffix in (".log", ".jsonl") else text[:MAX_CHARS]
    return {"source": _rel(target), "file": _age(target), "truncated": truncated, "content": redact(text)}


def get_platform_overview() -> dict[str, Any]:
    v009 = get_v009_status()
    shadow = get_shadow_strategies()
    legacy = get_legacy_learning_cycle()
    collection = get_collection_health()
    shadow_status = shadow.get("status") or {}
    return {
        "primary_program": {
            "v009_prospective_test": {
                "designation": (v009.get("status") or {}).get("designation"),
                "completed_periods": (v009.get("status") or {}).get("completed_non_overlapping_periods"),
                "next_milestone": (v009.get("status") or {}).get("next_milestone_periods"),
                "updated": (v009.get("file") or {}).get("modified"),
                "source": v009.get("source"),
            },
            "daily_collection": {
                "latest_result": collection.get("latest_result"),
                "updated": (collection.get("file") or {}).get("modified"),
                "source": collection.get("source"),
            },
            "shadow_strategies": {
                "healthy": shadow_status.get("healthy"),
                "problems": shadow_status.get("problems"),
                "count": len(shadow_status.get("strategies") or []),
                "updated": shadow_status.get("updated"),
                "source": shadow.get("source"),
            },
        },
        "legacy_track": {
            "name": "V4.1 intraday (AAPL, 1-minute)",
            "latest_cycle_updated": (legacy.get("file") or {}).get("modified"),
            "source": legacy.get("source"),
        },
        "trading": "Paper/shadow only. Live trading is not enabled and Ask FinAI cannot place orders.",
    }


TOOLS: dict[str, dict[str, Any]] = {
    "get_platform_overview": {
        "function": get_platform_overview,
        "description": "One-call summary of FinAI: V009 status, daily collection health, shadow strategies and the legacy track. Start here for broad questions.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "get_v009_status": {
        "function": get_v009_status,
        "description": "V009 prospective (performance-blind) test status and milestone progress (13, 26, 52 periods).",
        "input_schema": {"type": "object", "properties": {}},
    },
    "get_shadow_strategies": {
        "function": get_shadow_strategies,
        "description": "Forward shadow tests (H0, H3, H5): verdicts, completed vs needed periods, open period and early-retirement rules.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "get_research_history": {
        "function": get_research_history,
        "description": "V5.6 development research 005-008: net return, Sharpe, drawdown, rank IC, gate checks, blocking reasons and the attempt ledger.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "get_research_report": {
        "function": get_research_report,
        "description": "Full research_report.json for one V5.6 research version (005, 006, 007 or 008), including config and features.",
        "input_schema": {
            "type": "object",
            "properties": {"version": {"type": "string", "description": "005, 006, 007 or 008"}},
            "required": ["version"],
        },
    },
    "get_legacy_learning_cycle": {
        "function": get_legacy_learning_cycle,
        "description": "Latest learning cycle of the LEGACY V4.1 intraday loop (what the old Executive dashboard showed).",
        "input_schema": {"type": "object", "properties": {}},
    },
    "get_recent_events": {
        "function": get_recent_events,
        "description": "Recent autonomous supervisor events (learning cycles, starts, errors).",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 50}},
        },
    },
    "get_collection_health": {
        "function": get_collection_health,
        "description": "Daily V009 data-collection runs: latest result (OK/FAILED), recent run history and the latest log tail.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "list_files": {
        "function": list_files,
        "description": "List a folder inside artifacts, research, logs, docs, config or research_kit.",
        "input_schema": {
            "type": "object",
            "properties": {"folder": {"type": "string", "description": "Project-relative folder, e.g. artifacts/v41"}},
            "required": ["folder"],
        },
    },
    "read_file": {
        "function": read_file,
        "description": "Read a text file (json, jsonl, csv, md, txt, log, yml) inside the allowed folders or a root README. Secrets are blocked and redacted.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Project-relative path"}},
            "required": ["path"],
        },
    },
}


def run_tool(name: str, arguments: dict[str, Any] | None) -> str:
    """Run a read-only tool and return JSON text (never raises)."""
    spec = TOOLS.get(name)
    if spec is None:
        return json.dumps({"error": f"Unknown tool {name}"})
    try:
        result = spec["function"](**(arguments or {}))
    except AccessDenied as exc:
        result = {"error": str(exc)}
    except Exception as exc:  # report, don't crash the chat
        result = {"error": f"{type(exc).__name__}: {exc}"}
    text = redact(json.dumps(result, default=str, indent=1))
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n... [truncated]"
    return text
