import itertools
import math
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from typing import Union, assert_never

import numpy as np
from numpy.typing import NDArray

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.list.list_utils import array_to_list
from libecalc.common.logger import logger
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    Rates,
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesInt,
    TimeSeriesStreamDayRate,
)
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.consumers.base import BaseConsumer
from libecalc.core.consumers.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.core.consumers.legacy_consumer.result_mapper import (
    get_consumer_system_models,
    get_operational_settings_results_from_consumer_result,
    get_single_consumer_models,
)
from libecalc.core.consumers.legacy_consumer.system import (
    ConsumerSystemConsumerFunctionResult,
)
from libecalc.core.models.results import CompressorTrainResult
from libecalc.core.result import ConsumerSystemResult, EcalcModelResult
from libecalc.core.result.results import (
    CompressorResult,
    ConsumerModelResult,
    GenericComponentResult,
    PumpResult,
)
from libecalc.expression import Expression


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


class Consumer(BaseConsumer):
    def __init__(
        self,
        id: str,
        name: str,
        component_type: ComponentType,
        consumes: ConsumptionType,
        regularity: TemporalModel[Expression],
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

    def map_model_result(self, model_result: Union[ConsumerOrSystemFunctionResult]) -> list[ConsumerModelResult]:
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
        aggregated_result: Union[ConsumerOrSystemFunctionResult],
    ) -> ConsumerResult:
        if self.component_type in [ComponentType.PUMP_SYSTEM, ComponentType.COMPRESSOR_SYSTEM]:
            operational_settings_used = get_operational_settings_used_from_consumer_result(result=aggregated_result)
            operational_settings_used.values = self.reindex_periods(
                values=operational_settings_used.values,
                periods=aggregated_result.periods,
                new_periods=periods,
                fillna=-1,
            ).tolist()
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
            ).reindex(new_periods=periods)

            inlet_pressure_time_series = TimeSeriesFloat(
                periods=aggregated_result.periods,
                values=aggregated_result.energy_function_result.suction_pressure,
                unit=Unit.BARA,
            ).reindex(new_periods=periods)

            outlet_pressure_time_series = TimeSeriesFloat(
                periods=aggregated_result.periods,
                values=aggregated_result.energy_function_result.discharge_pressure,
                unit=Unit.BARA,
            ).reindex(new_periods=periods)

            operational_head_time_series = TimeSeriesFloat(
                periods=aggregated_result.periods,
                values=aggregated_result.energy_function_result.operational_head,
                unit=Unit.POLYTROPIC_HEAD_JOULE_PER_KG,
            ).reindex(new_periods=periods)

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
                recirculation_loss = aggregated_result.energy_function_result.recirculation_loss
                recirculation_loss = array_to_list(
                    self.reindex_periods(
                        values=recirculation_loss,
                        periods=aggregated_result.periods,
                        new_periods=periods,
                    )
                )
                rate_exceeds_maximum = aggregated_result.energy_function_result.rate_exceeds_maximum
                rate_exceeds_maximum = array_to_list(
                    self.reindex_periods(
                        values=rate_exceeds_maximum,
                        periods=aggregated_result.periods,
                        new_periods=periods,
                    )
                )
            else:
                recirculation_loss = [math.nan] * len(periods)
                rate_exceeds_maximum = [False] * len(periods)

            consumer_result = CompressorResult(
                id=self.id,
                periods=periods,
                is_valid=is_valid,
                energy_usage=energy_usage,
                power=power_usage,
                recirculation_loss=TimeSeriesStreamDayRate(
                    periods=periods,
                    values=recirculation_loss,
                    unit=Unit.MEGA_WATT,
                ),
                rate_exceeds_maximum=TimeSeriesBoolean(periods=periods, values=rate_exceeds_maximum, unit=Unit.NONE),
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
        regularity = list(expression_evaluator.evaluate(expression=self.regularity))

        # NOTE! This function may not handle regularity 0
        consumer_function_results = self.evaluate_consumer_temporal_model(
            expression_evaluator=expression_evaluator,
            regularity=regularity,
        )

        aggregated_consumer_function_result = self.aggregate_consumer_function_results(
            consumer_function_results=consumer_function_results,
        )

        energy_usage = self.reindex_periods(
            values=aggregated_consumer_function_result.energy_usage,
            periods=aggregated_consumer_function_result.periods,
            new_periods=expression_evaluator.get_periods(),
        )

        valid_periods = self.reindex_periods(
            values=aggregated_consumer_function_result.is_valid,
            periods=aggregated_consumer_function_result.periods,
            new_periods=expression_evaluator.get_periods(),
            fillna=True,  # Time-step is valid if not calculated.
        ).astype(bool)

        extrapolations = ~valid_periods
        energy_usage[extrapolations] = np.nan
        energy_usage = Rates.forward_fill_nan_values(rates=energy_usage)

        # By convention, we change remaining NaN-values to 0 regardless of extrapolation
        energy_usage = np.nan_to_num(energy_usage)

        if self.consumes == ConsumptionType.FUEL:
            power_time_series = None
            if aggregated_consumer_function_result.power is not None:
                power = self.reindex_periods(
                    values=aggregated_consumer_function_result.power,
                    periods=aggregated_consumer_function_result.periods,
                    new_periods=expression_evaluator.get_periods(),
                )
                power_time_series = TimeSeriesStreamDayRate(
                    periods=expression_evaluator.get_periods(),
                    values=array_to_list(power),
                    unit=Unit.MEGA_WATT,
                )
            energy_usage_time_series = TimeSeriesStreamDayRate(
                periods=expression_evaluator.get_periods(),
                values=array_to_list(energy_usage),
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            )

        elif self.consumes == ConsumptionType.ELECTRICITY:
            energy_usage_time_series = TimeSeriesStreamDayRate(
                periods=expression_evaluator.get_periods(),
                values=array_to_list(energy_usage),
                unit=Unit.MEGA_WATT,
            )

            power_time_series = energy_usage_time_series.model_copy()
        else:
            assert_never(self.consumes)

        is_valid = TimeSeriesBoolean(
            periods=expression_evaluator.get_periods(),
            values=array_to_list(valid_periods),
            unit=Unit.NONE,
        )

        consumer_result = self.get_consumer_result(
            periods=expression_evaluator.get_periods(),
            energy_usage=energy_usage_time_series,
            power_usage=power_time_series,
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
        regularity: list[float],
    ) -> list[ConsumerOrSystemFunctionResult]:
        """Evaluate each of the models in the temporal model for this consumer."""
        results = []
        for period, consumer_model in self._consumer_time_function.items():
            if Period.intersects(period, expression_evaluator.get_period()):
                start_index, end_index = period.get_period_indices(expression_evaluator.get_periods())
                regularity_this_period = regularity[start_index:end_index]
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

    @staticmethod
    def reindex_periods(
        values: Iterable[Union[str, float]],
        periods: Iterable[Period],
        new_periods: Iterable[Period],
        fillna: Union[float, str] = 0.0,
    ) -> NDArray[np.float64]:
        """Based on a consumer time function result (EnergyFunctionResult), the corresponding time vector and
        the consumer time vector, we calculate the actual consumer (consumption) rate.
        """
        new_values: defaultdict[Period, Union[float, str]] = defaultdict(float)
        new_values.update({t: fillna for t in new_periods})
        for t, v in zip(periods, values):
            if t in new_values:
                new_values[t] = v
            else:
                logger.warning(
                    "Reindexing consumer time vector and losing data. This should not happen."
                    " Please contact eCalc support."
                )

        return np.array([rate_sum for time, rate_sum in sorted(new_values.items())])

    @staticmethod
    def reindex_time_vector(
        values: Iterable[Union[str, float]],
        time_vector: Iterable[datetime],
        new_time_vector: Iterable[datetime],
        fillna: Union[float, str] = 0.0,
    ) -> NDArray[np.float64]:
        """Based on a consumer time function result (EnergyFunctionResult), the corresponding time vector and
        the consumer time vector, we calculate the actual consumer (consumption) rate.
        """
        new_values: defaultdict[datetime, Union[float, str]] = defaultdict(float)
        new_values.update({t: fillna for t in new_time_vector})
        for t, v in zip(time_vector, values):
            if t in new_values:
                new_values[t] = v
            else:
                logger.warning(
                    "Reindexing consumer time vector and losing data. This should not happen."
                    " Please contact eCalc support."
                )

        return np.array([rate_sum for time, rate_sum in sorted(new_values.items())])
