import numpy as np
from numpy.typing import NDArray


class TimeSeriesMask:
    """
    Encapsulates a mask for time series data, allowing conditional application to arrays.
    """

    def __init__(self, mask: NDArray[np.int_] | None):
        """
        Initializes the TimeSeriesMask.

        Args:
            mask: An integer NumPy array (1/0) or None. If None, no mask is applied.
        """
        self._mask = mask

    def apply(self, array: np.ndarray) -> np.ndarray:
        """
        Applies the mask to the given array.

        Args:
            array: The input NumPy array to be masked.

        Returns:
            A new array where values are set to 0 where the mask is 0, or unchanged if mask is None.
        """
        if self._mask is None:
            return np.asarray(array, copy=True)
        return np.where(self._mask, array, 0)

    @staticmethod
    def from_array(mask: np.ndarray | None) -> "TimeSeriesMask":
        """
        Creates a TimeSeriesMask from an evaluated mask array.

        Args:
            mask: An integer NumPy array or None.

        Returns:
            A TimeSeriesMask instance with the processed mask.
        """

        if mask is None:
            return TimeSeriesMask(None)
        return TimeSeriesMask((np.asarray(mask) != 0).astype(int))
