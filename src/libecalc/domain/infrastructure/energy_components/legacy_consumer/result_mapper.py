from libecalc.common.logger import logger
from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesBoolean, TimeSeriesStreamDayRate
from libecalc.core.result.results import CompressorModelResult, ConsumerModelResult, GenericModelResult
from libecalc.core.result.results import PumpModelResult as CorePumpModelResult
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import ConsumerFunctionResult
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.results import (
    ConsumerSystemConsumerFunctionResult,
    SystemComponentResult,
)
from libecalc.domain.process.core.results import CompressorTrainResult, PumpModelResult
from libecalc.domain.process.core.results.base import EnergyFunctionResult


def get_single_consumer_models(
    result: ConsumerFunctionResult,
    name: str,
) -> list[ConsumerModelResult]:
    """Mapping the energy consumer_function_results."""
    model_results = []

    if isinstance(result, ConsumerFunctionResult):
        # Consumer functions have only a single energy function result.
        if isinstance(result.energy_function_result, EnergyFunctionResult):
            model_results.extend(
                map_energy_function_results(
                    result=result.energy_function_result,
                    name=name,
                    periods=result.periods,
                )
            )
        elif isinstance(result.energy_function_result, list):
            time_vector_index = 0
            for energy_function_result in result.energy_function_result:
                model_results.extend(
                    map_energy_function_results(
                        result=energy_function_result,
                        name=name,
                        periods=result.periods[
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
    results: list[ConsumerSystemConsumerFunctionResult],
) -> list[ConsumerModelResult]:
    """Warning! Consumer systems does not have the normal:
        EnergyFunctionResult.consumer_model_result.time_slot_results.energy_function_result
    This is set to None, and results are stored under consumer_results. Fix this if possible.
    """
    energy_function_result = []
    # Consumer systems functions have multiple consumer results
    for time_slot_consumer_result in results:
        time_slot_periods = time_slot_consumer_result.periods
        for consumer_model_result in time_slot_consumer_result.consumer_results:
            energy_function_result.extend(
                map_energy_function_results(
                    result=consumer_model_result.result,
                    name=consumer_model_result.name,
                    periods=time_slot_periods,
                )
            )

    return energy_function_result


def map_energy_function_results(
    result: EnergyFunctionResult | SystemComponentResult,
    periods: Periods,
    name: str,
) -> list[ConsumerModelResult]:
    """Returns a list of results that are specific to each consumer. This can be details for compressor trains with
    chart results, pump results, or other results. We will need to add other details below here.
    """
    energy_function_results = []
    if isinstance(result, CompressorTrainResult):
        power = (
            TimeSeriesStreamDayRate(
                periods=periods,
                values=result.power,
                unit=result.power_unit,
            )
            if result.power is not None
            else None
        )
        energy_usage = TimeSeriesStreamDayRate(
            periods=periods,
            values=result.energy_usage,
            unit=result.energy_usage_unit,
        )
        energy_function_results.append(
            CompressorModelResult(
                name=name,
                periods=periods,
                is_valid=TimeSeriesBoolean(
                    periods=periods,
                    values=result.is_valid,
                    unit=Unit.NONE,
                ),
                energy_usage=energy_usage,
                power=power,
                rate_sm3_day=list(result.rate_sm3_day) if result.rate_sm3_day is not None else None,  # type: ignore[arg-type]
                stage_results=list(result.stage_results) if result.stage_results is not None else None,
                failure_status=list(result.failure_status) if result.failure_status is not None else None,
                turbine_result=result.turbine_result,
                max_standard_rate=list(result.max_standard_rate) if result.max_standard_rate is not None else None,  # type: ignore[arg-type]
                inlet_stream_condition=result.inlet_stream_condition,
                outlet_stream_condition=result.outlet_stream_condition,
            )
        )
    elif isinstance(result, PumpModelResult):
        # This is meant for ENERGY_USAGE_MODELS of TYPE Pump
        energy_function_results.append(
            CorePumpModelResult(  # type: ignore[arg-type]
                name=name,
                periods=periods,
                is_valid=TimeSeriesBoolean(
                    periods=periods,
                    values=result.is_valid,
                    unit=Unit.NONE,
                ),
                power=TimeSeriesStreamDayRate(
                    periods=periods,
                    values=result.power,
                    unit=result.power_unit,
                )
                if result.power is not None
                else None,
                energy_usage=TimeSeriesStreamDayRate(
                    periods=periods,
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
        assert hasattr(result, "power_unit") and hasattr(result, "energy_usage_unit")
        energy_function_results.append(
            GenericModelResult(  # type: ignore[arg-type]
                name=name,
                periods=periods,
                is_valid=TimeSeriesBoolean(
                    periods=periods,
                    values=result.is_valid,
                    unit=Unit.NONE,
                ),
                power=TimeSeriesStreamDayRate(
                    periods=periods,
                    values=result.power,
                    unit=result.power_unit,
                )
                if result.power is not None
                else None,
                energy_usage=TimeSeriesStreamDayRate(
                    periods=periods,
                    values=result.energy_usage,
                    unit=result.energy_usage_unit,
                ),
            )
        )
    return energy_function_results
