from abc import ABC, abstractmethod
from typing import List

from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.utils.rates import TimeSeriesFloat
from libecalc.core.result import EcalcModelResult
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
    def get_max_rate(self, inlet_stream: TimeSeriesStreamConditions, target_pressure: TimeSeriesFloat) -> List[float]:
        ...

    @abstractmethod
    def evaluate(self, **kwargs) -> EcalcModelResult:
        ...
