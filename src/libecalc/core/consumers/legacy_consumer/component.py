import itertools
import math
from collections import defaultdict
from datetime import datetime
from typing import DefaultDict, Iterable, List, Union

import numpy as np
from numpy.typing import NDArray

from libecalc import dto
from libecalc.common.list.list_utils import array_to_list
from libecalc.common.logger import logger
from libecalc.common.temporal_model import TemporalExpression, TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    Rates,
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesInt,
    TimeSeriesStreamDayRate,
)
from libecalc.core.consumers.base import BaseConsumer
from libecalc.core.consumers.legacy_consumer.consumer_function import (
    ConsumerFunctionResult,
)
from libecalc.core.consumers.legacy_consumer.consumer_function_mapper import (
    EnergyModelMapper,
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
from libecalc.dto import VariablesMap
from libecalc.dto.base import ComponentType
from libecalc.dto.types import ConsumptionType


def get_operational_settings_used_from_consumer_result(
    result: ConsumerSystemConsumerFunctionResult,
) -> TimeSeriesInt:
    return TimeSeriesInt(
        timesteps=result.time_vector.tolist(),
        values=result.operational_setting_used.tolist(),
        unit=Unit.NONE,
    )


ConsumerOrSystemFunctionResult = Union[ConsumerSystemConsumerFunctionResult, ConsumerFunctionResult]
ConsumerResult = Union[ConsumerSystemResult, PumpResult, CompressorResult]


class Consumer(BaseConsumer):
    def __init__(
        self,
        consumer_dto: dto.components.Consumer,
    ):
        logger.debug(f"Creating Consumer: {consumer_dto.name}")
        self._consumer_dto = consumer_dto
        self._consumer_time_function = TemporalModel(
            {
                start_time: EnergyModelMapper.from_dto_to_domain(model)
                for start_time, model in consumer_dto.energy_usage_model.items()
            }
        )

    @property
    def id(self):
        return self._consumer_dto.id

    def map_model_result(self, model_result: Union[ConsumerOrSystemFunctionResult]) -> List[ConsumerModelResult]:
        if self._consumer_dto.component_type in [ComponentType.PUMP_SYSTEM, ComponentType.COMPRESSOR_SYSTEM]:
            return get_consumer_system_models(
                model_result,
                name=self._consumer_dto.name,
            )
        else:
            return get_single_consumer_models(
                result=model_result,
                name=self._consumer_dto.name,
            )

    def get_consumer_result(
        self,
        timesteps: List[datetime],
        energy_usage: TimeSeriesStreamDayRate,
        is_valid: TimeSeriesBoolean,
        power_usage: TimeSeriesStreamDayRate,
        aggregated_result: Union[ConsumerOrSystemFunctionResult],
    ) -> ConsumerResult:
        if self._consumer_dto.component_type in [ComponentType.PUMP_SYSTEM, ComponentType.COMPRESSOR_SYSTEM]:
            operational_settings_used = get_operational_settings_used_from_consumer_result(result=aggregated_result)
            operational_settings_used.values = self.reindex_time_vector(
                values=operational_settings_used.values,
                time_vector=aggregated_result.time_vector,
                new_time_vector=timesteps,
                fillna=-1,
            ).tolist()
            operational_settings_used.timesteps = timesteps

            operational_settings_result = get_operational_settings_results_from_consumer_result(
                aggregated_result, parent_id=self._consumer_dto.id
            )

            # convert to 1-based index
            operational_settings_result = {i + 1: result for i, result in operational_settings_result.items()}
            operational_settings_used.values = [i + 1 for i in operational_settings_used.values]

            consumer_result = ConsumerSystemResult(
                id=self._consumer_dto.id,
                timesteps=timesteps,
                is_valid=is_valid,
                power=power_usage,
                energy_usage=energy_usage,
                operational_settings_used=operational_settings_used,
                operational_settings_results=operational_settings_result,
            )

        elif self._consumer_dto.component_type == ComponentType.PUMP:
            # Using generic consumer result as pump has no specific results currently

            inlet_rate_time_series = TimeSeriesStreamDayRate(
                timesteps=aggregated_result.time_vector.tolist(),
                values=aggregated_result.energy_function_result.rate,
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            ).reindex(new_time_vector=timesteps)

            inlet_pressure_time_series = TimeSeriesFloat(
                timesteps=aggregated_result.time_vector.tolist(),
                values=aggregated_result.energy_function_result.suction_pressure,
                unit=Unit.BARA,
            ).reindex(new_time_vector=timesteps)

            outlet_pressure_time_series = TimeSeriesFloat(
                timesteps=aggregated_result.time_vector.tolist(),
                values=aggregated_result.energy_function_result.discharge_pressure,
                unit=Unit.BARA,
            ).reindex(new_time_vector=timesteps)

            operational_head_time_series = TimeSeriesFloat(
                timesteps=aggregated_result.time_vector.tolist(),
                values=aggregated_result.energy_function_result.operational_head,
                unit=Unit.POLYTROPIC_HEAD_JOULE_PER_KG,
            ).reindex(new_time_vector=timesteps)

            consumer_result = PumpResult(
                id=self._consumer_dto.id,
                timesteps=timesteps,
                is_valid=is_valid,
                energy_usage=energy_usage,
                power=power_usage,
                inlet_liquid_rate_m3_per_day=inlet_rate_time_series,
                inlet_pressure_bar=inlet_pressure_time_series,
                outlet_pressure_bar=outlet_pressure_time_series,
                operational_head=operational_head_time_series,
            )
        elif self._consumer_dto.component_type == ComponentType.COMPRESSOR:
            # All energy_function_results should be CompressorTrainResult,
            # if not the consumer should not have COMPRESSOR type.
            if isinstance(aggregated_result.energy_function_result, CompressorTrainResult):
                recirculation_loss = aggregated_result.energy_function_result.recirculation_loss
                recirculation_loss = array_to_list(
                    self.reindex_time_vector(
                        values=recirculation_loss,
                        time_vector=aggregated_result.time_vector,
                        new_time_vector=timesteps,
                    )
                )
                rate_exceeds_maximum = aggregated_result.energy_function_result.rate_exceeds_maximum
                rate_exceeds_maximum = array_to_list(
                    self.reindex_time_vector(
                        values=rate_exceeds_maximum,
                        time_vector=aggregated_result.time_vector,
                        new_time_vector=timesteps,
                    )
                )
                outlet_pressure_before_choking = (
                    aggregated_result.energy_function_result.outlet_pressure_before_choking
                    if aggregated_result.energy_function_result.outlet_pressure_before_choking is not None
                    else [math.nan] * len(timesteps)
                )

                outlet_pressure_before_choking = array_to_list(
                    self.reindex_time_vector(
                        values=outlet_pressure_before_choking,
                        time_vector=aggregated_result.time_vector,
                        new_time_vector=timesteps,
                    )
                )
            else:
                recirculation_loss = [math.nan] * len(timesteps)
                rate_exceeds_maximum = [False] * len(timesteps)
                outlet_pressure_before_choking = [math.nan] * len(timesteps)

            consumer_result = CompressorResult(
                id=self._consumer_dto.id,
                timesteps=timesteps,
                is_valid=is_valid,
                energy_usage=energy_usage,
                power=power_usage,
                recirculation_loss=TimeSeriesStreamDayRate(
                    timesteps=timesteps,
                    values=recirculation_loss,
                    unit=Unit.MEGA_WATT,
                ),
                rate_exceeds_maximum=TimeSeriesBoolean(
                    timesteps=timesteps, values=rate_exceeds_maximum, unit=Unit.NONE
                ),
                outlet_pressure_before_choking=TimeSeriesFloat(
                    timesteps=timesteps, values=outlet_pressure_before_choking, unit=Unit.BARA
                ),
            )

        else:
            consumer_result = GenericComponentResult(
                id=self._consumer_dto.id,
                timesteps=timesteps,
                is_valid=is_valid,
                energy_usage=energy_usage,
                power=power_usage,
            )
        return consumer_result

    def evaluate(
        self,
        variables_map: VariablesMap,
    ) -> EcalcModelResult:
        """Warning! We are converting energy usage to NaN when the energy usage models has invalid timesteps. this will
        probably be changed soon.
        """
        logger.debug(f"Evaluating consumer: {self._consumer_dto.name}")
        regularity = TemporalExpression.evaluate(
            temporal_expression=TemporalModel(self._consumer_dto.regularity),
            variables_map=variables_map,
        )

        # NOTE! This function may not handle regularity 0
        consumer_function_results = self.evaluate_consumer_temporal_model(
            variables_map=variables_map,
            regularity=regularity,
        )

        aggregated_consumer_function_result = self.aggregate_consumer_function_results(
            consumer_function_results=consumer_function_results,
        )

        energy_usage = self.reindex_time_vector(
            values=aggregated_consumer_function_result.energy_usage,
            time_vector=aggregated_consumer_function_result.time_vector,
            new_time_vector=variables_map.time_vector,
        )

        valid_timesteps = self.reindex_time_vector(
            values=aggregated_consumer_function_result.is_valid,
            time_vector=aggregated_consumer_function_result.time_vector,
            new_time_vector=variables_map.time_vector,
            fillna=True,  # Time-step is valid if not calculated.
        ).astype(bool)

        extrapolations = ~valid_timesteps
        energy_usage[extrapolations] = np.nan
        energy_usage = Rates.forward_fill_nan_values(rates=energy_usage)

        # By convention, we change remaining NaN-values to 0 regardless of extrapolation
        energy_usage = np.nan_to_num(energy_usage)

        if self._consumer_dto.consumes == ConsumptionType.FUEL:
            power_time_series = None
            if aggregated_consumer_function_result.power is not None:
                power = self.reindex_time_vector(
                    values=aggregated_consumer_function_result.power,
                    time_vector=aggregated_consumer_function_result.time_vector,
                    new_time_vector=variables_map.time_vector,
                )
                power_time_series = TimeSeriesStreamDayRate(
                    timesteps=variables_map.time_vector,
                    values=array_to_list(power),
                    unit=Unit.MEGA_WATT,
                )
            energy_usage_time_series = TimeSeriesStreamDayRate(
                timesteps=variables_map.time_vector,
                values=array_to_list(energy_usage),
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            )

        elif self._consumer_dto.consumes == ConsumptionType.ELECTRICITY:
            energy_usage_time_series = TimeSeriesStreamDayRate(
                timesteps=variables_map.time_vector,
                values=array_to_list(energy_usage),
                unit=Unit.MEGA_WATT,
            )

            power_time_series = energy_usage_time_series.model_copy()
        else:
            raise ValueError(f"Consuming '{self._consumer_dto.consumes}' is not implemented.")

        is_valid = TimeSeriesBoolean(
            timesteps=variables_map.time_vector,
            values=array_to_list(valid_timesteps),
            unit=Unit.NONE,
        )

        consumer_result = self.get_consumer_result(
            timesteps=variables_map.time_vector,
            energy_usage=energy_usage_time_series,
            power_usage=power_time_series,
            is_valid=is_valid,
            aggregated_result=aggregated_consumer_function_result,
        )

        if self._consumer_dto.component_type in [ComponentType.PUMP_SYSTEM, ComponentType.COMPRESSOR_SYSTEM]:
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
        variables_map: VariablesMap,
        regularity: List[float],
    ) -> List[ConsumerOrSystemFunctionResult]:
        """Evaluate each of the models in the temporal model for this consumer."""
        results = []
        for period, consumer_model in self._consumer_time_function.items():
            if Period.intersects(period, variables_map.period):
                start_index, end_index = period.get_timestep_indices(variables_map.time_vector)
                regularity_this_period = regularity[start_index:end_index]
                variables_map_this_period = variables_map.get_subset(
                    start_index=start_index,
                    end_index=end_index,
                )
                logger.debug(
                    f"Evaluating {consumer_model.__class__.__name__} with"
                    f" {len(variables_map_this_period.time_vector)} timestep(s) in range"
                    f" [{period}]"
                )
                consumer_function_result = consumer_model.evaluate(
                    variables_map=variables_map_this_period,
                    regularity=regularity_this_period,
                )
                results.append(consumer_function_result)

        return results

    @staticmethod
    def aggregate_consumer_function_results(
        consumer_function_results: List[ConsumerOrSystemFunctionResult],
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
    def reindex_time_vector(
        values: Iterable[Union[str, float]],
        time_vector: Iterable[datetime],
        new_time_vector: Iterable[datetime],
        fillna: Union[float, str] = 0.0,
    ) -> NDArray[np.float64]:
        """Based on a consumer time function result (EnergyFunctionResult), the corresponding time vector and
        the consumer time vector, we calculate the actual consumer (consumption) rate.
        """
        new_values: DefaultDict[datetime, Union[float, str]] = defaultdict(float)
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
