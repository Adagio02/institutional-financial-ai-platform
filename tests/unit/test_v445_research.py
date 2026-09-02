from finai.domain.learning.v445_research import (
    candidate_failure_reasons,
    parse_config_key,
    select_focused_candidates,
)


def test_parse_config_key() -> None:
    assert parse_config_key(
        "h60_e5p0_expanding"
    ) == (60, 5.0)

    assert parse_config_key(
        "h5_e10p0_expanding"
    ) == (5, 10.0)


def test_select_focused_candidates() -> None:
    rows = [
        {
            "config_key": (
                "h60_e5p0_expanding"
            ),
            "model_name": "rf",
            "net_return": 0.04,
            "trade_count": 100,
            "positive_fold_fraction": 0.4,
        },
        {
            "config_key": (
                "h5_e5p0_expanding"
            ),
            "model_name": "lr",
            "net_return": -0.01,
            "trade_count": 200,
            "positive_fold_fraction": 0.8,
        },
    ]

    selected = (
        select_focused_candidates(
            rows,
            maximum_candidates=8,
            minimum_trades=50,
        )
    )

    assert len(selected) == 1
    assert (
        selected[0].model_name
        == "rf"
    )


def test_failure_reasons() -> None:
    reasons = candidate_failure_reasons(
        {
            "net_return": 0.05,
            "penalized_mean_fold_return": (
                -0.01
            ),
            "positive_fold_fraction": 0.4,
        }
    )

    assert (
        "non_positive_selection_adjusted_return"
        in reasons
    )
    assert (
        "insufficient_positive_fold_fraction"
        in reasons
    )
