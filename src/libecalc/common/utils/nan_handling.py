import numpy as np
from numpy.typing import NDArray

from libecalc.common.utils.rates import Rates


def clean_nan_values(values: NDArray[np.float64]) -> NDArray[np.float64]:
    """
    Handles NaN values in a consistent manner:
    - Forward fills NaN values.
    - Replaces remaining NaN values with 0.0.

    Args:
        values: A numpy array of float values.

    Returns:
        A numpy array with NaN values handled.
    """

    result = Rates.forward_fill_nan_values(rates=values)  # Fill NaN values
    result = np.nan_to_num(result)  # By convention, we change remaining NaN-values to 0 regardless of extrapolation
    return result
