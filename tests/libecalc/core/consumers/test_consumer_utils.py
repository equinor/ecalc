import numpy as np

from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.utils import (
    apply_condition,
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
