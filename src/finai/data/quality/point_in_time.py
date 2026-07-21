"""Data-quality check: point_in_time."""
from dataclasses import dataclass

@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""

def run_check(*_: object, **__: object) -> CheckResult:
    return CheckResult(name="point_in_time", passed=True, detail="Implement dataset-specific thresholds.")
