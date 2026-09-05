from __future__ import annotations

import json
from collections.abc import (
    AsyncIterator,
)
from typing import Any

from websockets.asyncio.client import (
    ClientConnection,
    connect,
)


ALPACA_PAPER_STREAM_URL = (
    "wss://paper-api.alpaca.markets/stream"
)


class AlpacaTradeStreamError(
    RuntimeError
):
    pass


class AlpacaTradeStreamAuthenticationError(
    AlpacaTradeStreamError
):
    pass


def decode_stream_frame(
    frame: str | bytes,
) -> dict[str, Any]:
    if isinstance(
        frame,
        bytes,
    ):
        raw = frame.decode(
            "utf-8",
            errors="strict",
        )

    else:
        raw = frame

    try:
        payload = json.loads(
            raw
        )

    except json.JSONDecodeError as error:
        raise AlpacaTradeStreamError(
            "Alpaca trade stream returned "
            "invalid JSON."
        ) from error

    if not isinstance(
        payload,
        dict,
    ):
        raise AlpacaTradeStreamError(
            "Unexpected Alpaca trade "
            "stream message type."
        )

    return payload


class AlpacaTradeUpdateStream:
    def __init__(
        self,
        *,
        api_key: str,
        secret_key: str,
        stream_url: str,
        open_timeout_seconds: float,
    ) -> None:
        self._api_key = (
            api_key.strip()
        )

        self._secret_key = (
            secret_key.strip()
        )

        self._stream_url = (
            stream_url
            .strip()
            .rstrip("/")
        )

        self._open_timeout_seconds = (
            open_timeout_seconds
        )

        if not self._api_key:
            raise ValueError(
                "Alpaca API key is "
                "required."
            )

        if not self._secret_key:
            raise ValueError(
                "Alpaca secret key is "
                "required."
            )

        if (
            self._stream_url
            != ALPACA_PAPER_STREAM_URL
        ):
            raise ValueError(
                "Version 2.1 permits only "
                "the Alpaca paper trading "
                "WebSocket endpoint."
            )

        if (
            self._open_timeout_seconds
            <= 0
        ):
            raise ValueError(
                "open_timeout_seconds "
                "must be positive."
            )

    async def verify_connection(
        self,
    ) -> None:
        async with self._connect() as websocket:
            await self._authenticate(
                websocket
            )

            await self._listen(
                websocket
            )

    async def messages(
        self,
    ) -> AsyncIterator[
        dict[str, Any]
    ]:
        async with self._connect() as websocket:
            await self._authenticate(
                websocket
            )

            await self._listen(
                websocket
            )

            while True:
                frame = (
                    await websocket.recv()
                )

                message = (
                    decode_stream_frame(
                        frame
                    )
                )

                if (
                    message.get("stream")
                    != "trade_updates"
                ):
                    continue

                yield message

    def _connect(
        self,
    ):
        return connect(
            self._stream_url,
            open_timeout=(
                self
                ._open_timeout_seconds
            ),
            close_timeout=5.0,
            ping_interval=20.0,
            ping_timeout=20.0,
            max_size=2**20,
        )

    async def _authenticate(
        self,
        websocket: ClientConnection,
    ) -> None:
        await websocket.send(
            json.dumps(
                {
                    "action": "auth",
                    "key": self._api_key,
                    "secret": (
                        self._secret_key
                    ),
                }
            )
        )

        response = (
            decode_stream_frame(
                await websocket.recv()
            )
        )

        if (
            response.get("stream")
            != "authorization"
        ):
            raise (
                AlpacaTradeStreamAuthenticationError(
                    "Unexpected Alpaca "
                    "authorization response."
                )
            )

        data = response.get(
            "data"
        )

        if not isinstance(
            data,
            dict,
        ):
            raise (
                AlpacaTradeStreamAuthenticationError(
                    "Alpaca authorization "
                    "response contains no "
                    "data object."
                )
            )

        if (
            data.get("status")
            != "authorized"
        ):
            raise (
                AlpacaTradeStreamAuthenticationError(
                    "Alpaca trade-stream "
                    "authentication failed."
                )
            )

    async def _listen(
        self,
        websocket: ClientConnection,
    ) -> None:
        await websocket.send(
            json.dumps(
                {
                    "action": "listen",
                    "data": {
                        "streams": [
                            "trade_updates"
                        ]
                    },
                }
            )
        )

        response = (
            decode_stream_frame(
                await websocket.recv()
            )
        )

        if (
            response.get("stream")
            != "listening"
        ):
            raise AlpacaTradeStreamError(
                "Alpaca did not acknowledge "
                "the trade_updates stream."
            )

        data = response.get(
            "data"
        )

        if not isinstance(
            data,
            dict,
        ):
            raise AlpacaTradeStreamError(
                "Invalid Alpaca listening "
                "response."
            )

        streams = data.get(
            "streams"
        )

        if (
            not isinstance(
                streams,
                list,
            )
            or "trade_updates"
            not in streams
        ):
            raise AlpacaTradeStreamError(
                "Alpaca did not subscribe "
                "to trade_updates."
            )