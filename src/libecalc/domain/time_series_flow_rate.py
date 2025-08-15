from abc import ABC, abstractmethod

from libecalc.common.time_utils import Periods


class TimeSeriesFlowRate(ABC):
    """
    Interface for evaluating flow rate time series.

    Implementations should provide methods to evaluate and return
    flow rate values as lists, for each stream day.

    """

    @abstractmethod
    def get_stream_day_values(self) -> list[float | None]:
        """
        Returns the evaluated flow rate values for each stream day.
        """
        pass

    @abstractmethod
    def get_periods(self) -> Periods:
        """
        Returns the periods associated with the flow rate time series.
        This is used to align the flow rate values with the corresponding periods.
        """
        pass
