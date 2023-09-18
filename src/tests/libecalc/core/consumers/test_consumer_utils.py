import numpy as np
from libecalc.core.consumers.consumer_system import ConsumerSystem
from libecalc.core.consumers.legacy_consumer.consumer_function.utils import (
    apply_condition,
)


def test_topologically_sort_consumers_by_crossover():
    unsorted_consumers = [
        "Consumer 1 with no crossover",
        "Consumer 2 with crossover to consumer 3",
        "Consumer 3 with crossover to consumer 1",
    ]

    sorted_consumers = [
        "Consumer 2 with crossover to consumer 3",
        "Consumer 3 with crossover to consumer 1",
        "Consumer 1 with no crossover",
    ]

    assert (
        ConsumerSystem._topologically_sort_consumers_by_crossover(crossover=[0, 3, 1], consumers=unsorted_consumers)
        == sorted_consumers
    )


def test_apply_condition() -> None:
    """Test that apply_condition sets elements in 1D array and columns in 2D array to zero"""
    condition = np.asarray([1, 0, 1, 0])
    input_array_1D = np.asarray([10, 10, 10, 10])
    input_array_2D = np.asarray([[10, 10, 10, 10], [10, 10, 10, 10]])

    input_array_1D_after_condition = apply_condition(input_array=input_array_1D, condition=condition)
    input_array_2D_after_condition = apply_condition(input_array=input_array_2D, condition=condition)

    expected_input_array_1D_after_condition = np.asarray([10, 0, 10, 0])
    expected_input_array_2D_after_condition = np.asarray([[10, 0, 10, 0], [10, 0, 10, 0]])

    assert np.array_equal(input_array_1D_after_condition, expected_input_array_1D_after_condition)
    assert np.array_equal(input_array_2D_after_condition, expected_input_array_2D_after_condition)
