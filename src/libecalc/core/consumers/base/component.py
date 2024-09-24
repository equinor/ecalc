from abc import ABC, abstractmethod
from typing import List

from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.utils.rates import TimeSeriesFloat
from libecalc.common.variables import VariablesMapService
from libecalc.core.result import EcalcModelResult


class BaseConsumer(ABC):
    @abstractmethod
    def evaluate(
        self,
        variables_map: VariablesMapService,
        temporal_operational_settings,
    ) -> EcalcModelResult: ...


class BaseConsumerWithoutOperationalSettings(ABC):
    id: str

    @abstractmethod
    def get_max_rate(
        self, inlet_stream: TimeSeriesStreamConditions, target_pressure: TimeSeriesFloat
    ) -> List[float]: ...

    @abstractmethod
    def evaluate(self, **kwargs) -> EcalcModelResult: ...
