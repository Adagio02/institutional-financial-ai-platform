"""python -m research_kit <command>  (run from the project root, virtual environment active)"""
from __future__ import annotations

import argparse
import sys

from . import registry


def main() -> int:
    p = argparse.ArgumentParser(prog="python -m research_kit", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("register", help="pre-register a hypothesis spec (JSON) before testing it")
    r.add_argument("spec")
    sub.add_parser("list", help="show every registered hypothesis and its status")
    b = sub.add_parser("build-events", help="download SEC earnings and insider data; build model_panel_v2")
    b.add_argument("--refresh-days", type=float, default=None)
    b.add_argument("--skip-insiders", action="store_true")
    t = sub.add_parser("test", help="run the ONE historical test of a registered hypothesis")
    t.add_argument("id")
    t.add_argument("--force-reason", default=None, help="only if the earlier test was broken by a bug")
    f = sub.add_parser("freeze", help="freeze a strategy for forward (shadow) testing")
    f.add_argument("id")
    f.add_argument("--exploratory", action="store_true", help="watch a failed or untested idea; never promotable")
    s = sub.add_parser("shadow-run", help="refresh data and record new shadow portfolios (schedule weekly)")
    s.add_argument("--skip-refresh", action="store_true")
    sub.add_parser("shadow-report", help="score shadow portfolios on data after each freeze date")
    d = sub.add_parser("daily", help="after-close pipeline: update data, record, evaluate (schedule on weekdays)")
    d.add_argument("--force", action="store_true", help="rebuild even if no new trading day was found")
    d.add_argument("--min-symbols", type=int, default=None,
                   help="only if you built the panel with a non-default --min-symbols")
    a = p.parse_args()

    if a.command == "register":
        registry.register(a.spec)
    elif a.command == "list":
        registry.list_hypotheses()
    elif a.command == "build-events":
        from . import events
        events.build_sue(a.refresh_days)
        if not a.skip_insiders:
            events.build_insiders(start="2018-01-01")
        events.build_panel_v2()
    elif a.command == "test":
        from . import study
        spec = registry.require_testable(a.id, a.force_reason)
        result = study.run_study(spec)
        study.print_result(spec, result)
        path = study.save_result(spec, result)
        registry.append({"event": "tested", "id": a.id, "passed": result["passed"], "blocking": result["blocking"],
                         "metrics": result["metrics"], "ic_checks": result["ic_checks"],
                         "force_reason": a.force_reason, "timestamp": registry.now(),
                         "git_commit": registry.git_commit(), "result_file": str(path)})
        print(f"\nRecorded in {registry.REGISTRY}; full result in {path}")
    elif a.command == "freeze":
        from . import shadow
        shadow.freeze(a.id, a.exploratory)
    elif a.command == "shadow-run":
        from . import shadow
        shadow.run(a.skip_refresh)
    elif a.command == "shadow-report":
        from . import shadow
        shadow.report()
    elif a.command == "daily":
        from . import daily
        return daily.run_daily(force=a.force, min_symbols=a.min_symbols)
    return 0


if __name__ == "__main__":
    sys.exit(main())
