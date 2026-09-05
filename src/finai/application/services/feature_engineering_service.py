from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pandas as pd
from sqlalchemy.orm import Session

from finai.domain.features.validation import (
    validate_feature_configuration,
    validate_feature_time_range,
)
from finai.domain.market_data.enums import BarInterval
from finai.infrastructure.database.repositories.feature_set_repository import (
    FeatureSetRepository,
)
from finai.infrastructure.database.repositories.feature_value_repository import (
    FeatureValueRepository,
)
from finai.infrastructure.database.repositories.instrument_repository import (
    InstrumentRepository,
)
from finai.infrastructure.database.repositories.market_bar_repository import (
    MarketBarRepository,
)
from finai.infrastructure.features.return_features import (
    calculate_log_return,
    calculate_momentum,
    calculate_simple_return,
    calculate_volume_change,
)
from finai.infrastructure.features.technical_indicators import (
    calculate_average_true_range,
    calculate_macd,
    calculate_relative_strength_index,
)
from finai.infrastructure.features.volatility_features import (
    calculate_drawdown,
    calculate_rolling_mean,
    calculate_rolling_standard_deviation,
    calculate_rolling_volatility,
)


class FeatureEngineeringService:
    def __init__(
        self,
        *,
        session: Session,
    ) -> None:
        self._instrument_repository = InstrumentRepository(session)
        self._market_bar_repository = MarketBarRepository(session)
        self._feature_set_repository = FeatureSetRepository(session)
        self._feature_value_repository = FeatureValueRepository(session)

    def generate(
        self,
        *,
        feature_set_name: str,
        description: str | None,
        configuration: dict,
        symbol: str,
        interval: BarInterval,
        start_time: datetime,
        end_time: datetime,
    ):
        validate_feature_time_range(
            start_time=start_time,
            end_time=end_time,
        )

        validate_feature_configuration(configuration)

        normalized_symbol = symbol.strip().upper()

        instrument = self._instrument_repository.get_model_by_symbol(normalized_symbol)

        bars = self._load_bars(
            instrument=instrument,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
        )

        if not bars:
            raise ValueError("No market bars exist for the requested range.")

        market_frame = self._bars_to_frame(bars)

        feature_frame = self._calculate_features(
            frame=market_frame,
            configuration=configuration,
        )

        feature_set = self._feature_set_repository.create(
            name=feature_set_name,
            description=description,
            configuration=configuration,
        )

        records = self._build_records(
            feature_set_id=feature_set.id,
            instrument_id=instrument.id,
            frame=feature_frame,
        )

        persisted_count = self._feature_value_repository.upsert_many(records)

        return feature_set, persisted_count

    def _load_bars(
        self,
        *,
        instrument,
        interval: BarInterval,
        start_time: datetime,
        end_time: datetime,
    ):
        return self._market_bar_repository.get_bars(
            instrument_id=instrument.id,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            limit=100_000,
        )

    @staticmethod
    def _bars_to_frame(
        bars,
    ) -> pd.DataFrame:
        rows = [
            {
                "timestamp": bar.timestamp,
                "open": float(bar.open_price),
                "high": float(bar.high_price),
                "low": float(bar.low_price),
                "close": float(bar.close_price),
                "volume": float(bar.volume),
            }
            for bar in bars
        ]

        frame = pd.DataFrame(rows)

        return frame.sort_values("timestamp").set_index("timestamp")

    @staticmethod
    def _calculate_features(
        *,
        frame: pd.DataFrame,
        configuration: dict,
    ) -> pd.DataFrame:
        requested_features = set(configuration["features"])

        result = pd.DataFrame(index=frame.index)

        simple_returns = calculate_simple_return(frame["close"])

        if "simple_return" in requested_features:
            result["simple_return"] = simple_returns

        if "log_return" in requested_features:
            result["log_return"] = calculate_log_return(frame["close"])

        if "rolling_mean_20" in requested_features:
            result["rolling_mean_20"] = calculate_rolling_mean(
                frame["close"],
                window=20,
            )

        if "rolling_std_20" in requested_features:
            result["rolling_std_20"] = calculate_rolling_standard_deviation(
                frame["close"],
                window=20,
            )

        if "rolling_volatility_20" in requested_features:
            result["rolling_volatility_20"] = calculate_rolling_volatility(
                simple_returns,
                window=20,
            )

        if "momentum_10" in requested_features:
            result["momentum_10"] = calculate_momentum(
                frame["close"],
                window=10,
            )

        if "rsi_14" in requested_features:
            result["rsi_14"] = calculate_relative_strength_index(
                frame["close"],
                window=14,
            )

        if "atr_14" in requested_features:
            result["atr_14"] = calculate_average_true_range(
                frame["high"],
                frame["low"],
                frame["close"],
                window=14,
            )

        if "volume_change" in requested_features:
            result["volume_change"] = calculate_volume_change(frame["volume"])

        if "drawdown" in requested_features:
            result["drawdown"] = calculate_drawdown(frame["close"])

        macd_features = {
            "macd",
            "macd_signal",
            "macd_histogram",
        }

        if requested_features & macd_features:
            macd = calculate_macd(frame["close"])

            for column in macd_features:
                if column in requested_features:
                    result[column] = macd[column]

        if result.empty:
            raise ValueError("No supported features were requested.")

        return result

    @staticmethod
    def _build_records(
        *,
        feature_set_id: UUID,
        instrument_id: UUID,
        frame: pd.DataFrame,
    ) -> list[dict]:
        records: list[dict] = []

        for timestamp, row in frame.iterrows():
            for feature_name, raw_value in row.items():
                feature_value = None

                if not pd.isna(raw_value):
                    feature_value = Decimal(str(float(raw_value)))

                normalized_timestamp = timestamp

                if hasattr(
                    timestamp,
                    "to_pydatetime",
                ):
                    normalized_timestamp = timestamp.to_pydatetime()

                records.append(
                    {
                        "feature_set_id": feature_set_id,
                        "instrument_id": instrument_id,
                        "timestamp": normalized_timestamp,
                        "feature_name": feature_name,
                        "feature_value": feature_value,
                    }
                )

        return records
