from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
from scipy.interpolate import LinearNDInterpolator, interp1d


def setup_interpolator(
    variables: Sequence[Any], function_values: np.ndarray, fill_value=np.nan, bounds_error=False, rescale=True
) -> Callable:
    """
    Create a 1D or multidimensional interpolator based on the number of variables.

    Args:
        variables: Sequence of variable arrays, each of shape (n,).
        function_values: NumPy array of function values.
        fill_value: Value to use for points outside the interpolation domain.
        bounds_error: If True, raise an error for out-of-bounds in 1D.
        rescale: If True, rescale points to the unit cube in N dimensions.

    Returns:
        Interpolator callable.
    """
    if len(variables) == 1:
        return interp1d(
            np.reshape(variables[0], -1),
            np.reshape(function_values, -1),
            fill_value=fill_value,
            bounds_error=bounds_error,
        )
    else:
        points = np.asarray([np.ravel(v) for v in variables]).T
        return LinearNDInterpolator(
            points,
            np.ravel(function_values),
            fill_value=fill_value,
            rescale=rescale,
        )
