from abc import ABC, abstractmethod

import numpy as np


class TimeSeriesFlowRateInterface(ABC):
    """
    Interface for flow rate expressions.
    """

    @abstractmethod
    def get_calendar_day_values(self) -> np.ndarray:
        """
        Returns the flow rate as a float.
        """
        pass

    @abstractmethod
    def get_stream_day_values(self) -> np.ndarray:
        """
        Returns the flow rate as a float.
        """
        pass
