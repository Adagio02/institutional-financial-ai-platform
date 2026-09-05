"""Data-quality check: feature_drift."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


def run_check(*_: object, **__: object) -> CheckResult:
    return CheckResult(
        name="feature_drift", passed=True, detail="Implement dataset-specific thresholds."
    )
