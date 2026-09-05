from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from finai.domain.features.enums import FeatureName


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    name: FeatureName
    parameters: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FeatureObservation:
    instrument_id: UUID
    symbol: str
    timestamp: datetime
    feature_name: FeatureName
    feature_value: Decimal | None
