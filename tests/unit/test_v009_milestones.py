from pathlib import Path

import pandas as pd

from finai.research.v56.v009_milestones import completed_rebalance_periods, qualified_dates, status_for


def test_completed_period_count_requires_future_horizon():
    assert completed_rebalance_periods(5) == 0
    assert completed_rebalance_periods(6) == 1
    assert completed_rebalance_periods(66) == 13
    assert completed_rebalance_periods(131) == 26
    assert completed_rebalance_periods(261) == 52


def test_status_does_not_unlock_v57():
    assert status_for(12) == ("collecting", 13)
    assert status_for(13) == ("provisional_shadow_champion", 26)
    assert status_for(26) == ("validated_shadow_monitoring", 52)
    assert status_for(52) == ("official_lock_ready", 52)


def test_qualified_dates_respects_start_and_breadth():
    frame = pd.DataFrame({
        "timestamp": ["2026-09-07"] * 3 + ["2026-09-08"] * 3 + ["2026-09-09"] * 2,
        "symbol": ["A", "B", "C", "A", "B", "C", "A", "B"],
    })
    protocol = {"prospective_lock_start": "2026-09-08T00:00:00+00:00"}
    dates = qualified_dates(frame, protocol, 3)
    assert [d.strftime("%Y-%m-%d") for d in dates] == ["2026-09-08"]
