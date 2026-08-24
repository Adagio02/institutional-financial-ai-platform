from __future__ import annotations

import json
from typing import Any
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.parse import (
    quote,
    urlencode,
)
from urllib.request import (
    Request,
    urlopen,
)


ALPACA_PAPER_BASE_URL = (
    "https://paper-api.alpaca.markets"
)


class AlpacaApiError(
    RuntimeError
):
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
        self._api_key = (
            api_key.strip()
        )

        self._secret_key = (
            secret_key.strip()
        )

        self._base_url = (
            base_url
            .strip()
            .rstrip("/")
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
                "Only the Alpaca paper "
                "endpoint is permitted."
            )

        if (
            self._timeout_seconds
            <= 0
        ):
            raise ValueError(
                "timeout_seconds must "
                "be greater than zero."
            )

    @property
    def base_url(
        self,
    ) -> str:
        return self._base_url

    def get_account(
        self,
    ) -> dict[str, Any]:
        response = self._request(
            method="GET",
            path="/v2/account",
        )

        if not isinstance(
            response,
            dict,
        ):
            raise AlpacaApiError(
                "Unexpected Alpaca "
                "account response."
            )

        return response

    def get_asset(
        self,
        *,
        symbol: str,
    ) -> dict[str, Any]:
        normalized = (
            symbol
            .strip()
            .upper()
        )

        if not normalized:
            raise ValueError(
                "symbol is required."
            )

        encoded_symbol = quote(
            normalized,
            safe="",
        )

        response = self._request(
            method="GET",
            path=(
                f"/v2/assets/"
                f"{encoded_symbol}"
            ),
        )

        if not isinstance(
            response,
            dict,
        ):
            raise AlpacaApiError(
                "Unexpected Alpaca "
                "asset response."
            )

        return response

    def get_clock(
        self,
    ) -> dict[str, Any]:
        response = self._request(
            method="GET",
            path="/v2/clock",
        )

        if not isinstance(
            response,
            dict,
        ):
            raise AlpacaApiError(
                "Unexpected Alpaca "
                "clock response."
            )

        return response

    def submit_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        time_in_force: str,
        limit_price: float | None,
        client_order_id: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "symbol": (
                symbol
                .strip()
                .upper()
            ),
            "side": side,
            "type": order_type,
            "qty": str(
                quantity
            ),
            "time_in_force": (
                time_in_force
            ),
            "client_order_id": (
                client_order_id
            ),
        }

        if limit_price is not None:
            payload[
                "limit_price"
            ] = str(
                limit_price
            )

        response = self._request(
            method="POST",
            path="/v2/orders",
            payload=payload,
        )

        if not isinstance(
            response,
            dict,
        ):
            raise AlpacaApiError(
                "Unexpected Alpaca "
                "order response."
            )

        return response

    def get_order(
        self,
        *,
        broker_order_id: str,
    ) -> dict[str, Any]:
        normalized = (
            broker_order_id
            .strip()
        )

        if not normalized:
            raise ValueError(
                "broker_order_id is required."
            )

        response = self._request(
            method="GET",
            path=(
                f"/v2/orders/"
                f"{normalized}"
            ),
        )

        if not isinstance(
            response,
            dict,
        ):
            raise AlpacaApiError(
                "Unexpected Alpaca "
                "order response."
            )

        return response

    def get_order_by_client_order_id(
        self,
        *,
        client_order_id: str,
    ) -> dict[str, Any]:
        normalized = (
            client_order_id
            .strip()
        )

        if not normalized:
            raise ValueError(
                "client_order_id is required."
            )

        query = urlencode(
            {
                "client_order_id": (
                    normalized
                )
            }
        )

        response = self._request(
            method="GET",
            path=(
                "/v2/orders:"
                "by_client_order_id"
                f"?{query}"
            ),
        )

        if not isinstance(
            response,
            dict,
        ):
            raise AlpacaApiError(
                "Unexpected Alpaca "
                "order response."
            )

        return response

    def list_orders(
        self,
        *,
        status: str = "all",
        limit: int = 500,
        direction: str = "desc",
        nested: bool = False,
    ) -> list[
        dict[str, Any]
    ]:
        normalized_status = (
            status
            .strip()
            .lower()
        )

        if normalized_status not in {
            "open",
            "closed",
            "all",
        }:
            raise ValueError(
                "status must be "
                "'open', 'closed', "
                "or 'all'."
            )

        if not (
            1
            <= limit
            <= 500
        ):
            raise ValueError(
                "limit must be between "
                "1 and 500."
            )

        normalized_direction = (
            direction
            .strip()
            .lower()
        )

        if normalized_direction not in {
            "asc",
            "desc",
        }:
            raise ValueError(
                "direction must be "
                "'asc' or 'desc'."
            )

        query = urlencode(
            {
                "status": (
                    normalized_status
                ),
                "limit": limit,
                "direction": (
                    normalized_direction
                ),
                "nested": (
                    "true"
                    if nested
                    else "false"
                ),
            }
        )

        response = self._request(
            method="GET",
            path=(
                f"/v2/orders?{query}"
            ),
        )

        if not isinstance(
            response,
            list,
        ):
            raise AlpacaApiError(
                "Unexpected Alpaca "
                "order-list response."
            )

        orders: list[
            dict[str, Any]
        ] = []

        for item in response:
            if not isinstance(
                item,
                dict,
            ):
                raise AlpacaApiError(
                    "Alpaca order list "
                    "contains an invalid item."
                )

            orders.append(
                item
            )

        return orders

    def cancel_order(
        self,
        *,
        broker_order_id: str,
    ) -> None:
        normalized = (
            broker_order_id
            .strip()
        )

        if not normalized:
            raise ValueError(
                "broker_order_id is required."
            )

        self._request(
            method="DELETE",
            path=(
                f"/v2/orders/"
                f"{normalized}"
            ),
            expect_body=False,
        )

    def _request(
        self,
        *,
        method: str,
        path: str,
        payload: (
            dict[str, Any]
            | None
        ) = None,
        expect_body: bool = True,
    ) -> Any:
        body: bytes | None = None

        headers = {
            "APCA-API-KEY-ID": (
                self._api_key
            ),
            "APCA-API-SECRET-KEY": (
                self._secret_key
            ),
            "Accept": (
                "application/json"
            ),
        }

        if payload is not None:
            body = json.dumps(
                payload
            ).encode(
                "utf-8"
            )

            headers[
                "Content-Type"
            ] = (
                "application/json"
            )

        request = Request(
            url=(
                f"{self._base_url}"
                f"{path}"
            ),
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urlopen(
                request,
                timeout=(
                    self
                    ._timeout_seconds
                ),
            ) as response:
                raw = (
                    response.read()
                )

        except HTTPError as error:
            raw_error = (
                error
                .read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            if error.code in {
                401,
                403,
            }:
                raise (
                    AlpacaAuthenticationError(
                        "Alpaca authentication "
                        "or authorization failed."
                    )
                ) from error

            raise AlpacaApiError(
                "Alpaca request failed. "
                f"status={error.code}, "
                f"body={raw_error}"
            ) from error

        except URLError as error:
            raise AlpacaApiError(
                "Could not connect "
                "to Alpaca."
            ) from error

        if not expect_body:
            return {}

        if not raw:
            return {}

        try:
            return json.loads(
                raw.decode(
                    "utf-8"
                )
            )

        except json.JSONDecodeError as error:
            raise AlpacaApiError(
                "Alpaca returned "
                "invalid JSON."
            ) from error