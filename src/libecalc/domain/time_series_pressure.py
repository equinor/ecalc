from abc import ABC, abstractmethod

import numpy as np


class TimeSeriesPressure(ABC):
    """
    Interface for evaluating pressure time series.

    Implementations should provide methods to evaluate and return
    pressure values as NumPy arrays.

    """

    @abstractmethod
    def get_values(self) -> np.ndarray:
        """
        Returns the evaluated pressure values as a NumPy array.
        """
        pass
