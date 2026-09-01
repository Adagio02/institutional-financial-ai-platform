import pandas as pd

from finai.domain.learning.v44_research import (
    freeze_payload,
    research_configs,
    split_discovery_locked_final,
    verify_frozen_payload,
)


def test_v44_research_grid_has_expected_size() -> None:
    assert len(research_configs()) == 16


def test_v44_partitions_are_chronological_and_disjoint() -> None:
    frame = pd.DataFrame({"x": range(1000)})
    discovery, locked, final = split_discovery_locked_final(
        frame
    )
    assert discovery["x"].max() < locked["x"].min()
    assert locked["x"].max() < final["x"].min()


def test_frozen_payload_detects_mutation() -> None:
    frozen = freeze_payload({"model": "rf", "horizon": 15})
    assert verify_frozen_payload(frozen)
    frozen["candidate"]["horizon"] = 30
    assert not verify_frozen_payload(frozen)
