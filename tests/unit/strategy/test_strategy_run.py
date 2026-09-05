from uuid import uuid4

import pytest

from finai.application.services.strategy_run_service import (
    StrategySignal,
)
from finai.domain.execution.enums import (
    OrderSide,
)


def test_strategy_signal_preserves_values() -> None:
    model_id = uuid4()

    prediction_id = uuid4()

    signal = StrategySignal(
        symbol="AAPL",
        side=OrderSide.BUY,
        confidence=0.85,
        source_model_id=model_id,
        source_prediction_id=(prediction_id),
    )

    assert signal.symbol == "AAPL"

    assert signal.side == (OrderSide.BUY)

    assert signal.confidence == (pytest.approx(0.85))

    assert signal.source_model_id == (model_id)

    assert signal.source_prediction_id == prediction_id


def test_strategy_signal_can_omit_sources() -> None:
    signal = StrategySignal(
        symbol="BTCUSD",
        side=OrderSide.SELL,
        confidence=0.70,
    )

    assert signal.source_model_id is None

    assert signal.source_prediction_id is None
