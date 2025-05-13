import itertools
import math
from typing import Union, assert_never

import numpy as np

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.logger import logger
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.nan_handling import clean_nan_values
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesInt,
    TimeSeriesStreamDayRate,
)
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import ConsumerSystemResult, EcalcModelResult
from libecalc.core.result.results import (
    CompressorResult,
    ConsumerModelResult,
    GenericComponentResult,
    PumpResult,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.result_mapper import (
    get_consumer_system_models,
    get_operational_settings_results_from_consumer_result,
    get_single_consumer_models,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system import (
    ConsumerSystemConsumerFunctionResult,
)
from libecalc.domain.process.core.results import CompressorTrainResult
from libecalc.domain.regularity import Regularity


def get_operational_settings_used_from_consumer_result(
    result: ConsumerSystemConsumerFunctionResult,
) -> TimeSeriesInt:
    return TimeSeriesInt(
        periods=result.periods,
        values=result.operational_setting_used.tolist(),
        unit=Unit.NONE,
    )


ConsumerOrSystemFunctionResult = Union[ConsumerSystemConsumerFunctionResult, ConsumerFunctionResult]
ConsumerResult = Union[ConsumerSystemResult, PumpResult, CompressorResult]


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

    def map_model_result(self, model_result: ConsumerOrSystemFunctionResult) -> list[ConsumerModelResult]:
        if self.component_type in [ComponentType.PUMP_SYSTEM, ComponentType.COMPRESSOR_SYSTEM]:
            return get_consumer_system_models(
                model_result,
                name=self.name,
            )
        else:
            return get_single_consumer_models(
                result=model_result,
                name=self.name,
            )

    def get_consumer_result(
        self,
        periods: Periods,
        energy_usage: TimeSeriesStreamDayRate,
        is_valid: TimeSeriesBoolean,
        power_usage: TimeSeriesStreamDayRate,
        aggregated_result: ConsumerOrSystemFunctionResult,
    ) -> ConsumerResult:
        if self.component_type in [ComponentType.PUMP_SYSTEM, ComponentType.COMPRESSOR_SYSTEM]:
            operational_settings_used = get_operational_settings_used_from_consumer_result(result=aggregated_result)
            operational_settings_used.values = (
                TimeSeriesInt(
                    values=operational_settings_used.values,
                    periods=aggregated_result.periods,
                    unit=Unit.NONE,
                )
                .fill_values_for_new_periods(new_periods=periods, fillna=-1)
                .values
            )
            operational_settings_used.periods = periods

            operational_settings_result = get_operational_settings_results_from_consumer_result(
                aggregated_result, parent_id=self.id
            )

            # convert to 1-based index
            operational_settings_result = {i + 1: result for i, result in operational_settings_result.items()}
            operational_settings_used.values = [i + 1 for i in operational_settings_used.values]

            consumer_result = ConsumerSystemResult(
                id=self.id,
                periods=periods,
                is_valid=is_valid,
                power=power_usage,
                energy_usage=energy_usage,
                operational_settings_used=operational_settings_used,
                operational_settings_results=operational_settings_result,
            )

        elif self.component_type == ComponentType.PUMP:
            # Using generic consumer result as pump has no specific results currently

            inlet_rate_time_series = TimeSeriesStreamDayRate(
                periods=aggregated_result.periods,
                values=aggregated_result.energy_function_result.rate,
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            ).fill_values_for_new_periods(new_periods=periods, fillna=0.0)

            inlet_pressure_time_series = TimeSeriesFloat(
                periods=aggregated_result.periods,
                values=aggregated_result.energy_function_result.suction_pressure,
                unit=Unit.BARA,
            ).fill_values_for_new_periods(new_periods=periods, fillna=0.0)

            outlet_pressure_time_series = TimeSeriesFloat(
                periods=aggregated_result.periods,
                values=aggregated_result.energy_function_result.discharge_pressure,
                unit=Unit.BARA,
            ).fill_values_for_new_periods(new_periods=periods, fillna=0.0)

            operational_head_time_series = TimeSeriesFloat(
                periods=aggregated_result.periods,
                values=aggregated_result.energy_function_result.operational_head,
                unit=Unit.POLYTROPIC_HEAD_JOULE_PER_KG,
            ).fill_values_for_new_periods(new_periods=periods, fillna=0.0)

            consumer_result = PumpResult(
                id=self.id,
                periods=periods,
                is_valid=is_valid,
                energy_usage=energy_usage,
                power=power_usage,
                inlet_liquid_rate_m3_per_day=inlet_rate_time_series,
                inlet_pressure_bar=inlet_pressure_time_series,
                outlet_pressure_bar=outlet_pressure_time_series,
                operational_head=operational_head_time_series,
            )
        elif self.component_type == ComponentType.COMPRESSOR:
            # All energy_function_results should be CompressorTrainResult,
            # if not the consumer should not have COMPRESSOR type.
            if isinstance(aggregated_result.energy_function_result, CompressorTrainResult):
                recirculation_loss = TimeSeriesStreamDayRate(
                    periods=aggregated_result.periods,
                    values=aggregated_result.energy_function_result.recirculation_loss,
                    unit=Unit.MEGA_WATT,
                ).fill_values_for_new_periods(new_periods=periods, fillna=0.0)
                rate_exceeds_maximum = TimeSeriesBoolean(
                    periods=aggregated_result.periods,
                    values=aggregated_result.energy_function_result.rate_exceeds_maximum,
                    unit=Unit.NONE,
                ).fill_values_for_new_periods(new_periods=periods, fillna=False)
            else:
                recirculation_loss = TimeSeriesStreamDayRate(
                    periods=periods,
                    values=[math.nan] * len(periods),
                    unit=Unit.MEGA_WATT,
                )
                rate_exceeds_maximum = TimeSeriesBoolean(
                    periods=aggregated_result.periods,
                    values=[False] * len(periods),
                    unit=Unit.NONE,
                )

            consumer_result = CompressorResult(
                id=self.id,
                periods=periods,
                is_valid=is_valid,
                energy_usage=energy_usage,
                power=power_usage,
                recirculation_loss=recirculation_loss,
                rate_exceeds_maximum=rate_exceeds_maximum,
            )

        else:
            consumer_result = GenericComponentResult(
                id=self.id,
                periods=periods,
                is_valid=is_valid,
                energy_usage=energy_usage,
                power=power_usage,
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
        regularity = self.regularity

        # NOTE! This function may not handle regularity 0
        consumer_function_results = self.evaluate_consumer_temporal_model(
            expression_evaluator=expression_evaluator,
            regularity=regularity,
        )

        aggregated_consumer_function_result = self.aggregate_consumer_function_results(
            consumer_function_results=consumer_function_results,
        )
        energy_usage = TimeSeriesStreamDayRate(
            periods=aggregated_consumer_function_result.periods,
            values=aggregated_consumer_function_result.energy_usage,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        ).fill_values_for_new_periods(new_periods=expression_evaluator.get_periods(), fillna=0.0)

        is_valid = TimeSeriesBoolean(
            periods=aggregated_consumer_function_result.periods,
            values=aggregated_consumer_function_result.is_valid,
            unit=Unit.NONE,
        ).fill_values_for_new_periods(new_periods=expression_evaluator.get_periods(), fillna=True)

        extrapolations = [i for i, _is_valid in enumerate(is_valid.values) if not _is_valid]
        for i in extrapolations:
            energy_usage.values[i] = np.nan

        energy_usage.values = clean_nan_values(np.asarray(energy_usage.values)).tolist()

        if self.consumes == ConsumptionType.FUEL:
            power = None
            if aggregated_consumer_function_result.power is not None:
                power = TimeSeriesStreamDayRate(
                    values=aggregated_consumer_function_result.power,
                    periods=aggregated_consumer_function_result.periods,
                    unit=Unit.MEGA_WATT,
                ).fill_values_for_new_periods(new_periods=expression_evaluator.get_periods(), fillna=0.0)

        elif self.consumes == ConsumptionType.ELECTRICITY:
            energy_usage.unit = Unit.MEGA_WATT

            power = energy_usage.model_copy()
        else:
            assert_never(self.consumes)

        consumer_result = self.get_consumer_result(
            periods=expression_evaluator.get_periods(),
            energy_usage=energy_usage,
            power_usage=power,
            is_valid=is_valid,
            aggregated_result=aggregated_consumer_function_result,
        )

        if self.component_type in [ComponentType.PUMP_SYSTEM, ComponentType.COMPRESSOR_SYSTEM]:
            model_results = self.map_model_result(aggregated_consumer_function_result)
        else:
            model_results = [self.map_model_result(model_result) for model_result in consumer_function_results]
            model_results = list(itertools.chain(*model_results))  # Flatten model results

        return EcalcModelResult(
            component_result=consumer_result,
            models=model_results,
            sub_components=[],
        )

    def evaluate_consumer_temporal_model(
        self,
        expression_evaluator: ExpressionEvaluator,
        regularity: Regularity,
    ) -> list[ConsumerOrSystemFunctionResult]:
        """Evaluate each of the models in the temporal model for this consumer."""
        results = []
        for period, consumer_model in self._consumer_time_function.items():
            if Period.intersects(period, expression_evaluator.get_period()):
                start_index, end_index = period.get_period_indices(expression_evaluator.get_periods())
                regularity_this_period = regularity.time_series.values[start_index:end_index]
                variables_map_this_period = expression_evaluator.get_subset(
                    start_index=start_index,
                    end_index=end_index,
                )
                logger.debug(
                    f"Evaluating {consumer_model.__class__.__name__} with"
                    f" {len(variables_map_this_period.get_time_vector())} timestep(s) in range"
                    f" [{period}]"
                )
                consumer_function_result = consumer_model.evaluate(
                    expression_evaluator=variables_map_this_period,
                    regularity=regularity_this_period,
                )
                results.append(consumer_function_result)

        return results

    @staticmethod
    def aggregate_consumer_function_results(
        consumer_function_results: list[ConsumerOrSystemFunctionResult],
    ) -> ConsumerOrSystemFunctionResult:
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
