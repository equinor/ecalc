from abc import ABC, abstractmethod

import numpy as np


class TimeSeriesFlowRate(ABC):
    """
    Interface for evaluating flow rate time series.

    Implementations should provide methods to evaluate and return
    flow rate values as NumPy arrays, either for each stream day.

    """

    @abstractmethod
    def get_stream_day_values(self) -> np.ndarray:
        """
        Returns the evaluated flow rate values for each calendar day as a NumPy array.
        """
        pass
