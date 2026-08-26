from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(
    frozen=True,
    slots=True,
)
class V35Prediction:
    symbol: str
    interval: str

    timestamp: datetime

    predicted_class: int

    short_probability: float
    neutral_probability: float
    long_probability: float

    confidence: float

    signal: str

    model_name: str
    model_path: str

    market_data_provider: str


@dataclass(
    frozen=True,
    slots=True,
)
class V35ShadowSignal:
    symbol: str
    timestamp: datetime

    signal: str
    confidence: float

    reference_price: float

    model_name: str

    executable: bool
    reason: str