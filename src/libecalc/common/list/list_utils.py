from collections import defaultdict
from collections.abc import Sequence
from typing import Any, cast

import numpy as np
from numpy import float64
from numpy.typing import NDArray

from libecalc.common.time_utils import Periods

"""
NOTE! A "list util" class is not the best, but maybe we should try to
expand a "prototype" class instead, e.g. create "our own static list class" where we extend
python list and add static methods to it..?
"""


def transpose(a: list[list[str | int | float]]) -> list[list[str | int | float]]:
    """Easily transpose from row based to column based data, and other
    way around, in order to use the format that best fits a certain
    purpose to work with such a list/dataframe.

    Args:
        a:list to be transposed

    Returns:
        Transposed list

    """
    return list(map(list, zip(*a)))


def group_data_by_value_at_index(index: int, row_based_data: list[list[Any]]) -> dict[float | int, list[Any]]:
    """Given an index of the list, group the list by the value corresponding to that index and
    return a dict with lists, where the keys correspond to the different values at the index provided.

    E.g. if we provide a list [[1,20], [2,10], [1,30]] and provide index 0,
    we will get the dict: {1: [[1, 20], [1, 30]], 2: [[2, 10]]}

    Args:
        index: Positive index
        row_based_data:

    Returns:
        dict with lists, where the keys correspond to the different values at the index provided.

    Raises:
        IndexError: if index specified is out of range/bounds, which should be handled by calling function.

    """
    if index < 0:
        raise IndexError(f"Negative indexes are not allowed: {index}")

    chart_grouped_by_index = defaultdict(list)
    for row in row_based_data:
        current_value = row[index]
        chart_grouped_by_index[current_value].append(row)

    return chart_grouped_by_index


def elementwise_sum(*vectors: Sequence[float | None], periods: Periods | None = None) -> NDArray[np.float64]:
    """Sum up multiple vectors elementwise.

    E.g. if we provide three lists [1,20], [2,10], [1,30], the result will be [1+2+1,20+10+30] = [4,60]

    Args:
        *vectors: Sequences to be summed up elementwise
        periods: Optional list of periods used to initialize resulting array. If no periods are provided, the first vector is used

    Returns:
        Numpy array where the elements of provided vectors are summed up elementwise

    """
    if periods is not None:
        result = np.full_like(periods.periods, fill_value=0.0, dtype=float64)
    else:
        result = np.full_like(vectors[0], fill_value=0.0, dtype=float64)

    for vector in vectors:
        result = np.add(result, vector)  # type: ignore[arg-type]
    return result


def elementwise_multiplication(*vectors: Sequence[float | None], periods: Periods | None = None) -> NDArray[np.float64]:
    """Multiply multiple vectors elementwise.

    E.g. if we provide three lists [1,20], [2,10], [1,30], the result will be [1*2*1,20*10*30] = [2,6000]

    Args:
        *vectors: Sequences to be multiplied up elementwise
        periods: Optional list of periods used to initialize resulting array. If no periods are provided, the first vector is used

    Returns:
        Numpy array where the elements of provided vectors are multiplied up elementwise

    """
    if periods is not None:
        result = np.full_like(periods.periods, fill_value=1.0, dtype=float64)
    else:
        result = np.full_like(vectors[0], fill_value=1.0, dtype=float64)

    for vector in vectors:
        result = np.multiply(result, vector)  # type: ignore[arg-type]
    return result


def array_to_list(result_array: NDArray[np.float64] | list[NDArray[np.float64]] | None) -> list | None:
    """Method to convert numpy arrays and list of numpy arrays into lists (or list of lists). Method is used recursively on lists so needs to handle None as well.

    Args:
        result_array: A numpy array, a list of numpy arrays or None

    Returns:
        list or list of lists
    """
    if result_array is None:
        return None

    if isinstance(result_array, list):
        # In case we have a list of arrays.
        return [array_to_list(array) for array in result_array]
    elif isinstance(result_array, np.ndarray):
        return cast(list, result_array.tolist())
