"""Minimal Claude Messages API client with a tool-use loop (standard library only)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from finai.assistant import knowledge
from finai.assistant.jobs import JOBS, describe_jobs

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = os.getenv("FINAI_CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_TOKENS = 2048
MAX_TOOL_ROUNDS = 8

SYSTEM_PROMPT = """You are Ask FinAI, the assistant inside Felipe's FinAI research platform.
You answer questions about the platform's research, data pipelines and governance using the
tools provided. Look things up with tools instead of guessing, and never invent numbers.

How the platform is organised:
- PRIMARY program: V5.6 development research (versions 005-008: daily, cross-sectional,
  cost-aware, purged walk-forward) and V009, the frozen candidate's prospective test, which is
  PERFORMANCE-BLIND until its 52-period one-shot lock. Forward shadow tests H0/H3/H5 run daily.
- LEGACY track: the V4.1 intraday loop (AAPL, 1-minute bars, 5-bar horizon). It is kept for
  reference; its candidates usually fail the gates. Say so when it comes up.

Rules you must follow:
- V009 is performance-blind. Never estimate, infer or compute its returns, and never suggest
  looking at its performance before the lock.
- Never recommend lowering gates, re-tuning on already-observed holdout or V009 data, or
  deleting and recreating sealed protocols or policies. Explain the integrity reason instead.
- You cannot trade and live trading is disabled. Do not imply otherwise.
- You can propose a job with request_job, but it only runs if the user clicks Confirm.
- This is research, not financial advice.

Style: plain, concise English. Lead with the answer. End every answer with a short
"Sources:" line listing the project files your answer came from (tool results include them)."""

RunTool = Callable[[str, dict[str, Any]], str]


def tool_definitions() -> list[dict[str, Any]]:
    tools = [
        {"name": name, "description": spec["description"], "input_schema": spec["input_schema"]}
        for name, spec in knowledge.TOOLS.items()
    ]
    tools.append(
        {
            "name": "request_job",
            "description": (
                "Propose running a job. It does NOT run now: the user sees a Confirm button. "
                "Available jobs: " + json.dumps(describe_jobs())
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "job": {"type": "string", "enum": sorted(JOBS)},
                    "reason": {"type": "string", "description": "One sentence on why."},
                },
                "required": ["job", "reason"],
            },
        }
    )
    return tools


@dataclass
class TurnResult:
    text: str
    messages: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    pending_job: dict[str, str] | None = None
    usage: dict[str, int] = field(default_factory=dict)


class ClaudeError(RuntimeError):
    pass


def _post(payload: dict[str, Any], api_key: str, timeout: int = 120) -> dict[str, Any]:
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": API_VERSION,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:600]
        if exc.code == 401:
            raise ClaudeError("The Anthropic API key was rejected (401). Run scripts\\set_anthropic_key.ps1 again.") from exc
        if exc.code == 429:
            raise ClaudeError("Rate limited by the Anthropic API (429). Wait a minute and retry.") from exc
        raise ClaudeError(f"Anthropic API error {exc.code}: {knowledge.redact(body)}") from exc
    except urllib.error.URLError as exc:
        raise ClaudeError(f"Could not reach the Anthropic API: {exc.reason}") from exc


def run_turn(
    messages: list[dict[str, Any]],
    api_key: str,
    model: str = DEFAULT_MODEL,
    post: Callable[[dict[str, Any], str], dict[str, Any]] | None = None,
    run_tool: RunTool | None = None,
) -> TurnResult:
    """Send the conversation, run read-only tools until Claude answers, return the reply."""
    post = post or _post
    run_tool = run_tool or knowledge.run_tool
    messages = list(messages)
    calls: list[dict[str, Any]] = []
    pending: dict[str, str] | None = None
    usage = {"input_tokens": 0, "output_tokens": 0}

    for _ in range(MAX_TOOL_ROUNDS):
        response = post(
            {
                "model": model,
                "max_tokens": MAX_TOKENS,
                "system": SYSTEM_PROMPT,
                "tools": tool_definitions(),
                "messages": list(messages),
            },
            api_key,
        )
        for key in usage:
            usage[key] += int((response.get("usage") or {}).get(key, 0))
        content = response.get("content") or []
        messages.append({"role": "assistant", "content": content})

        tool_uses = [block for block in content if block.get("type") == "tool_use"]
        if response.get("stop_reason") != "tool_use" or not tool_uses:
            text = "\n".join(b.get("text", "") for b in content if b.get("type") == "text").strip()
            return TurnResult(text=text, messages=messages, tool_calls=calls, pending_job=pending, usage=usage)

        results = []
        for block in tool_uses:
            name, arguments = block.get("name", ""), block.get("input") or {}
            if name == "request_job":
                job = str(arguments.get("job", ""))
                if job in JOBS:
                    pending = {"job": job, "reason": str(arguments.get("reason", ""))}
                    output = json.dumps({"status": "awaiting_user_confirmation", "job": JOBS[job].title})
                else:
                    output = json.dumps({"error": f"Unknown job {job}"})
            else:
                output = run_tool(name, arguments)
            calls.append({"tool": name, "input": arguments})
            results.append({"type": "tool_result", "tool_use_id": block.get("id"), "content": output})
        messages.append({"role": "user", "content": results})

    return TurnResult(
        text="I stopped after several lookups without finishing. Please ask a narrower question.",
        messages=messages,
        tool_calls=calls,
        pending_job=pending,
        usage=usage,
    )
