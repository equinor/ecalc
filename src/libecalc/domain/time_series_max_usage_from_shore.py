from abc import ABC, abstractmethod


class TimeSeriesMaxUsageFromShore(ABC):
    """
    Interface for evaluating max usage from shore time series.

    """

    @abstractmethod
    def get_values(self) -> list[float]:
        """
        Returns the evaluated max usage from shore values.
        """
        pass
