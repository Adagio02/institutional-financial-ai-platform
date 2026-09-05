from finai.application.services.v35_inference_service import (
    determine_signal,
)


def test_long_signal() -> None:
    assert (
        determine_signal(
            predicted_class=1,
            confidence=0.70,
            minimum_confidence=0.55,
        )
        == "long"
    )


def test_short_signal() -> None:
    assert (
        determine_signal(
            predicted_class=-1,
            confidence=0.70,
            minimum_confidence=0.55,
        )
        == "short"
    )


def test_neutral_class_is_hold() -> None:
    assert (
        determine_signal(
            predicted_class=0,
            confidence=0.90,
            minimum_confidence=0.55,
        )
        == "hold"
    )


def test_low_confidence_is_hold() -> None:
    assert (
        determine_signal(
            predicted_class=1,
            confidence=0.50,
            minimum_confidence=0.55,
        )
        == "hold"
    )