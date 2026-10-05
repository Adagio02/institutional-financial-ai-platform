"""Apply the three V5.6 fixes without git.

Run from the project root:
    python apply_v56_fixes.py

- Works with Windows (CRLF) or Unix (LF) line endings and keeps each file's style.
- Safe to run more than once: steps that are already applied are skipped.
- Saves a .bak copy of every file before changing it.
- Changes nothing if any target cannot be found; it reports what to check instead.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

V56 = Path("src/finai/research/v56")
FILES = {
    "core": V56 / "core.py",
    "portfolio": V56 / "portfolio.py",
    "pipeline": V56 / "pipeline.py",
    "pipeline_v007": V56 / "pipeline_v007.py",
    "pipeline_v008": V56 / "pipeline_v008.py",
    "script": Path("scripts/run_v56_research.py"),
}

CORE_FIELDS = """    rebalance_every: int = 5
    beta_exposure_limit: float = 0.10
    rebalance_turnover_limit: float = 0.25
"""
CORE_POST_INIT = """
    def __post_init__(self) -> None:
        if self.horizon < 1 or self.rebalance_every < 1:
            raise ValueError("horizon and rebalance_every must be at least 1")
        if self.rebalance_every < self.horizon:
            raise ValueError(
                f"rebalance_every ({self.rebalance_every}) must be >= horizon ({self.horizon}); "
                "otherwise each ledger row books an overlapping multi-day forward return"
            )
