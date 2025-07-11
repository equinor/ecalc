from abc import ABC, abstractmethod
from collections.abc import Sequence


class TimeSeriesFlowRate(ABC):
    """
    Interface for evaluating flow rate time series.

    Implementations should provide methods to evaluate and return
    flow rate values as NumPy arrays, for each stream day.

    """

    @abstractmethod
    def get_stream_day_values(self) -> Sequence[float]:
        """
        Returns the evaluated flow rate values for each calendar day as a NumPy array.
        """
        pass
