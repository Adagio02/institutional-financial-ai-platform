from uuid import uuid4

from fastapi.testclient import TestClient

from finai.api.main import application


client = TestClient(application)


def test_create_and_get_instrument() -> None:
    symbol = f"T{uuid4().hex[:7]}".upper()

    create_response = client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "name": "Version 0.3 Test Instrument",
            "asset_class": "equity",
            "exchange": "TEST",
            "currency": "USD",
        },
    )

    assert create_response.status_code == 201

    created = create_response.json()

    assert created["symbol"] == symbol
    assert created["active"] is True

    get_response = client.get(f"/api/v1/instruments/{symbol}")

    assert get_response.status_code == 200
    assert get_response.json()["symbol"] == symbol


def test_duplicate_instrument_returns_conflict() -> None:
    symbol = f"D{uuid4().hex[:7]}".upper()

    payload = {
        "symbol": symbol,
        "name": "Duplicate Test",
        "asset_class": "equity",
        "exchange": "TEST",
        "currency": "USD",
    }

    first_response = client.post(
        "/api/v1/instruments",
        json=payload,
    )

    second_response = client.post(
        "/api/v1/instruments",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
