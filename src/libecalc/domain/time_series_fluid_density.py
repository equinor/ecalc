from abc import ABC, abstractmethod


class TimeSeriesFluidDensity(ABC):
    """
    Interface for evaluating fluid density time series.

    """

    @abstractmethod
    def get_values(self) -> list[float]:
        """
        Returns the evaluated fluid density values.
        """
        pass
