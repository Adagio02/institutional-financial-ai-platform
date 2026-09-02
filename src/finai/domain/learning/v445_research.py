from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FocusedCandidate:
    config_key: str
    model_name: str
    horizon_bars: int
    edge_bps: float
    source_net_return: float
    source_trade_count: int
    source_positive_fold_fraction: float

    @property
    def key(self) -> str:
        return f"{self.config_key}__{self.model_name}"


def parse_config_key(
    config_key: str,
) -> tuple[int, float]:
    """
    Parse keys produced by V4.4, for example:
        h60_e5p0_expanding
        h5_e10p0_expanding
    """
    parts = config_key.split("_")
    if len(parts) < 2:
        raise ValueError(
            f"Unrecognized V4.4 config key: {config_key}"
        )

    horizon_token = parts[0]
    edge_token = parts[1]

    if not horizon_token.startswith("h"):
        raise ValueError(
            f"Unrecognized horizon token: {horizon_token}"
        )
    if not edge_token.startswith("e"):
        raise ValueError(
            f"Unrecognized edge token: {edge_token}"
        )

    horizon = int(horizon_token[1:])
    edge = float(
        edge_token[1:].replace("p", ".")
    )
    return horizon, edge


def select_focused_candidates(
    leaderboard: list[dict[str, Any]],
    *,
    maximum_candidates: int = 8,
    minimum_trades: int = 50,
) -> list[FocusedCandidate]:
    """
    Select promising candidates using DISCOVERY results only.

    This does not make a candidate eligible for promotion. It only
    narrows the next research experiment to candidates that:
      - actually traded,
      - had positive aggregate discovery return,
      - had enough observations to be worth investigating.

    The candidates remain subject to all later stability and
    multiple-testing gates.
    """
    ranked = sorted(
        leaderboard,
        key=lambda item: (
            float(item.get("net_return", 0.0)),
            float(
                item.get(
                    "positive_fold_fraction",
                    0.0,
                )
            ),
            int(item.get("trade_count", 0)),
        ),
        reverse=True,
    )

    selected: list[FocusedCandidate] = []

    for item in ranked:
        net_return = float(
            item.get("net_return", 0.0)
        )
        trade_count = int(
            item.get("trade_count", 0)
        )

        if net_return <= 0.0:
            continue
        if trade_count < minimum_trades:
            continue

        config_key = str(
            item["config_key"]
        )
        horizon, edge = parse_config_key(
            config_key
        )

        selected.append(
            FocusedCandidate(
                config_key=config_key,
                model_name=str(
                    item["model_name"]
                ),
                horizon_bars=horizon,
                edge_bps=edge,
                source_net_return=net_return,
                source_trade_count=trade_count,
                source_positive_fold_fraction=float(
                    item.get(
                        "positive_fold_fraction",
                        0.0,
                    )
                ),
            )
        )

        if (
            len(selected)
            >= maximum_candidates
        ):
            break

    return selected


def candidate_failure_reasons(
    item: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []

    if float(
        item.get("net_return", 0.0)
    ) <= 0.0:
        reasons.append(
            "non_positive_net_return"
        )

    if float(
        item.get(
            "penalized_mean_fold_return",
            0.0,
        )
    ) <= 0.0:
        reasons.append(
            "non_positive_selection_adjusted_return"
        )

    if float(
        item.get(
            "positive_fold_fraction",
            0.0,
        )
    ) < 0.50:
        reasons.append(
            "insufficient_positive_fold_fraction"
        )

    return reasons
