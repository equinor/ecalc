from abc import ABC, abstractmethod
from typing import List

from libecalc.common.utils.rates import TimeSeriesFloat
from libecalc.core.result import EcalcModelResult
from libecalc.domain.stream_conditions import StreamConditions
from libecalc.dto import VariablesMap


class BaseConsumer(ABC):
    @abstractmethod
    def evaluate(
        self,
        variables_map: VariablesMap,
        temporal_operational_settings,
    ) -> EcalcModelResult:
        ...


class BaseConsumerWithoutOperationalSettings(ABC):
    id: str

    @abstractmethod
    def get_max_rate(self, inlet_stream: StreamConditions, target_pressure: TimeSeriesFloat) -> List[float]:
        ...

    @abstractmethod
    def get_supported_speeds(self) -> List[int]:
        ...

    @abstractmethod
    def evaluate_with_speed(self, inlet_streams: List[StreamConditions], speed: int) -> EcalcModelResult:
        ...

    @abstractmethod
    def evaluate(self, **kwargs) -> EcalcModelResult:
        ...
