"""Compatibility entry point; V4.8.1 creates neutral targets, not a shortlist."""

from run_v481_neutral_targets import result

assert result["version"] == "4.8.1"
