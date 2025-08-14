from abc import ABC, abstractmethod

import numpy as np


class TimeSeriesPowerLossFactor(ABC):
    """
    Interface for evaluating power loss factor time series.

    Implementations should provide methods to evaluate and return
    power loss factor values.

    """

    @abstractmethod
    def get_values(self, length=None) -> list[float]:
        """
        Returns the evaluated power loss factor values as a list.
        """
        pass

    @abstractmethod
    def apply(self, energy_usage: list[float | None] | np.ndarray) -> list[float]:
        """
        Apply the power loss factor to the given energy usage.
        """
        pass
