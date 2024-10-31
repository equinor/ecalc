from abc import ABC, abstractmethod

from libecalc.common.utils.rates import TimeSeriesFloat
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import EcalcModelResult
from libecalc.domain.stream_conditions import StreamConditions


class BaseConsumer(ABC):
    @abstractmethod
    def evaluate(
        self,
        expression_evaluator: ExpressionEvaluator,
    ) -> EcalcModelResult: ...


class BaseConsumerWithoutOperationalSettings(ABC):
    id: str

    @abstractmethod
    def get_max_rate(self, inlet_stream: StreamConditions, target_pressure: TimeSeriesFloat) -> list[float]: ...

    @abstractmethod
    def evaluate(self, streams: list[StreamConditions]) -> EcalcModelResult: ...
