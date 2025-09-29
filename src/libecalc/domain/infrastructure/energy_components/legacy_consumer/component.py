import itertools
from typing import cast

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.logger import logger
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Periods
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import ConsumerSystemResult, EcalcModelResult
from libecalc.core.result.results import CompressorResult, ConsumerModelResult, GenericComponentResult, PumpResult
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.result_mapper import (
    get_consumer_system_models,
    get_single_consumer_models,
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

    def map_model_result(
        self, model_result: ConsumerFunctionResult | ConsumerSystemConsumerFunctionResult
    ) -> list[ConsumerModelResult]:
        if self.component_type in [ComponentType.PUMP_SYSTEM, ComponentType.COMPRESSOR_SYSTEM]:
            return get_consumer_system_models(
                model_result,
                name=self.name,
            )
        else:
            return get_single_consumer_models(
                result=model_result,  # type: ignore[arg-type]
                name=self.name,
            )

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
    ) -> EcalcModelResult:
        """Warning! We are converting energy usage to NaN when the energy usage models has invalid periods. this will
        probably be changed soon.
        """
        logger.debug(f"Evaluating consumer: {self.name}")

        # NOTE! This function may not handle regularity 0
        consumer_function_results = self.evaluate_consumer_temporal_model()

        consumer_result = self.get_consumer_result(
            periods=expression_evaluator.get_periods(),
            results=consumer_function_results,
        )

        aggregated_consumer_function_result = self.aggregate_consumer_function_results(
            consumer_function_results=consumer_function_results,
        )
        if self.component_type in [ComponentType.PUMP_SYSTEM, ComponentType.COMPRESSOR_SYSTEM]:
            model_results = self.map_model_result(aggregated_consumer_function_result)
        else:
            model_results = [self.map_model_result(model_result) for model_result in consumer_function_results]  # type: ignore[misc]
            model_results = list(itertools.chain(*model_results))  # type: ignore[arg-type] # Flatten model results

        return EcalcModelResult(
            component_result=consumer_result,
            models=model_results,
            sub_components=[],
        )

    def evaluate_consumer_temporal_model(
        self,
    ) -> list[ConsumerFunctionResult] | list[ConsumerSystemConsumerFunctionResult]:
        """Evaluate each of the models in the temporal model for this consumer."""
        results = []
        for _period, consumer_model in self._consumer_time_function.items():
            consumer_function_result = consumer_model.evaluate()
            results.append(consumer_function_result)

        return results

    @staticmethod
    def aggregate_consumer_function_results(
        consumer_function_results: list[ConsumerFunctionResult] | list[ConsumerSystemConsumerFunctionResult],
    ) -> ConsumerFunctionResult | ConsumerSystemConsumerFunctionResult:
        merged_result = None
        for consumer_function_result in consumer_function_results:
            if merged_result is None:
                merged_result = consumer_function_result.model_copy(deep=True)
            else:
                merged_result.extend(consumer_function_result)

        if merged_result is None:
            # This will happen if all the energy usage functions are defined outside the parent consumer timeslot(s).
            empty_result = ConsumerFunctionResult.create_empty()
            return empty_result
        return merged_result
