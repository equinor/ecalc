from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
from scipy.interpolate import LinearNDInterpolator, interp1d


def setup_interpolator_1d(
    variable: np.ndarray, function_values: np.ndarray, fill_value=np.nan, bounds_error=False
) -> Callable:
    """
    Create a 1D interpolator for given variable and function values.

    Parameters:
        variable (np.ndarray): 1D array of input variable values.
        function_values (np.ndarray): 1D array of function values corresponding to the variable.
        fill_value (float or tuple, optional): Value to use for points outside the interpolation range. Default is np.nan.
        bounds_error (bool, optional): If True, raise an error when interpolating outside the range. Default is False.

    Returns:
        Callable: A function that interpolates new values.
    """
    return interp1d(
        np.reshape(variable, -1),
        np.reshape(function_values, -1),
        fill_value=fill_value,
        bounds_error=bounds_error,
    )


def setup_interpolator_n_dimensional(
    variables: Sequence[np.ndarray], function_values: np.ndarray, fill_value=np.nan, rescale=True
) -> Callable:
    """
    Create an N-dimensional linear interpolator for given variables and function values.

    Parameters:
        variables (Sequence[np.ndarray]): Sequence of arrays representing each input dimension.
        function_values (np.ndarray): Array of function values at the grid points defined by variables.
        fill_value (float, optional): Value to use for points outside the convex hull. Default is np.nan.
        rescale (bool, optional): Whether to rescale variables to the unit cube before interpolating. Default is True.

    Returns:
        Callable: A function that interpolates new values in N dimensions.
    """
    points = np.asarray([np.ravel(v) for v in variables]).T
    return LinearNDInterpolator(
        points,
        np.ravel(function_values),
        fill_value=fill_value,
        rescale=rescale,
    )


def setup_interpolator(
    variables: Sequence[Any], function_values: np.ndarray, fill_value=np.nan, bounds_error=False, rescale=True
) -> Callable:
    """
    Dispatcher for 1D or N-dimensional interpolation.
    """
    if len(variables) == 1:
        return setup_interpolator_1d(
            variable=variables[0],
            function_values=function_values,
            fill_value=fill_value,
            bounds_error=bounds_error,
        )
    else:
        return setup_interpolator_n_dimensional(
            variables=variables,
            function_values=function_values,
            fill_value=fill_value,
            rescale=rescale,
        )
