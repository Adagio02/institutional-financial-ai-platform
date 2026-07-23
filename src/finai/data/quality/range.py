"""Data-quality check: range."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


def run_check(*_: object, **__: object) -> CheckResult:
    return CheckResult(name="range", passed=True, detail="Implement dataset-specific thresholds.")
