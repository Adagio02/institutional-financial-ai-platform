import json

import pytest

from finai.infrastructure.execution.alpaca_trade_update_stream import (
    AlpacaTradeStreamError,
    decode_stream_frame,
)


def test_decode_text_frame() -> None:
    frame = json.dumps(
        {
            "stream": (
                "trade_updates"
            ),
            "data": {
                "event": "fill"
            },
        }
    )

    result = (
        decode_stream_frame(
            frame
        )
    )

    assert (
        result["stream"]
        == "trade_updates"
    )


def test_decode_binary_frame() -> None:
    frame = json.dumps(
        {
            "stream": (
                "trade_updates"
            ),
            "data": {
                "event": (
                    "partial_fill"
                )
            },
        }
    ).encode("utf-8")

    result = (
        decode_stream_frame(
            frame
        )
    )

    assert (
        result["data"]["event"]
        == "partial_fill"
    )


def test_invalid_json_is_rejected() -> None:
    with pytest.raises(
        AlpacaTradeStreamError
    ):
        decode_stream_frame(
            b"not-json"
        )


def test_non_object_is_rejected() -> None:
    with pytest.raises(
        AlpacaTradeStreamError
    ):
        decode_stream_frame(
            b"[]"
        )