"""Ask FinAI safety and tool-loop tests (no network, no API key needed)."""

import json

import pytest

from finai.assistant import claude_client, knowledge
from finai.assistant.jobs import JOBS


@pytest.fixture()
def project(tmp_path, monkeypatch):
    (tmp_path / "artifacts" / "v009-shadow-monitoring").mkdir(parents=True)
    (tmp_path / "artifacts" / "v009-shadow-monitoring" / "latest_status.json").write_text(
        json.dumps({"designation": "collecting", "completed_non_overlapping_periods": 9,
                    "next_milestone_periods": 13, "performance_blind": True}),
        encoding="utf-8",
    )
    (tmp_path / "artifacts" / "notes.txt").write_text("password=hunter2 key " + "P" + "K" + "A" * 18, encoding="utf-8")
    (tmp_path / ".env").write_text("ALPACA_SECRET_KEY=topsecret", encoding="utf-8")
    (tmp_path / "artifacts" / ".env").write_text("X=1", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "code.py").write_text("print(1)", encoding="utf-8")
    monkeypatch.setattr(knowledge, "PROJECT_ROOT", tmp_path.resolve())
    return tmp_path


@pytest.mark.parametrize("path", [".env", "artifacts/.env", "../outside.txt", ".git/config",
                                  "src/code.py", "artifacts/alpaca-credential.xml", ""])
def test_blocked_paths(project, path):
    with pytest.raises(knowledge.AccessDenied):
        knowledge.resolve_allowed(path)


def test_read_allowed_file_is_redacted(project):
    result = json.loads(knowledge.run_tool("read_file", {"path": "artifacts/notes.txt"}))
    assert "hunter2" not in result["content"]
    assert "PK" + "A" * 18 not in result["content"]


def test_env_file_cannot_be_read_through_tool(project):
    result = json.loads(knowledge.run_tool("read_file", {"path": ".env"}))
    assert "error" in result
    assert "topsecret" not in json.dumps(result)


def test_redact_common_key_shapes():
    # Fake keys are assembled at runtime so secret scanners (gitleaks) don't flag the source.
    fake_aws = "AK" + "IA" + "Q" * 16
    fake_alpaca = "P" + "K" + "Z" * 18
    text = knowledge.redact(f"sk-ant-api03-abcdefghijklmnop and secret_key: abc123 and {fake_aws} {fake_alpaca}")
    assert "abcdefghijklmnop" not in text and "abc123" not in text
    assert fake_aws not in text and fake_alpaca not in text


def test_v009_status_reports_milestones_without_performance(project):
    result = knowledge.get_v009_status()
    assert result["milestones"]["13"] == {"completed": 9, "target": 13, "reached": False}
    assert "performance-blind" in result["note"]


def test_unknown_tool_returns_error():
    assert "error" in json.loads(knowledge.run_tool("place_order", {"symbol": "AAPL"}))


def test_no_trading_or_governance_jobs():
    assert set(JOBS) == {"legacy_learning_cycle"}
    names = {tool["name"] for tool in claude_client.tool_definitions()}
    assert not any(word in name for name in names for word in ("order", "trade", "promote", "gate", "config"))


def test_tool_loop_runs_tools_then_answers(project):
    replies = [
        {"stop_reason": "tool_use", "usage": {"input_tokens": 10, "output_tokens": 5},
         "content": [{"type": "tool_use", "id": "t1", "name": "get_v009_status", "input": {}}]},
        {"stop_reason": "end_turn", "usage": {"input_tokens": 20, "output_tokens": 7},
         "content": [{"type": "text", "text": "9 of 13 periods.\nSources: latest_status.json"}]},
    ]
    sent = []

    def fake_post(payload, api_key):
        sent.append(payload)
        return replies[len(sent) - 1]

    result = claude_client.run_turn([{"role": "user", "content": "status?"}], "sk-ant-test", post=fake_post)
    assert result.text.startswith("9 of 13")
    assert [c["tool"] for c in result.tool_calls] == ["get_v009_status"]
    tool_result = sent[1]["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and tool_result["tool_use_id"] == "t1"
    assert "collecting" in tool_result["content"]
    assert result.usage == {"input_tokens": 30, "output_tokens": 12}
    assert sent[0]["system"] == claude_client.SYSTEM_PROMPT


def test_request_job_only_proposes(project, monkeypatch):
    from finai.assistant import jobs

    monkeypatch.setattr(jobs, "run_job", lambda key: pytest.fail("job must not run without confirmation"))
    replies = [
        {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": "j1", "name": "request_job",
                                                  "input": {"job": "legacy_learning_cycle", "reason": "refresh"}}]},
        {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Click Confirm to run it."}]},
    ]
    responses = iter(replies)
    result = claude_client.run_turn([{"role": "user", "content": "run it"}], "k",
                                    post=lambda payload, key: next(responses))
    assert result.pending_job == {"job": "legacy_learning_cycle", "reason": "refresh"}
