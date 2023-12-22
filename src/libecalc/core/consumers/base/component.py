from abc import ABC, abstractmethod
from typing import List

from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.utils.rates import TimeSeriesFloat
from libecalc.core.consumers.base.result import ConsumerResult

ConsumerID = str


class Consumer(ABC):
    id: ConsumerID

    @abstractmethod
    def get_max_rate(self, inlet_stream: TimeSeriesStreamConditions, target_pressure: TimeSeriesFloat) -> List[float]:
        ...

    @abstractmethod
    def evaluate(self, **kwargs) -> ConsumerResult:
        ...
