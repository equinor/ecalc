from abc import ABC, abstractmethod


class TimeSeriesFlowRate(ABC):
    """
    Interface for evaluating flow rate time series.

    Implementations should provide methods to evaluate and return
    flow rate values as lists, for each stream day.

    """

    @abstractmethod
    def get_stream_day_values(self) -> list[float | None]:
        """
        Returns the evaluated flow rate values for each calendar day.
        """
        pass
