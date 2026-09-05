from uuid import uuid4

from fastapi.testclient import TestClient

from finai.api.main import application


client = TestClient(
    application
)


def create_account() -> dict:
    response = client.post(
        "/api/v1/paper/accounts",
        json={
            "name": (
                "Trading-Control-"
                + uuid4().hex[:8]
            ),
            "initial_cash": 100_000.0,
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def test_control_is_created_for_account() -> None:
    account = create_account()

    response = client.get(
        (
            "/api/v1/trading-controls/"
            + account["id"]
        )
    )

    assert response.status_code == 200, (
        response.text
    )

    payload = response.json()

    assert (
        payload["account_id"]
        == account["id"]
    )

    assert (
        payload["trading_enabled"]
        is True
    )

    assert (
        payload["manual_halt"]
        is False
    )

    assert (
        payload[
            "circuit_breaker_tripped"
        ]
        is False
    )

    assert (
        payload[
            "maximum_daily_loss_fraction"
        ]
        > 0
    )

    assert (
        payload[
            "maximum_gross_exposure_fraction"
        ]
        > 0
    )

    assert (
        payload[
            "maximum_symbol_fraction"
        ]
        > 0
    )

    assert (
        payload[
            "maximum_order_fraction"
        ]
        > 0
    )


def test_account_can_be_manually_halted() -> None:
    account = create_account()

    response = client.post(
        (
            "/api/v1/trading-controls/"
            + account["id"]
            + "/halt"
        ),
        json={
            "reason": (
                "Integration test halt"
            ),
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    payload = response.json()

    assert (
        payload["manual_halt"]
        is True
    )

    assert (
        payload[
            "manual_halt_reason"
        ]
        == "Integration test halt"
    )


def test_account_can_resume() -> None:
    account = create_account()

    halt_response = client.post(
        (
            "/api/v1/trading-controls/"
            + account["id"]
            + "/halt"
        ),
        json={
            "reason": "Temporary halt",
        },
    )

    assert (
        halt_response.status_code
        == 200
    ), halt_response.text

    resume_response = client.post(
        (
            "/api/v1/trading-controls/"
            + account["id"]
            + "/resume"
        )
    )

    assert (
        resume_response.status_code
        == 200
    ), resume_response.text

    payload = resume_response.json()

    assert (
        payload["manual_halt"]
        is False
    )

    assert (
        payload[
            "manual_halt_reason"
        ]
        is None
    )


def test_account_can_be_disabled_and_enabled() -> None:
    account = create_account()

    disable_response = client.post(
        (
            "/api/v1/trading-controls/"
            + account["id"]
            + "/enabled"
        ),
        json={
            "enabled": False,
        },
    )

    assert (
        disable_response.status_code
        == 200
    ), disable_response.text

    disabled = (
        disable_response.json()
    )

    assert (
        disabled["trading_enabled"]
        is False
    )

    enable_response = client.post(
        (
            "/api/v1/trading-controls/"
            + account["id"]
            + "/enabled"
        ),
        json={
            "enabled": True,
        },
    )

    assert (
        enable_response.status_code
        == 200
    ), enable_response.text

    enabled = (
        enable_response.json()
    )

    assert (
        enabled["trading_enabled"]
        is True
    )


def test_circuit_breaker_can_be_reset() -> None:
    account = create_account()

    response = client.post(
        (
            "/api/v1/trading-controls/"
            + account["id"]
            + "/reset-circuit-breaker"
        )
    )

    assert response.status_code == 200, (
        response.text
    )

    payload = response.json()

    assert (
        payload[
            "circuit_breaker_tripped"
        ]
        is False
    )

    assert (
        payload[
            "circuit_breaker_reason"
        ]
        is None
    )

    assert (
        payload[
            "circuit_breaker_message"
        ]
        is None
    )

    assert (
        payload[
            "circuit_breaker_tripped_at"
        ]
        is None
    )


def test_unknown_account_returns_404() -> None:
    unknown_account_id = str(
        uuid4()
    )

    response = client.get(
        (
            "/api/v1/trading-controls/"
            + unknown_account_id
        )
    )

    assert (
        response.status_code
        == 404
    )


def test_blank_halt_reason_is_rejected() -> None:
    account = create_account()

    response = client.post(
        (
            "/api/v1/trading-controls/"
            + account["id"]
            + "/halt"
        ),
        json={
            "reason": "",
        },
    )

    assert response.status_code == 422