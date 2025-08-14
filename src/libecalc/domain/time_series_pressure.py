from abc import ABC, abstractmethod


class TimeSeriesPressure(ABC):
    """
    Interface for evaluating pressure time series.

    Implementations should provide methods to evaluate and return
    pressure values as NumPy arrays.

    """

    @abstractmethod
    def get_values(self) -> list[float]:
        """
        Returns the evaluated pressure values.
        """
        pass
