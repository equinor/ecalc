from abc import ABC, abstractmethod

from libecalc.common.time_utils import Periods


class TimeSeriesVariable(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def get_values(self) -> list[float]: ...

    @abstractmethod
    def get_periods(self) -> Periods: ...
