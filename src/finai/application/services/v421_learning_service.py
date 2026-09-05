from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from finai.application.services.v38_learning_service import (
    V38BacktestMetrics,
    V38LearningCycleResult,
)
from finai.application.services.v41_learning_service import (
    V41LearningService,
)
from finai.domain.learning.v421_features import (
    V421_FEATURE_COLUMNS,
    build_v421_features,
)


class V421LearningService(V41LearningService):
    """
    V4.2.1 correctness release.

    Changes from V4.1:

    1. Non-overlapping fixed-horizon event backtest.
    2. One configured round-trip transaction cost
       is charged per completed event trade.
    3. DST-aware America/New_York session features.
    4. V4.1 model-selection and governance logic
       remains unchanged.
    """

    VERSION = "4.2.1"

    LEARNING_ARCHITECTURE = "fixed_horizon_cost_corrected_dst_aware_regime_ensemble"

    BACKTEST_METHOD = "non_overlapping_fixed_horizon"

    SESSION_TIMEZONE = "America/New_York"

    @property
    def feature_columns(
        self,
    ) -> list[str]:
        return list(V421_FEATURE_COLUMNS)

    def build_dataset(
        self,
        *,
        symbol: str,
        interval: str,
        include_target: bool,
    ) -> tuple[
        pd.DataFrame,
        int,
    ]:
        normalized_symbol = symbol.strip().upper()

        normalized_interval = interval.strip().lower()

        target_bars = self.load_market_bars(
            symbol=normalized_symbol,
            interval=normalized_interval,
        )

        spy_bars = self.load_market_bars(
            symbol="SPY",
            interval=normalized_interval,
        )

        qqq_bars = self.load_market_bars(
            symbol="QQQ",
            interval=normalized_interval,
        )

        rows_loaded = len(target_bars)

        dataset = build_v421_features(
            target_bars=target_bars,
            spy_bars=spy_bars,
            qqq_bars=qqq_bars,
            forward_horizon_bars=(self._forward_horizon_bars),
            minimum_edge_bps=(self._target_minimum_edge_bps),
            round_trip_cost_bps=(self._v41_round_trip_cost_bps),
            include_target=include_target,
        )

        return (
            dataset,
            rows_loaded,
        )

    def simulate(
        self,
        *,
        positions: np.ndarray,
        forward_returns: np.ndarray,
    ) -> V38BacktestMetrics:
        """
        Simulate fixed-horizon, non-overlapping
        event trades.

        A signal at row t opens one position whose
        economic result is the forward return from
        t to t + forward_horizon_bars.

        While that trade is active, subsequent rows
        are not treated as additional independent
        full-size positions.

        A new trade may begin at t + horizon.

        Transaction-cost convention:

            round_trip_cost_bps

        represents the COMPLETE entry + exit cost
        for one completed event trade and is
        therefore subtracted exactly once.
        """

        normalized_positions = np.asarray(
            positions,
            dtype=int,
        )

        normalized_returns = np.asarray(
            forward_returns,
            dtype=float,
        )

        if len(normalized_positions) != len(normalized_returns):
            raise ValueError("Position and return row counts do not match.")

        if len(normalized_positions) == 0:
            return V38BacktestMetrics(
                gross_return=0.0,
                transaction_cost=0.0,
                net_return=0.0,
                trade_count=0,
                turnover=0.0,
                maximum_drawdown=0.0,
                sharpe_like=0.0,
            )

        horizon = max(
            1,
            int(self._forward_horizon_bars),
        )

        round_trip_cost_rate = self._v41_round_trip_cost_bps / 10_000.0

        gross_trade_returns: list[float] = []

        net_trade_returns: list[float] = []

        index = 0

        row_count = len(normalized_positions)

        while index < row_count:
            position = int(normalized_positions[index])

            forward_return = float(normalized_returns[index])

            if position == 0 or not np.isfinite(forward_return):
                index += 1
                continue

            gross_trade_return = float(position) * forward_return

            net_trade_return = gross_trade_return - round_trip_cost_rate

            gross_trade_returns.append(gross_trade_return)

            net_trade_returns.append(net_trade_return)

            # The event occupies the full target
            # horizon. The next independent event
            # may begin at t + horizon.
            index += horizon

        trade_count = len(net_trade_returns)

        if trade_count == 0:
            return V38BacktestMetrics(
                gross_return=0.0,
                transaction_cost=0.0,
                net_return=0.0,
                trade_count=0,
                turnover=0.0,
                maximum_drawdown=0.0,
                sharpe_like=0.0,
            )

        gross_array = np.asarray(
            gross_trade_returns,
            dtype=float,
        )

        net_array = np.asarray(
            net_trade_returns,
            dtype=float,
        )

        gross_equity = np.cumprod(1.0 + gross_array)

        net_equity = np.cumprod(1.0 + net_array)

        gross_return = float(gross_equity[-1] - 1.0)

        net_return = float(net_equity[-1] - 1.0)

        transaction_cost = float(trade_count * round_trip_cost_rate)

        # One entry plus one exit for each
        # completed event trade.
        turnover = float(trade_count * 2)

        running_peak = np.maximum.accumulate(net_equity)

        drawdowns = 1.0 - (
            net_equity
            / np.where(
                running_peak == 0.0,
                1.0,
                running_peak,
            )
        )

        maximum_drawdown = float(np.max(drawdowns))

        return_std = float(np.std(net_array))

        if return_std > 0.0:
            sharpe_like = float(np.mean(net_array) / return_std * np.sqrt(float(trade_count)))
        else:
            sharpe_like = 0.0

        return V38BacktestMetrics(
            gross_return=gross_return,
            transaction_cost=(transaction_cost),
            net_return=net_return,
            trade_count=trade_count,
            turnover=turnover,
            maximum_drawdown=(maximum_drawdown),
            sharpe_like=(sharpe_like),
        )

    @staticmethod
    def _load_json_file(
        path: Path,
    ) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(
            payload,
            dict,
        ):
            raise RuntimeError(f"Expected JSON object: {path}")

        return payload

    @staticmethod
    def _write_json_file(
        *,
        path: Path,
        payload: dict[str, Any],
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            json.dumps(
                payload,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    def _patch_candidate_metadata(
        self,
        *,
        path: Path,
    ) -> None:
        if not path.exists():
            return

        payload = self._load_json_file(path)

        payload["version"] = self.VERSION

        payload["learning_architecture"] = self.LEARNING_ARCHITECTURE

        payload["backtest_method"] = self.BACKTEST_METHOD

        payload["session_timezone"] = self.SESSION_TIMEZONE

        payload["correctness_release"] = {
            "non_overlapping_forward_returns": True,
            "single_round_trip_cost_per_trade": True,
            "dst_aware_session_features": True,
        }

        payload["backtest"] = {
            "method": (self.BACKTEST_METHOD),
            "holding_period_bars": (int(self._forward_horizon_bars)),
            "overlapping_positions": False,
            "round_trip_cost_bps": (float(self._v41_round_trip_cost_bps)),
            "cost_accounting": ("one complete round-trip cost per event trade"),
        }

        self._write_json_file(
            path=path,
            payload=payload,
        )

    def _patch_latest_metadata(
        self,
    ) -> None:
        latest_path = self._artifact_directory / "latest_learning_cycle.json"

        if not latest_path.exists():
            return

        payload = self._load_json_file(latest_path)

        payload["version"] = self.VERSION

        payload["learning_architecture"] = self.LEARNING_ARCHITECTURE

        payload["backtest_method"] = self.BACKTEST_METHOD

        payload["session_timezone"] = self.SESSION_TIMEZONE

        payload["correctness_release"] = {
            "non_overlapping_forward_returns": True,
            "single_round_trip_cost_per_trade": True,
            "dst_aware_session_features": True,
        }

        shadow_metadata_path = payload.get("shadow_metadata_path")

        self._write_json_file(
            path=latest_path,
            payload=payload,
        )

        if shadow_metadata_path:
            shadow_path = Path(shadow_metadata_path)

            if shadow_path.exists():
                shadow_payload = self._load_json_file(shadow_path)

                shadow_payload["version"] = self.VERSION

                shadow_payload["learning_architecture"] = self.LEARNING_ARCHITECTURE

                shadow_payload["backtest_method"] = self.BACKTEST_METHOD

                shadow_payload["session_timezone"] = self.SESSION_TIMEZONE

                self._write_json_file(
                    path=shadow_path,
                    payload=(shadow_payload),
                )

    def run_learning_cycle(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> V38LearningCycleResult:
        """
        Use the complete V4.1 research/governance
        workflow while dispatching through the
        V4.2.1 feature builder and simulator.
        """

        result = super().run_learning_cycle(
            symbol=symbol,
            interval=interval,
        )

        candidate_metadata_path = Path(result.candidate_metadata_path)

        self._patch_candidate_metadata(path=(candidate_metadata_path))

        self._patch_latest_metadata()

        return result
