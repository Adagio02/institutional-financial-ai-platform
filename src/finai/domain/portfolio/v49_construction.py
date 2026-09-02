from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

import numpy as np


@dataclass(frozen=True, slots=True)
class PortfolioConstraints:
    target_gross_exposure: float = 1.0
    target_net_exposure: float = 0.0
    maximum_absolute_weight: float = 0.10
    minimum_absolute_weight: float = 1e-6

    def validate(self) -> None:
        if self.target_gross_exposure <= 0.0:
            raise ValueError("target_gross_exposure must be positive.")
        if abs(self.target_net_exposure) > self.target_gross_exposure:
            raise ValueError("Absolute net exposure cannot exceed gross exposure.")
        if not 0.0 < self.maximum_absolute_weight <= 1.0:
            raise ValueError("maximum_absolute_weight must be in (0, 1].")
        if self.minimum_absolute_weight < 0.0:
            raise ValueError("minimum_absolute_weight cannot be negative.")
        if self.minimum_absolute_weight > self.maximum_absolute_weight:
            raise ValueError("Minimum weight cannot exceed maximum weight.")


@dataclass(frozen=True, slots=True)
class PortfolioConstructionResult:
    weights: dict[str, float]
    gross_exposure: float
    net_exposure: float
    long_exposure: float
    short_exposure: float
    position_count: int
    maximum_absolute_weight: float
    turnover_from_current: float | None
    constraints: dict[str, float]


class PortfolioConstructionEngine:
    """Apply portfolio-level exposure and position constraints to proposed weights.

    V4.9 deliberately accepts proposed weights rather than generating them from
    ranks. Rank-to-position construction is V4.9.1, risk/factor neutralization is
    V4.9.2, and turnover/cost-aware optimization is V4.9.3.
    """

    _TOLERANCE = 1e-10

    def __init__(self, constraints: PortfolioConstraints | None = None) -> None:
        self.constraints = constraints or PortfolioConstraints()
        self.constraints.validate()

    def construct(
        self,
        proposed_weights: Mapping[str, float],
        *,
        current_weights: Mapping[str, float] | None = None,
    ) -> PortfolioConstructionResult:
        names, proposals = self._validated_vector(proposed_weights)
        long_target = (
            self.constraints.target_gross_exposure
            + self.constraints.target_net_exposure
        ) / 2.0
        short_target = (
            self.constraints.target_gross_exposure
            - self.constraints.target_net_exposure
        ) / 2.0

        weights = np.zeros_like(proposals)
        weights[proposals > 0.0] = self._allocate_side(
            np.abs(proposals[proposals > 0.0]), target=long_target
        )
        weights[proposals < 0.0] = -self._allocate_side(
            np.abs(proposals[proposals < 0.0]), target=short_target
        )
        weights[np.abs(weights) < self.constraints.minimum_absolute_weight] = 0.0

        output = {
            name: float(weight)
            for name, weight in zip(names, weights, strict=True)
            if weight != 0.0
        }
        long_exposure = float(weights[weights > 0.0].sum())
        short_exposure = float(-weights[weights < 0.0].sum())
        turnover = self._turnover(output, current_weights) if current_weights is not None else None
        return PortfolioConstructionResult(
            weights=output,
            gross_exposure=long_exposure + short_exposure,
            net_exposure=long_exposure - short_exposure,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            position_count=len(output),
            maximum_absolute_weight=float(np.abs(weights).max(initial=0.0)),
            turnover_from_current=turnover,
            constraints=asdict(self.constraints),
        )

    @staticmethod
    def _validated_vector(proposed_weights: Mapping[str, float]) -> tuple[list[str], np.ndarray]:
        if not proposed_weights:
            raise ValueError("proposed_weights cannot be empty.")
        normalized: dict[str, float] = {}
        for symbol, value in proposed_weights.items():
            name = str(symbol).strip().upper()
            if not name:
                raise ValueError("Symbols cannot be blank.")
            if name in normalized:
                raise ValueError("Symbols must be unique after normalization.")
            normalized[name] = float(value)
        values = np.asarray(list(normalized.values()), dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("All proposed weights must be finite.")
        return list(normalized), values

    def _allocate_side(self, preferences: np.ndarray, *, target: float) -> np.ndarray:
        if target <= self._TOLERANCE:
            return np.zeros_like(preferences)
        count = len(preferences)
        cap = self.constraints.maximum_absolute_weight
        if count == 0:
            raise ValueError("Proposed weights do not contain both required sides.")
        if count * cap + self._TOLERANCE < target:
            raise ValueError("Position cap is infeasible for the requested exposure.")

        allocation = np.zeros(count, dtype=float)
        active = np.ones(count, dtype=bool)
        remaining = float(target)
        while remaining > self._TOLERANCE:
            active_index = np.flatnonzero(active)
            if not len(active_index):
                raise RuntimeError("Unable to satisfy portfolio exposure constraints.")
            basis = preferences[active_index]
            proposed = (
                remaining * basis / basis.sum()
                if basis.sum() > self._TOLERANCE
                else np.full(len(active_index), remaining / len(active_index))
            )
            room = cap - allocation[active_index]
            applied = np.minimum(proposed, room)
            allocation[active_index] += applied
            remaining = target - float(allocation.sum())
            saturated = room - applied <= self._TOLERANCE
            active[active_index[saturated]] = False
        return allocation

    @staticmethod
    def _turnover(
        new_weights: Mapping[str, float], current_weights: Mapping[str, float]
    ) -> float:
        normalized_current = {
            str(symbol).strip().upper(): float(weight)
            for symbol, weight in current_weights.items()
        }
        universe = set(new_weights) | set(normalized_current)
        values = [
            abs(float(new_weights.get(symbol, 0.0)) - normalized_current.get(symbol, 0.0))
            for symbol in universe
        ]
        return 0.5 * float(sum(values))
