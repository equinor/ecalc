import numpy as np
import pandas as pd
from numpy.typing import NDArray


def clean_nan_values(values: NDArray[np.float64]) -> NDArray[np.float64]:
    """
    Handles NaN values in a consistent and predictable way by:

    1. Forward filling all NaN values using the last valid observation.
    2. Replacing any remaining NaNs (e.g., if the first value was NaN) with 0.0.

    This function is immutable – it does not modify the input array in-place.

    Args:
        values: A NumPy array of float64 values (may contain NaNs).

    Returns:
        A cleaned NumPy array with no NaN values.
    """

    # Step 1: Forward-fill NaNs using pandas
    filled = pd.Series(values).ffill().to_numpy()

    result = np.nan_to_num(filled)  # By convention, we change remaining NaN-values to 0 regardless of extrapolation
    return result
