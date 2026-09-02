"""Compatibility exports for the corrected V4.8 research platform."""

from finai.domain.learning.v48_features import (
    V48_FEATURE_COLUMNS,
    V48_RANK_FEATURE_COLUMNS,
    V48_RAW_FEATURE_COLUMNS,
    V48_ZSCORE_FEATURE_COLUMNS,
    build_cross_sectional_feature_platform,
    feature_platform_summary,
)

__all__ = [
    "V48_FEATURE_COLUMNS",
    "V48_RANK_FEATURE_COLUMNS",
    "V48_RAW_FEATURE_COLUMNS",
    "V48_ZSCORE_FEATURE_COLUMNS",
    "build_cross_sectional_feature_platform",
    "feature_platform_summary",
]
