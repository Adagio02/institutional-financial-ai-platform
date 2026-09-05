import numpy as np

from finai.infrastructure.modeling.splitters.walk_forward_splitter import (
    WalkForwardSplitter,
)


def test_walk_forward_splitter_keeps_time_order() -> None:
    splitter = WalkForwardSplitter(
        number_of_splits=3,
        test_size=5,
        minimum_training_size=15,
    )

    folds = list(splitter.split(30))

    assert len(folds) == 3

    for training_indices, validation_indices in folds:
        assert training_indices.max() < (validation_indices.min())


def test_walk_forward_training_window_expands() -> None:
    splitter = WalkForwardSplitter(
        number_of_splits=3,
        test_size=5,
        minimum_training_size=15,
    )

    folds = list(splitter.split(30))

    training_sizes = [len(training_indices) for training_indices, _ in folds]

    assert training_sizes == [15, 20, 25]


def test_walk_forward_validation_windows_do_not_overlap() -> None:
    splitter = WalkForwardSplitter(
        number_of_splits=3,
        test_size=5,
        minimum_training_size=15,
    )

    folds = list(splitter.split(30))

    first_validation = folds[0][1]
    second_validation = folds[1][1]

    assert not np.intersect1d(
        first_validation,
        second_validation,
    ).size
