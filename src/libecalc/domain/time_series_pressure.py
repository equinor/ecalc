from abc import ABC, abstractmethod
from collections.abc import Sequence


class TimeSeriesPressure(ABC):
    """
    Interface for evaluating pressure time series.

    Implementations should provide methods to evaluate and return
    pressure values as NumPy arrays.

    """

    @abstractmethod
    def get_values(self) -> Sequence[float]:
        """
        Returns the evaluated pressure values as a NumPy array.
        """
        pass
