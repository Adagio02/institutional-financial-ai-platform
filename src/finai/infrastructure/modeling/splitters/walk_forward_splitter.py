from collections.abc import Iterator

import numpy as np

from finai.domain.modeling.validation import (
    validate_walk_forward_settings,
)


class WalkForwardSplitter:
    def __init__(
        self,
        *,
        number_of_splits: int,
        test_size: int,
        minimum_training_size: int | None = None,
    ) -> None:
        self._number_of_splits = number_of_splits
        self._test_size = test_size
        self._minimum_training_size = minimum_training_size

    def split(
        self,
        number_of_rows: int,
    ) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        validate_walk_forward_settings(
            number_of_rows=number_of_rows,
            number_of_splits=self._number_of_splits,
            test_size=self._test_size,
        )

        minimum_training_size = self._minimum_training_size or number_of_rows - (
            self._number_of_splits * self._test_size
        )

        if minimum_training_size < 1:
            raise ValueError("minimum_training_size must be positive.")

        for fold_number in range(self._number_of_splits):
            training_end = minimum_training_size + fold_number * self._test_size

            validation_start = training_end
            validation_end = validation_start + self._test_size

            if validation_end > number_of_rows:
                break

            training_indices = np.arange(
                0,
                training_end,
            )

            validation_indices = np.arange(
                validation_start,
                validation_end,
            )

            yield (
                training_indices,
                validation_indices,
            )
