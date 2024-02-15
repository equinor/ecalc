from collections import defaultdict
from typing import Dict, List, Union

import numpy as np
from numpy.typing import NDArray

from libecalc.common.list.list_utils import array_to_list
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesBoolean, TimeSeriesStreamDayRate
from libecalc.core import result as core_results
from libecalc.core.consumers.legacy_consumer.consumer_function import (
    ConsumerFunctionResult,
)
from libecalc.core.consumers.legacy_consumer.system.results import (
    ConsumerSystemConsumerFunctionResult,
)
from libecalc.core.models.results import CompressorTrainResult, PumpModelResult
from libecalc.core.models.results.base import EnergyFunctionResult


def get_single_consumer_models(
    result: ConsumerFunctionResult,
    name: str,
) -> List[core_results.ConsumerModelResult]:
    """Mapping the energy consumer_function_results."""
    model_results = []

    if isinstance(result, ConsumerFunctionResult):
        # Consumer functions have only a single energy function result.
        if isinstance(result.energy_function_result, EnergyFunctionResult):
            model_results.extend(
                map_energy_function_results(
                    result=result.energy_function_result,
                    name=name,
                    time_vector=result.time_vector,
                )
            )
        elif isinstance(result.energy_function_result, list):
            time_vector_index = 0
            for energy_function_result in result.energy_function_result:
                model_results.extend(
                    map_energy_function_results(
                        result=energy_function_result,
                        name=name,
                        time_vector=result.time_vector[
                            time_vector_index : time_vector_index + len(energy_function_result.energy_usage)
                        ],
                    )
                )
                time_vector_index += len(energy_function_result.energy_usage)
        else:
            logger.warning(
                f"Unexpected type: {type(result.energy_function_result)} , can not map result for" f" {name}"
            )
    return model_results


def get_consumer_system_models(
    result: Union[ConsumerSystemConsumerFunctionResult, ConsumerFunctionResult],
    name: str,
) -> List[core_results.ConsumerModelResult]:
    """Warning! Consumer systems does not have the normal:
        EnergyFunctionResult.consumer_model_result.time_slot_results.energy_function_result
    This is set to None, and results are stored under consumer_results. Fix this if possible.
    """
    energy_function_result = []
    if isinstance(result, ConsumerSystemConsumerFunctionResult):
        # Consumer systems functions have multiple consumer results
        time_slot_time_vector_index = 0
        for time_slot_consumer_results in result.consumer_results:
            n_steps = len(time_slot_consumer_results[0].energy_usage)
            time_slot_time_vector = result.time_vector[
                time_slot_time_vector_index : time_slot_time_vector_index + n_steps
            ]
            for consumer_model_result in time_slot_consumer_results:
                energy_function_result.extend(
                    map_energy_function_results(
                        result=consumer_model_result.consumer_model_result,
                        name=consumer_model_result.name,
                        time_vector=time_slot_time_vector,
                    )
                )
            time_slot_time_vector_index += n_steps

    else:
        logger.warning(f"Unexpected type: {type(result)} , can not map result for {name}")

    return energy_function_result


def get_operational_settings_results_from_consumer_result(
    result: Union[ConsumerSystemConsumerFunctionResult, ConsumerFunctionResult], parent_id: str
) -> Dict[int, List[core_results.ConsumerModelResult]]:
    operational_settings_results = defaultdict(list)
    if isinstance(result, ConsumerSystemConsumerFunctionResult):
        # Consumer systems functions have multiple consumer results
        time_slot_time_vector_index = 0
        n_steps = 0
        for time_slot_operational_settings_results in result.operational_settings_results:
            for i, operational_settings_result in enumerate(time_slot_operational_settings_results):
                for consumer_model_result in operational_settings_result.consumer_results:
                    n_steps = len(consumer_model_result.energy_usage)
                    time_slot_time_vector = result.time_vector[
                        time_slot_time_vector_index : time_slot_time_vector_index + n_steps
                    ]
                    if isinstance(consumer_model_result.consumer_model_result, EnergyFunctionResult):
                        consumer_specific_consumer_results = map_energy_function_results(
                            result=consumer_model_result.consumer_model_result,
                            name=consumer_model_result.name,
                            time_vector=time_slot_time_vector,
                        )
                        operational_settings_results[i].extend(consumer_specific_consumer_results)
                    else:
                        logger.warning(
                            f"Unexpected type: {type(consumer_model_result.consumer_model_result)},"
                            f" can not map result for {parent_id}"
                        )
            time_slot_time_vector_index += n_steps

    return operational_settings_results


def map_energy_function_results(
    result: EnergyFunctionResult,
    time_vector: NDArray[np.float64],
    name: str,
) -> List[core_results.ConsumerModelResult]:
    """Returns a list of results that are specific to each consumer. This can be details for compressor trains with
    chart results, pump results, or other results. We will need to add other details below here.
    """
    time_vector = array_to_list(time_vector)

    energy_function_results = []
    if isinstance(result, CompressorTrainResult):
        power = (
            TimeSeriesStreamDayRate(
                timesteps=time_vector,
                values=result.power,
                unit=result.power_unit,
            )
            if result.power is not None
            else None
        )
        energy_usage = TimeSeriesStreamDayRate(
            timesteps=time_vector,
            values=result.energy_usage,
            unit=result.energy_usage_unit,
        )
        energy_function_results.append(
            core_results.CompressorModelResult(
                name=name,
                timesteps=time_vector,
                is_valid=TimeSeriesBoolean(
                    timesteps=time_vector,
                    values=result.is_valid,
                    unit=Unit.NONE,
                ),
                energy_usage=energy_usage,
                power=power,
                rate_sm3_day=result.rate_sm3_day,
                stage_results=result.stage_results,
                failure_status=result.failure_status,
                turbine_result=result.turbine_result,
                max_standard_rate=result.max_standard_rate,
            )
        )
    elif isinstance(result, PumpModelResult):
        # This is meant for ENERGY_USAGE_MODELS of TYPE Pump
        energy_function_results.append(
            core_results.PumpModelResult(
                name=name,
                timesteps=time_vector,
                is_valid=TimeSeriesBoolean(
                    timesteps=time_vector,
                    values=result.is_valid,
                    unit=Unit.NONE,
                ),
                power=TimeSeriesStreamDayRate(
                    timesteps=time_vector,
                    values=result.power,
                    unit=result.power_unit,
                )
                if result.power is not None
                else None,
                energy_usage=TimeSeriesStreamDayRate(
                    timesteps=time_vector,
                    values=result.energy_usage,
                    unit=result.energy_usage_unit,
                ),
                inlet_liquid_rate_m3_per_day=result.rate,
                inlet_pressure_bar=result.suction_pressure,
                outlet_pressure_bar=result.discharge_pressure,
                operational_head=result.operational_head,
            )
        )
    else:
        energy_function_results.append(
            core_results.GenericModelResult(
                name=name,
                timesteps=time_vector,
                is_valid=TimeSeriesBoolean(
                    timesteps=time_vector,
                    values=result.is_valid,
                    unit=Unit.NONE,
                ),
                power=TimeSeriesStreamDayRate(
                    timesteps=time_vector,
                    values=result.power,
                    unit=result.power_unit,
                )
                if result.power is not None
                else None,
                energy_usage=TimeSeriesStreamDayRate(
                    timesteps=time_vector,
                    values=result.energy_usage,
                    unit=result.energy_usage_unit,
                ),
            )
        )
    return energy_function_results
