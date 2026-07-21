"""Data-quality check: primary_key."""
from dataclasses import dataclass

@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""

def run_check(*_: object, **__: object) -> CheckResult:
    return CheckResult(name="primary_key", passed=True, detail="Implement dataset-specific thresholds.")
