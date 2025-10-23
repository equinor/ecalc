from abc import ABC, abstractmethod


class TimeSeriesUnitPowerAdjustment(ABC):
    """
    Interface for unit power adjustment time series. A unit can be a compressor (stage), pump etc.
    """

    @abstractmethod
    def get_values(self) -> list[float]:
        """
        Returns the evaluated values for power adjustment.
        """
        pass
