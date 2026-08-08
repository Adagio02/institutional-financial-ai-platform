def validate_confidence_level(
    confidence: float,
) -> None:
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between zero and one.")
