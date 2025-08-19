from abc import ABC, abstractmethod

from libecalc.common.time_utils import Periods


class TimeSeriesPressure(ABC):
    """
    Interface for evaluating pressure time series.

    Implementations should provide methods to evaluate and return
    pressure values as NumPy arrays.

    """

    @abstractmethod
    def get_periods(self) -> Periods:
        """
        Returns the periods associated with the flow rate time series.
        This is used to align the flow rate values with the corresponding periods.
        """
        pass

    @abstractmethod
    def get_values(self) -> list[float]:
        """
        Returns the evaluated pressure values.
        """
        pass
