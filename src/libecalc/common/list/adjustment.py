import numpy as np
from numpy.typing import NDArray


def transform_linear(
    values: NDArray[np.float64] | float,
    constant: float = 0.0,
    factor: float = 1.0,
) -> NDArray[np.float64] | float:
    """Linear transformation of an array. May typically be used for energy functions to adjust a result
    according to given energy_usage_adjustment_constant and energy_usage_adjustment_factor.
    """
    constant = constant if constant is not None else 0.0
    factor = factor if factor is not None else 1.0
    return values * factor + constant
