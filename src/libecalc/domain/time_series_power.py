from abc import ABC, abstractmethod
from collections.abc import Sequence


class TimeSeriesPower(ABC):
    """
    Interface for evaluating power time series.

    Implementations should provide methods to evaluate and return
    power values as lists, for each stream day.

    """

    @abstractmethod
    def get_stream_day_values(self) -> Sequence[float | None]:
        """
        Returns the evaluated power values for each calendar.
        """
        pass
