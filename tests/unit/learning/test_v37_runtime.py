from pathlib import Path

from finai.application.services.v37_runtime_state_service import (
    V37RuntimeStateService,
)


def test_state_defaults(
    tmp_path: Path,
) -> None:
    service = (
        V37RuntimeStateService(
            state_path=str(
                tmp_path
                / "state.json"
            ),
            event_log_path=str(
                tmp_path
                / "events.jsonl"
            ),
        )
    )

    state = service.load()

    assert (
        state[
            "version"
        ]
        == "3.7"
    )

    assert (
        state[
            "last_learning_bar_count"
        ]
        == 0
    )


def test_state_round_trip(
    tmp_path: Path,
) -> None:
    service = (
        V37RuntimeStateService(
            state_path=str(
                tmp_path
                / "state.json"
            ),
            event_log_path=str(
                tmp_path
                / "events.jsonl"
            ),
        )
    )

    expected = {
        "version": "3.7",
        "last_learning_bar_count": 123,
        "last_learning_timestamp": None,
        "jobs": {},
    }

    service.save(
        expected
    )

    assert (
        service.load()
        == expected
    )


def test_event_logging(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "events.jsonl"
    )

    service = (
        V37RuntimeStateService(
            state_path=str(
                tmp_path
                / "state.json"
            ),
            event_log_path=str(
                path
            ),
        )
    )

    service.record_event(
        event_type="test",
        message="hello",
    )

    assert path.exists()

    assert (
        '"event_type": "test"'
        in path.read_text(
            encoding="utf-8"
        )
    )