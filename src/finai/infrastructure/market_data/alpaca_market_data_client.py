from __future__ import annotations

import json
import socket
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


ALPACA_DATA_BASE_URL = (
    "https://data.alpaca.markets"
)


class AlpacaMarketDataError(
    RuntimeError
):
    pass


class AlpacaMarketDataAuthenticationError(
    AlpacaMarketDataError
):
    pass


class AlpacaMarketDataTransportError(
    AlpacaMarketDataError
):
    pass


class AlpacaMarketDataClient:
    def __init__(
        self,
        *,
        api_key: str,
        secret_key: str,
        base_url: str,
        feed: str,
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

        self._feed = (
            feed
            .strip()
            .lower()
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
            != ALPACA_DATA_BASE_URL
        ):
            raise ValueError(
                "Unsupported Alpaca market "
                "data base URL."
            )

        if self._feed not in {
            "iex",
            "sip",
            "delayed_sip",
            "boats",
            "overnight",
            "otc",
        }:
            raise ValueError(
                "Unsupported Alpaca "
                "market-data feed."
            )

        if (
            self._timeout_seconds
            <= 0
        ):
            raise ValueError(
                "timeout_seconds must be "
                "greater than zero."
            )

    @property
    def feed(
        self,
    ) -> str:
        return self._feed

    def get_latest_quote(
        self,
        *,
        symbol: str,
    ) -> dict[str, Any]:
        normalized_symbol = (
            symbol
            .strip()
            .upper()
        )

        if not normalized_symbol:
            raise ValueError(
                "symbol cannot be blank."
            )

        encoded_symbol = quote(
            normalized_symbol,
            safe="",
        )

        query = urlencode(
            {
                "feed": (
                    self._feed
                )
            }
        )

        response = self._request(
            path=(
                f"/v2/stocks/"
                f"{encoded_symbol}"
                f"/quotes/latest?"
                f"{query}"
            )
        )

        if not isinstance(
            response,
            dict,
        ):
            raise AlpacaMarketDataError(
                "Unexpected Alpaca "
                "latest-quote response."
            )

        quote_data = response.get(
            "quote"
        )

        if not isinstance(
            quote_data,
            dict,
        ):
            raise AlpacaMarketDataError(
                "Alpaca latest-quote "
                "response contains no quote."
            )

        return quote_data

    def _request(
        self,
        *,
        path: str,
    ) -> Any:
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

        request = Request(
            url=(
                f"{self._base_url}"
                f"{path}"
            ),
            headers=headers,
            method="GET",
        )

        try:
            with urlopen(
                request,
                timeout=(
                    self
                    ._timeout_seconds
                ),
            ) as response:
                raw = response.read()

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
                    AlpacaMarketDataAuthenticationError(
                        "Alpaca market-data "
                        "authentication or "
                        "authorization failed."
                    )
                ) from error

            raise AlpacaMarketDataError(
                "Alpaca market-data "
                "request failed. "
                f"status={error.code}, "
                f"body={raw_error}"
            ) from error

        except (
            URLError,
            TimeoutError,
            socket.timeout,
        ) as error:
            raise (
                AlpacaMarketDataTransportError(
                    "Could not complete "
                    "the Alpaca market-data "
                    "request."
                )
            ) from error

        if not raw:
            raise AlpacaMarketDataError(
                "Alpaca market-data "
                "response was empty."
            )

        try:
            return json.loads(
                raw.decode(
                    "utf-8"
                )
            )

        except json.JSONDecodeError as error:
            raise AlpacaMarketDataError(
                "Alpaca market-data API "
                "returned invalid JSON."
            ) from error