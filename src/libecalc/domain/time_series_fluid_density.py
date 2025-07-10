from abc import ABC, abstractmethod
from typing import Sequence

import numpy as np


class TimeSeriesFluidDensity(ABC):
    """
    Interface for evaluating fluid density time series.

    """

    @abstractmethod
    def get_values(self) -> Sequence[float]:
        """
        Returns the evaluated fluid density values as a NumPy array.
        """
        pass
