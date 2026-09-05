from finai.application.services.v432_learning_service import V432LearningService


def test_v432_separates_calibration_and_global_trade_requirements() -> None:
    assert V432LearningService.DIRECTIONAL_CALIBRATION_MINIMUM_TRADES == 20
    assert V432LearningService.NEIGHBOR_MINIMUM_TRADES == 10
    assert (
        V432LearningService.NEIGHBOR_MINIMUM_TRADES
        < V432LearningService.DIRECTIONAL_CALIBRATION_MINIMUM_TRADES
    )
