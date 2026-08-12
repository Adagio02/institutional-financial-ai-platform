from fastapi.testclient import (
    TestClient,
)

from finai.api.main import application


client = TestClient(application)


def test_kill_switch_lifecycle() -> None:
    deactivate_response = client.post(
        ("/api/v1/trading-control/kill-switch/deactivate"),
        json={"reason": ("Integration test reset")},
    )

    assert deactivate_response.status_code == 200

    enable_response = client.put(
        "/api/v1/trading-control/enabled",
        json={
            "enabled": True,
            "reason": ("Integration test enable"),
        },
    )

    assert enable_response.status_code == 200

    enabled = enable_response.json()

    assert enabled["trading_enabled"] is True

    assert enabled["can_trade"] is True

    activate_response = client.post(
        ("/api/v1/trading-control/kill-switch/activate"),
        json={"reason": ("Integration test risk shutdown")},
    )

    assert activate_response.status_code == 200

    stopped = activate_response.json()

    assert stopped["kill_switch_active"] is True

    assert stopped["trading_enabled"] is False

    assert stopped["can_trade"] is False

    blocked_enable = client.put(
        "/api/v1/trading-control/enabled",
        json={
            "enabled": True,
            "reason": ("Should remain blocked"),
        },
    )

    assert blocked_enable.status_code == 409

    reset_response = client.post(
        ("/api/v1/trading-control/kill-switch/deactivate"),
        json={"reason": ("Integration test complete")},
    )

    assert reset_response.status_code == 200

    reenable_response = client.put(
        "/api/v1/trading-control/enabled",
        json={
            "enabled": True,
            "reason": ("Restore test state"),
        },
    )

    assert reenable_response.status_code == 200
