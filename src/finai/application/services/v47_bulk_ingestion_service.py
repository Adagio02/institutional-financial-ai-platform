from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import time
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from finai.application.services.market_data_ingestion_service import (
    MarketDataIngestionService,
)
from finai.domain.learning.v47_universe import (
    V47Instrument,
    load_v47_universe,
)
from finai.domain.market_data.entities import Instrument
from finai.domain.market_data.enums import (
    AssetClass,
    BarInterval,
)
from finai.infrastructure.database.repositories.exceptions import (
    InstrumentNotFoundError,
)
from finai.infrastructure.database.repositories.instrument_repository import (
    InstrumentRepository,
)
from finai.infrastructure.database.repositories.market_bar_repository import (
    MarketBarRepository,
)
from finai.infrastructure.market_data.v47_alpaca_provider import (
    V47AlpacaHistoricalProvider,
)


@dataclass(frozen=True, slots=True)
class V47BulkIngestionResult:
    symbol_count: int
    successful_symbols: int
    failed_symbols: int
    windows_completed: int
    bars_received: int
    bars_persisted: int
    start_time: str
    end_time: str
    interval: str
    state_path: str
    summary_path: str


class V47BulkIngestionService:
    def __init__(
        self,
        *,
        database_url: str,
        provider: V47AlpacaHistoricalProvider,
        universe_path: str = (
            "config/v47_universe.json"
        ),
        artifact_directory: str = (
            "artifacts/v47/ingestion"
        ),
        maximum_bars_per_window: int = (
            10_000
        ),
        request_delay_seconds: float = 0.40,
        retry_count: int = 5,
    ) -> None:
        self._engine = create_engine(
            database_url
        )
        self._provider = provider
        self._universe_path = Path(
            universe_path
        )
        self._artifact_directory = Path(
            artifact_directory
        )
        self._artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._maximum_bars_per_window = int(
            maximum_bars_per_window
        )
        self._request_delay_seconds = float(
            request_delay_seconds
        )
        self._retry_count = int(
            retry_count
        )

    @property
    def state_path(self) -> Path:
        return (
            self._artifact_directory
            / "v47_bulk_ingestion_state.json"
        )

    @property
    def summary_path(self) -> Path:
        return (
            self._artifact_directory
            / "v47_bulk_ingestion_summary.json"
        )

    def _load_state(
        self,
    ) -> dict[str, Any]:
        if not self.state_path.exists():
            return {
                "version": "4.7",
                "symbols": {},
            }

        return json.loads(
            self.state_path.read_text(
                encoding="utf-8"
            )
        )

    def _save_state(
        self,
        state: dict[str, Any],
    ) -> None:
        temporary = self.state_path.with_suffix(
            ".tmp"
        )
        temporary.write_text(
            json.dumps(
                state,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        temporary.replace(
            self.state_path
        )

    @staticmethod
    def _ensure_instrument(
        repository: InstrumentRepository,
        definition: V47Instrument,
    ) -> None:
        try:
            repository.get_by_symbol(
                definition.symbol
            )
            return
        except InstrumentNotFoundError:
            pass

        repository.create(
            Instrument(
                symbol=definition.symbol,
                name=definition.name,
                asset_class=AssetClass(
                    definition.asset_class
                ),
                exchange=definition.exchange,
                currency="USD",
                active=True,
            )
        )

    @staticmethod
    def _windows(
        *,
        start_time: datetime,
        end_time: datetime,
        chunk_days: int,
    ):
        cursor = start_time

        while cursor < end_time:
            next_end = min(
                cursor
                + timedelta(
                    days=chunk_days
                ),
                end_time,
            )
            yield cursor, next_end
            cursor = next_end

    def _ingest_with_retry(
        self,
        *,
        service: MarketDataIngestionService,
        symbol: str,
        interval: BarInterval,
        start_time: datetime,
        end_time: datetime,
    ):
        last_error: Exception | None = None

        for attempt in range(
            1,
            self._retry_count + 1,
        ):
            try:
                return service.ingest(
                    symbol=symbol,
                    interval=interval,
                    start_time=start_time,
                    end_time=end_time,
                )
            except Exception as error:
                last_error = error

                if attempt >= self._retry_count:
                    raise

                delay = min(
                    30.0,
                    2.0 ** (
                        attempt - 1
                    ),
                )
                print(
                    f"[retry] {symbol} "
                    f"{start_time.isoformat()} "
                    f"attempt={attempt} "
                    f"delay={delay:.1f}s "
                    f"error={type(error).__name__}: "
                    f"{error}",
                    flush=True,
                )
                time.sleep(delay)

        if last_error is not None:
            raise last_error

        raise RuntimeError(
            "Ingestion retry loop failed."
        )

    def run(
        self,
        *,
        interval: str,
        start_time: datetime,
        end_time: datetime,
        chunk_days: int = 14,
        symbols: list[str] | None = None,
        maximum_symbols: int | None = None,
        resume: bool = True,
    ) -> V47BulkIngestionResult:
        if start_time.tzinfo is None:
            raise ValueError(
                "start_time must be timezone-aware."
            )
        if end_time.tzinfo is None:
            raise ValueError(
                "end_time must be timezone-aware."
            )
        if start_time >= end_time:
            raise ValueError(
                "start_time must be before end_time."
            )
        if chunk_days < 1:
            raise ValueError(
                "chunk_days must be positive."
            )

        bar_interval = BarInterval(
            interval.strip().lower()
        )
        universe = load_v47_universe(
            self._universe_path
        )

        selected = [
            item
            for item in universe.instruments
            if item.enabled
        ]

        if symbols:
            requested = {
                value.strip().upper()
                for value in symbols
            }
            selected = [
                item
                for item in selected
                if item.symbol in requested
            ]

        if maximum_symbols is not None:
            selected = selected[
                :int(maximum_symbols)
            ]

        state = self._load_state()
        state["run_start_time"] = (
            start_time.isoformat()
        )
        state["run_end_time"] = (
            end_time.isoformat()
        )
        state["interval"] = (
            bar_interval.value
        )
        state["chunk_days"] = int(
            chunk_days
        )

        successful_symbols = 0
        failed_symbols = 0
        windows_completed = 0
        bars_received = 0
        bars_persisted = 0

        with Session(
            self._engine
        ) as session:
            instrument_repository = (
                InstrumentRepository(
                    session
                )
            )
            market_bar_repository = (
                MarketBarRepository(
                    session
                )
            )
            ingestion_service = (
                MarketDataIngestionService(
                    instrument_repository=(
                        instrument_repository
                    ),
                    market_bar_repository=(
                        market_bar_repository
                    ),
                    provider=self._provider,
                    maximum_bars=(
                        self
                        ._maximum_bars_per_window
                    ),
                )
            )

            for index, definition in enumerate(
                selected,
                start=1,
            ):
                symbol = definition.symbol

                print(
                    f"[symbol {index}/"
                    f"{len(selected)}] "
                    f"{symbol}",
                    flush=True,
                )

                symbol_state = (
                    state["symbols"]
                    .setdefault(
                        symbol,
                        {
                            "completed_windows": [],
                            "bars_received": 0,
                            "bars_persisted": 0,
                            "status": "pending",
                        },
                    )
                )

                try:
                    self._ensure_instrument(
                        instrument_repository,
                        definition,
                    )

                    for (
                        window_start,
                        window_end,
                    ) in self._windows(
                        start_time=start_time,
                        end_time=end_time,
                        chunk_days=chunk_days,
                    ):
                        window_key = (
                            window_start
                            .isoformat()
                            + "__"
                            + window_end
                            .isoformat()
                        )

                        if (
                            resume
                            and window_key
                            in symbol_state[
                                "completed_windows"
                            ]
                        ):
                            continue

                        print(
                            "  [window] "
                            f"{window_start.date()} "
                            "-> "
                            f"{window_end.date()}",
                            flush=True,
                        )

                        result = (
                            self
                            ._ingest_with_retry(
                                service=(
                                    ingestion_service
                                ),
                                symbol=symbol,
                                interval=bar_interval,
                                start_time=(
                                    window_start
                                ),
                                end_time=window_end,
                            )
                        )

                        received = int(
                            result.bars_received
                        )
                        persisted = int(
                            result.bars_persisted
                        )

                        windows_completed += 1
                        bars_received += received
                        bars_persisted += (
                            persisted
                        )

                        symbol_state[
                            "bars_received"
                        ] = int(
                            symbol_state.get(
                                "bars_received",
                                0,
                            )
                        ) + received
                        symbol_state[
                            "bars_persisted"
                        ] = int(
                            symbol_state.get(
                                "bars_persisted",
                                0,
                            )
                        ) + persisted
                        symbol_state[
                            "completed_windows"
                        ].append(
                            window_key
                        )
                        symbol_state[
                            "last_completed_end"
                        ] = (
                            window_end
                            .isoformat()
                        )
                        symbol_state[
                            "status"
                        ] = "running"

                        self._save_state(
                            state
                        )

                        if (
                            self
                            ._request_delay_seconds
                            > 0.0
                        ):
                            time.sleep(
                                self
                                ._request_delay_seconds
                            )

                    symbol_state[
                        "status"
                    ] = "complete"
                    symbol_state[
                        "completed_at"
                    ] = datetime.now(
                        UTC
                    ).isoformat()
                    successful_symbols += 1

                except Exception as error:
                    session.rollback()
                    symbol_state[
                        "status"
                    ] = "failed"
                    symbol_state[
                        "error"
                    ] = (
                        f"{type(error).__name__}: "
                        f"{error}"
                    )
                    failed_symbols += 1

                    print(
                        f"  [failed] {symbol}: "
                        f"{type(error).__name__}: "
                        f"{error}",
                        flush=True,
                    )

                self._save_state(
                    state
                )

        result = V47BulkIngestionResult(
            symbol_count=len(selected),
            successful_symbols=(
                successful_symbols
            ),
            failed_symbols=failed_symbols,
            windows_completed=(
                windows_completed
            ),
            bars_received=bars_received,
            bars_persisted=bars_persisted,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            interval=bar_interval.value,
            state_path=str(
                self.state_path
            ),
            summary_path=str(
                self.summary_path
            ),
        )

        self.summary_path.write_text(
            json.dumps(
                asdict(result),
                indent=2,
            ),
            encoding="utf-8",
        )

        return result
