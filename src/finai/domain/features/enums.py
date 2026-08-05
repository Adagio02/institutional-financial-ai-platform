from enum import StrEnum


class FeatureName(StrEnum):
    SIMPLE_RETURN = "simple_return"
    LOG_RETURN = "log_return"
    ROLLING_MEAN = "rolling_mean"
    ROLLING_STANDARD_DEVIATION = "rolling_standard_deviation"
    ROLLING_VOLATILITY = "rolling_volatility"
    MOMENTUM = "momentum"
    RELATIVE_STRENGTH_INDEX = "relative_strength_index"
    MACD = "macd"
    MACD_SIGNAL = "macd_signal"
    MACD_HISTOGRAM = "macd_histogram"
    AVERAGE_TRUE_RANGE = "average_true_range"
    VOLUME_CHANGE = "volume_change"
    DRAWDOWN = "drawdown"


class MissingValuePolicy(StrEnum):
    DROP = "drop"
    KEEP = "keep"
    FORWARD_FILL = "forward_fill"


class DatasetStatus(StrEnum):
    PENDING = "pending"
    BUILDING = "building"
    COMPLETED = "completed"
    FAILED = "failed"
