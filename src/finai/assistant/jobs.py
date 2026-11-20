"""Jobs Ask FinAI may *propose*. A job only runs after the user clicks Confirm in the UI.

There is deliberately no job that trades, changes governance, edits the V009
protocol/policy/panel, or changes configuration.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any

from finai.assistant.knowledge import PROJECT_ROOT, redact


@dataclass(frozen=True)
class Job:
    key: str
    title: str
    description: str
    script: str
    timeout_seconds: int


JOBS: dict[str, Job] = {
    "legacy_learning_cycle": Job(
        key="legacy_learning_cycle",
        title="Run one legacy V4.1 learning cycle",
        description=(
            "Trains and evaluates the legacy AAPL 1-minute models once and writes "
            "artifacts/v41. Research only: it never places orders or promotes a champion."
        ),
        script="scripts/run_v41_learning_cycle.py",
        timeout_seconds=1800,
    ),
}


def describe_jobs() -> list[dict[str, str]]:
    return [{"job": j.key, "title": j.title, "description": j.description} for j in JOBS.values()]


def run_job(key: str) -> dict[str, Any]:
    """Run a confirmed job and return its result. Called only from the UI's Confirm button."""
    job = JOBS.get(key)
    if job is None:
        return {"ok": False, "error": f"Unknown job {key}"}
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    env.pop("ANTHROPIC_API_KEY", None)  # jobs never need the assistant's key
    started = time.time()
    try:
        completed = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / job.script)],
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=job.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "job": key, "error": f"Timed out after {job.timeout_seconds} s"}
    output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    return {
        "ok": completed.returncode == 0,
        "job": key,
        "exit_code": completed.returncode,
        "seconds": round(time.time() - started, 1),
        "output_tail": redact(output[-6000:]),
    }
