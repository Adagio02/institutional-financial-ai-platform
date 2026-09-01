from finai.domain.learning.v44_research import (
    selection_penalized_fold_score,
)


def test_selection_penalty_is_nonnegative() -> None:
    result = selection_penalized_fold_score(
        [0.01, 0.02, 0.00, 0.01, 0.015],
        trial_count=64,
    )
    assert result["selection_penalty"] >= 0.0
    assert (
        result["penalized_mean_fold_return"]
        <= result["mean_fold_return"]
    )
