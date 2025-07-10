from abc import ABC, abstractmethod

import numpy as np


class TimeSeriesFlowRateInterface(ABC):
    """
    Interface for flow rate expressions.
    """

    @abstractmethod
    def get_calendar_day_values(self) -> np.ndarray:
        """
        Returns the evaluated flow rate values for each calendar day as a NumPy array.
        """
        pass

    @abstractmethod
    def get_stream_day_values(self) -> np.ndarray:
        """
        Returns the evaluated flow rate values for each calendar day as a NumPy array.
        """
        pass
