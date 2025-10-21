from typing import cast

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.logger import logger
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Periods
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import ConsumerSystemResult
from libecalc.core.result.results import CompressorResult, GenericComponentResult, PumpResult
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system import ConsumerSystemConsumerFunctionResult
from libecalc.domain.regularity import Regularity


class Consumer:
    def __init__(
        self,
        id: str,
        name: str,
        component_type: ComponentType,
        consumes: ConsumptionType,
        regularity: Regularity,
        energy_usage_model: TemporalModel[ConsumerFunction],
    ) -> None:
        logger.debug(f"Creating Consumer: {name}")
        self._id = id
        self.name = name
        self.component_type = component_type
        self.consumes: ConsumptionType = consumes
        self.regularity = regularity
        self._consumer_time_function = energy_usage_model

    @property
    def id(self):
        return self._id

    def get_consumer_result(
        self,
        periods: Periods,
        results: list[ConsumerFunctionResult] | list[ConsumerSystemConsumerFunctionResult],
    ) -> ConsumerSystemResult | CompressorResult | PumpResult | GenericComponentResult:
        if self.component_type in [ComponentType.PUMP_SYSTEM, ComponentType.COMPRESSOR_SYSTEM]:
            assert all(isinstance(result, ConsumerSystemConsumerFunctionResult) for result in results)
            results = cast(list[ConsumerSystemConsumerFunctionResult], results)
            consumer_result = ConsumerSystemResult(
                id=self.id,
                periods=periods,
                results=results,
            )
        elif self.component_type == ComponentType.PUMP:
            assert all(isinstance(result, ConsumerFunctionResult) for result in results)
            results = cast(list[ConsumerFunctionResult], results)
            consumer_result = PumpResult(
                id=self.id,
                periods=periods,
                results=results,
            )
        elif self.component_type == ComponentType.COMPRESSOR:
            assert all(isinstance(result, ConsumerFunctionResult) for result in results)
            results = cast(list[ConsumerFunctionResult], results)
            consumer_result = CompressorResult(
                id=self.id,
                periods=periods,
                results=results,
            )
        else:
            assert all(isinstance(result, ConsumerFunctionResult) for result in results)
            results = cast(list[ConsumerFunctionResult], results)
            consumer_result = GenericComponentResult(
                id=self.id,
                periods=periods,
                results=results,
            )
        return consumer_result

    def evaluate(
        self,
        expression_evaluator: ExpressionEvaluator,
    ) -> ConsumerSystemResult | CompressorResult | PumpResult | GenericComponentResult:
        """Warning! We are converting energy usage to NaN when the energy usage models has invalid periods. this will
        probably be changed soon.
        """
        logger.debug(f"Evaluating consumer: {self.name}")

        # NOTE! This function may not handle regularity 0

        consumer_function_results: list[ConsumerSystemConsumerFunctionResult] | list[ConsumerFunctionResult] = []
        for consumer_model in self._consumer_time_function.get_models():
            consumer_function_result = consumer_model.evaluate()
            consumer_function_results.append(consumer_function_result)

        consumer_result = self.get_consumer_result(
            periods=expression_evaluator.get_periods(),
            results=consumer_function_results,
        )

        return consumer_result
