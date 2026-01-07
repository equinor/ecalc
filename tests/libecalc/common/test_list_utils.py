import numpy as np
import pytest

from libecalc.common.list.list_utils import (
    array_to_list,
    elementwise_multiplication,
    elementwise_sum,
    group_data_by_value_at_index,
)


def test_group_data_by_value_at_index():
    expected = {1: [[1, 20], [1, 30]], 2: [[2, 10]]}
    res = group_data_by_value_at_index(0, [[1, 20], [2, 10], [1, 30]])

    assert expected == res


def test_group_data_by_value_at_index_negative_index():
    with pytest.raises(expected_exception=IndexError):
        group_data_by_value_at_index(-1, [[1, 20], [2, 10], [1, 30]])


def test_group_data_by_value_at_index_out_of_bounds():
    with pytest.raises(expected_exception=IndexError):
        group_data_by_value_at_index(2, [[1, 20], [2, 10], [1, 30]])


def test_elementwise_sum():
    list1 = [0, 1, 2]
    list2 = [0, 0, 1]
    expected_result = [0, 1, 3]
    result = list(elementwise_sum(list1, list2))

    assert result == expected_result


def test_elementwise_multiplication():
    list1 = [0, 1, 2]
    list2 = [0, 0, 1]
    expected_result = [0, 0, 2]
    result = list(elementwise_multiplication(list1, list2))

    assert result == expected_result


def test_array_to_list_always_returns_list():
    # 0D array
    arr_0d = np.array(42.0)
    assert array_to_list(arr_0d) == [42.0]

    # 1D array with single element
    arr_1d_single = np.array([42.0])
    assert array_to_list(arr_1d_single) == [42.0]

    # 1D array
    arr_1d = np.array([1.0, 2.0])
    assert array_to_list(arr_1d) == [1.0, 2.0]

    # List of arrays
    arr_list = [np.array([1.0]), np.array([2.0])]
    assert array_to_list(arr_list) == [1.0, 2.0]

    # Scalar float - returns empty list, as only allowed input is array or list of arrays
    assert array_to_list(3.14) == []

    # Scalar int - returns empty list, as only allowed input is array or list of arrays
    assert array_to_list(7) == []

    # None
    assert array_to_list(None) is None
