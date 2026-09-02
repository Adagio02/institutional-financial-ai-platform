"""Compatibility entry point: V4.8 now builds and audits the feature platform."""

from run_v48_feature_platform import result

assert result["version"] == "4.8"
