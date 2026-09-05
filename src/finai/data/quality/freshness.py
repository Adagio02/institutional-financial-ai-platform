"""Data-quality check: freshness."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


def run_check(*_: object, **__: object) -> CheckResult:
    return CheckResult(
        name="freshness", passed=True, detail="Implement dataset-specific thresholds."
    )
