"""Compatibility entry point; V4.8.3 performs IC analysis, not locked validation."""

from run_v483_signal_ic_analysis import result

assert result["version"] == "4.8.3"
