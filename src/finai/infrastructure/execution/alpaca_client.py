from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ALPACA_PAPER_BASE_URL = (
    "https://paper-api.alpaca.markets"
)


class AlpacaApiError(RuntimeError):
    pass


class AlpacaAuthenticationError(
    AlpacaApiError
):
    pass


class AlpacaPaperClient:
    def __init__(
        self,
        *,
        api_key: str,
        secret_key: str,
        base_url: str,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._api_key = api_key.strip()

        self._secret_key = (
            secret_key.strip()
        )

        self._base_url = (
            base_url.strip().rstrip("/")
        )

        self._timeout_seconds = (
            timeout_seconds
        )

        if not self._api_key:
            raise ValueError(
                "Alpaca API key is required."
            )

        if not self._secret_key:
            raise ValueError(
                "Alpaca secret key is required."
            )

        if (
            self._base_url
            != ALPACA_PAPER_BASE_URL
        ):
            raise ValueError(
                "Version 1.9 supports only "
                "the Alpaca paper endpoint."
            )

        if self._timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be "
                "greater than zero."
            )

    @property
    def base_url(self) -> str:
        return self._base_url

    def get_account(
        self,
    ) -> dict[str, Any]:
        return self._request(
            method="GET",
            path="/v2/account",
        )

    def submit_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        time_in_force: str,
        limit_price: float | None,
        client_order_id: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "symbol": symbol.strip().upper(),
            "side": side,
            "type": order_type,
            "qty": str(quantity),
            "time_in_force": (
                time_in_force
            ),
        }

        if limit_price is not None:
            payload["limit_price"] = str(
                limit_price
            )

        if client_order_id:
            payload["client_order_id"] = (
                client_order_id
            )

        return self._request(
            method="POST",
            path="/v2/orders",
            payload=payload,
        )

    def get_order(
        self,
        *,
        broker_order_id: str,
    ) -> dict[str, Any]:
        normalized_id = (
            broker_order_id.strip()
        )

        if not normalized_id:
            raise ValueError(
                "broker_order_id is required."
            )

        return self._request(
            method="GET",
            path=(
                "/v2/orders/"
                f"{normalized_id}"
            ),
        )

    def cancel_order(
        self,
        *,
        broker_order_id: str,
    ) -> None:
        normalized_id = (
            broker_order_id.strip()
        )

        if not normalized_id:
            raise ValueError(
                "broker_order_id is required."
            )

        self._request(
            method="DELETE",
            path=(
                "/v2/orders/"
                f"{normalized_id}"
            ),
            expect_body=False,
        )

    def _request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        expect_body: bool = True,
    ) -> dict[str, Any]:
        body: bytes | None = None

        headers = {
            "APCA-API-KEY-ID": (
                self._api_key
            ),
            "APCA-API-SECRET-KEY": (
                self._secret_key
            ),
            "Accept": "application/json",
        }

        if payload is not None:
            body = json.dumps(
                payload
            ).encode("utf-8")

            headers["Content-Type"] = (
                "application/json"
            )

        request = Request(
            url=(
                f"{self._base_url}{path}"
            ),
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urlopen(
                request,
                timeout=(
                    self._timeout_seconds
                ),
            ) as response:
                response_body = (
                    response.read()
                )

        except HTTPError as error:
            raw_error = error.read().decode(
                "utf-8",
                errors="replace",
            )

            if error.code == 401:
                raise (
                    AlpacaAuthenticationError(
                        "Alpaca authentication "
                        "failed."
                    )
                ) from error

            raise AlpacaApiError(
                "Alpaca request failed. "
                f"status={error.code}, "
                f"body={raw_error}"
            ) from error

        except URLError as error:
            raise AlpacaApiError(
                "Could not connect to "
                "Alpaca."
            ) from error

        if not expect_body:
            return {}

        if not response_body:
            return {}

        try:
            parsed = json.loads(
                response_body.decode(
                    "utf-8"
                )
            )

        except json.JSONDecodeError as error:
            raise AlpacaApiError(
                "Alpaca returned invalid "
                "JSON."
            ) from error

        if not isinstance(parsed, dict):
            raise AlpacaApiError(
                "Unexpected Alpaca response."
            )

        return parsed