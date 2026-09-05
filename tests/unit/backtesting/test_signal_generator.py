from finai.domain.backtesting.enums import (
    SignalDirection,
)
from finai.infrastructure.backtesting.signal_generator import (
    generate_classification_signal,
)


def test_high_probability_generates_long() -> None:
    signal = generate_classification_signal(
        probability=0.80,
        long_threshold=0.60,
        short_threshold=0.40,
        allow_short=True,
    )

    assert signal == SignalDirection.LONG


def test_low_probability_generates_short() -> None:
    signal = generate_classification_signal(
        probability=0.20,
        long_threshold=0.60,
        short_threshold=0.40,
        allow_short=True,
    )

    assert signal == SignalDirection.SHORT


def test_middle_probability_is_flat() -> None:
    signal = generate_classification_signal(
        probability=0.50,
        long_threshold=0.60,
        short_threshold=0.40,
        allow_short=True,
    )

    assert signal == SignalDirection.FLAT


def test_short_signal_disabled() -> None:
    signal = generate_classification_signal(
        probability=0.20,
        long_threshold=0.60,
        short_threshold=0.40,
        allow_short=False,
    )

    assert signal == SignalDirection.FLAT
