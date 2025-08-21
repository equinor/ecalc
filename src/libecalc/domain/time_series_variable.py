from abc import ABC, abstractmethod


class TimeSeriesVariable(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def get_values(self) -> list[float]: ...