"""
METRICS_HEADER = '''def metrics(ledger: pd.DataFrame, rebalance_every: int | None = None) -> dict:
    """Ledger metrics. Each row spans `rebalance_every` daily periods, so the
    Sharpe ratio is annualized with 252 / rebalance_every periods per year."""
    if rebalance_every is None:
        rebalance_every = int(ledger.attrs.get("rebalance_every", 1))
    periods_per_year = 252.0 / max(1, int(rebalance_every))
'''
TEST_FILE = '''import numpy as np
import pandas as pd
import pytest

from finai.research.v56.core import Config
from finai.research.v56.portfolio import metrics


def test_config_accepts_v007_v008_risk_fields():
    cfg = Config(beta_exposure_limit=0.10, rebalance_turnover_limit=0.25)
    assert cfg.beta_exposure_limit == 0.10 and cfg.rebalance_turnover_limit == 0.25


def test_config_rejects_overlapping_forward_returns():
    with pytest.raises(ValueError, match="rebalance_every"):
        Config(horizon=5, rebalance_every=1)
    Config(horizon=5, rebalance_every=5)  # non-overlapping is allowed


def test_sharpe_is_annualized_by_rebalance_period():
    rng = np.random.default_rng(0)
    ledger = pd.DataFrame({"net_return": rng.normal(0.001, 0.01, 200), "turnover": 0.1, "cost": 0.0})
    daily = metrics(ledger, rebalance_every=1)["annualized_sharpe"]
    weekly = metrics(ledger, rebalance_every=5)["annualized_sharpe"]
    assert np.isclose(daily / weekly, np.sqrt(5))
'''


class Problem(Exception):
    pass


def read(path: Path) -> tuple[str, bool]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        raw = f.read()
    return raw.replace("\r\n", "\n"), "\r\n" in raw


def fix_core(text: str) -> str:
    if "class Config" not in text:
        raise Problem("could not find 'class Config'")
    if "beta_exposure_limit" not in text:
        text, n = re.subn(r"^    rebalance_every: int = \d+[ \t]*\n", CORE_FIELDS, text, flags=re.M)
        if n != 1:
            raise Problem("could not find the 'rebalance_every: int = ...' line in Config")
    else:
        if "rebalance_turnover_limit" not in text:
            raise Problem("Config has beta_exposure_limit but not rebalance_turnover_limit; add it by hand")
        text = re.sub(r"^(    rebalance_every: int = )1([ \t]*)$", r"\g<1>5\2", text, flags=re.M)
    if "def __post_init__" not in text:
        # Insert after the last field of the Config dataclass (before the next top-level def).
        match = re.search(r"(class Config:\n(?:    .*\n|\n)*?)(?=\n\S|\n\n\S)", text)
        if not match:
            raise Problem("could not find the end of the Config class")
        text = text[: match.end()].rstrip("\n") + "\n" + CORE_POST_INIT + text[match.end():]
    return text


LOCAL_ANNUAL_PERIODS = re.compile(
    r'^    annual_periods = 252\.0 / max\(1, int\(getattr\(ledger, "attrs", \{\}\)\.get\("rebalance_every", 1\)\)\)[ \t]*\n',
    flags=re.M,
)
LOCAL_ANNUAL_PERIODS_NEW = (
    "    if rebalance_every is None:\n"
    '        rebalance_every = int(getattr(ledger, "attrs", {}).get("rebalance_every", 1))\n'
    "    annual_periods = 252.0 / max(1, int(rebalance_every))\n"
)


def fix_portfolio(text: str) -> str:
    already = re.search(r"^def metrics\(ledger: pd\.DataFrame, rebalance_every: int \| None = None\)", text, flags=re.M)
    if not already:
        if LOCAL_ANNUAL_PERIODS.search(text):
            # Local variant: Sharpe already annualized from ledger.attrs. Add an explicit
            # rebalance_every argument so pipelines can pass it directly.
            text, n = re.subn(r"^def metrics\(ledger: pd\.DataFrame\) -> dict:",
                              "def metrics(ledger: pd.DataFrame, rebalance_every: int | None = None) -> dict:",
                              text, flags=re.M)
            if n != 1:
                raise Problem("could not find 'def metrics(ledger: pd.DataFrame) -> dict:'")
            text = LOCAL_ANNUAL_PERIODS.sub(LOCAL_ANNUAL_PERIODS_NEW, text, count=1)
        else:
            text, n = re.subn(r"^def metrics\(ledger: pd\.DataFrame\) -> dict:[ \t]*\n", METRICS_HEADER, text, flags=re.M)
            if n != 1:
                raise Problem("could not find 'def metrics(ledger: pd.DataFrame) -> dict:'")
            text, n = re.subn(r"np\.sqrt\(252\)", "np.sqrt(periods_per_year)", text)
            if n != 1:
                raise Problem(f"expected exactly one 'np.sqrt(252)' in portfolio.py, found {n}")
    # Optional: also tag the base simulate() ledger. Pipelines pass the value explicitly,
    # so skipping this when the line has a different shape is harmless.
    old = "    return pd.DataFrame(rows), pd.DataFrame(positions)\n"
    if 'attrs["rebalance_every"]' not in text and text.count(old) == 1:
        text = text.replace(old, "    ledger = pd.DataFrame(rows)\n"
                                 '    ledger.attrs["rebalance_every"] = cfg.rebalance_every\n'
                                 "    return ledger, pd.DataFrame(positions)\n")
    return text


def fix_pipeline(text: str) -> str:
    if re.search(r"metrics\(ledger,\s*cfg\.rebalance_every\)", text):
        return text
    text, n = re.subn(r"metrics\(ledger\)", "metrics(ledger, cfg.rebalance_every)", text)
    if n != 1:
        raise Problem(f"expected one 'metrics(ledger)' call, found {n}")
    return text


def fix_script(text: str) -> str:
    if "--rebalance-every" in text:
        return text
    arg = ('    parser.add_argument("--rebalance-every", type=int, default=None,\n'
           '                        help="periods between rebalances; defaults to --horizon (non-overlapping)")\n')
    text, n = re.subn(r"^(    args = parser\.parse_args\(\)[ \t]*\n)", arg + r"\1", text, flags=re.M)
    if n != 1:
        raise Problem("could not find 'args = parser.parse_args()'")
    cfg_new = ("    rebalance_every = args.rebalance_every if args.rebalance_every is not None else args.horizon\n"
               "    cfg = Config(min_symbols=args.min_symbols, cost_bps=args.cost_bps, horizon=args.horizon,\n"
               "                 rebalance_every=rebalance_every)\n")
    text, n = re.subn(
        r"^    cfg = Config\(min_symbols=args\.min_symbols, cost_bps=args\.cost_bps, horizon=args\.horizon\)[ \t]*\n",
        cfg_new, text, flags=re.M)
    if n != 1:
        raise Problem("could not find the 'cfg = Config(min_symbols=..., horizon=args.horizon)' line")
    return text


FIXERS = {
    "core": fix_core, "portfolio": fix_portfolio, "pipeline": fix_pipeline,
    "pipeline_v007": fix_pipeline, "pipeline_v008": fix_pipeline, "script": fix_script,
}


def main() -> int:
    missing = [str(p) for p in FILES.values() if not p.exists()]
    if missing:
        print("Run this from the project root. Missing:", *missing, sep="\n  ")
        return 1

    planned, problems = {}, []
    for key, path in FILES.items():
        text, crlf = read(path)
        try:
            new = FIXERS[key](text)
        except Problem as exc:
            problems.append(f"{path}: {exc}")
            continue
        if new != text:
            planned[path] = (new, crlf)

    if problems:
        print("No files were changed. These targets could not be found:")
        for item in problems:
            print("  -", item)
        print("Paste this output into the chat for manual edits.")
        return 1

    for path, (new, crlf) in planned.items():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new.replace("\n", "\r\n") if crlf else new)
        print("updated  ", path)
    for path in FILES.values():
        if path not in planned:
            print("unchanged", path, "(already applied)")

    test_path = Path("tests/unit/test_v56_fixes.py")
    if not test_path.exists():
        test_path.write_text(TEST_FILE, encoding="utf-8")
        print("created  ", test_path)
    print("\nDone. Backups saved as *.bak next to each changed file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
