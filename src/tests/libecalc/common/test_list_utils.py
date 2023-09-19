import pytest
from libecalc.common.list_utils import (
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
