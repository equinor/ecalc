import numpy as np
from libecalc.common.list.adjustment import transform_linear


def test_linear_transform():
    array = np.array([1, 2, 3, 4, 5])
    constant = 1.5
    factor = 3
    result = transform_linear(values=array, constant=constant, factor=factor)
    np.testing.assert_allclose(actual=result, desired=array * factor + constant)
