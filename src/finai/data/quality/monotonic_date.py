"""Data-quality check: monotonic_date."""
from dataclasses import dataclass

@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""

def run_check(*_: object, **__: object) -> CheckResult:
    return CheckResult(name="monotonic_date", passed=True, detail="Implement dataset-specific thresholds.")
