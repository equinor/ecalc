from abc import ABC, abstractmethod


class TimeSeriesEfficiencyLoss(ABC):
    """
    Interface for evaluating cable loss time series.

    """

    @abstractmethod
    def get_values(self) -> list[float]:
        """
        Returns the evaluated values for efficiency loss constant.
        """
        pass
