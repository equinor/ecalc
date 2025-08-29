from abc import ABC, abstractmethod


class TimeSeriesCableLoss(ABC):
    """
    Interface for evaluating cable loss time series.

    """

    @abstractmethod
    def get_values(self) -> list[float]:
        """
        Returns the evaluated cable loss values.
        """
        pass
