from finai.application.services.v37_runtime_state_service import V37RuntimeStateService
from finai.core.durable_io import write_text_durable


def test_write_text_durable_replaces_file(tmp_path):
    target = tmp_path / "state.json"
    write_text_durable(target, '{"a": 1}')
    write_text_durable(target, '{"a": 2}')
    assert target.read_text(encoding="utf-8") == '{"a": 2}'
    assert not (tmp_path / "state.json.tmp").exists()


def test_corrupt_state_is_recovered(tmp_path):
    state = tmp_path / "state.json"
    state.write_bytes(b"\x00" * 1149)  # what a power loss left behind
    service = V37RuntimeStateService(state_path=str(state), event_log_path=str(tmp_path / "events.jsonl"))
    loaded = service.load()
    assert loaded["jobs"] == {} and loaded["version"] == "3.7"
    assert list(tmp_path.glob("state.json.corrupt-*"))
    assert "state_recovered" in (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    service.save({"version": "3.7", "jobs": {"x": 1}})
    assert service.load()["jobs"] == {"x": 1}
