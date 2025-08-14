from abc import ABC, abstractmethod


class TimeSeriesPowerLossFactor(ABC):
    """
    Interface for evaluating power loss factor time series.

    Implementations should provide methods to evaluate and return
    power loss factor values, for each stream day.

    """

    @abstractmethod
    def get_stream_day_values(self) -> list[float]:
        """
        Returns the evaluated power loss factor values for each stream day.
        """
        pass
