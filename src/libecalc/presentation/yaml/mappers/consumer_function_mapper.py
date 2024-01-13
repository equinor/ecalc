from datetime import datetime
from typing import Dict, List, Optional, Set, Union

from libecalc import dto
from libecalc.common.logger import logger
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.common.utils.rates import RateType
from libecalc.dto import (
    CompressorWithTurbine,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.dto.types import EnergyModelType, EnergyUsageType
from libecalc.expression import Expression
from libecalc.presentation.yaml.mappers.utils import (
    resolve_reference,
)
from libecalc.presentation.yaml.validation_errors import DataValidationError
from libecalc.presentation.yaml.yaml_entities import References
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


def _handle_condition_list(conditions: List[str]):
    conditions_with_parentheses = [f"({condition})" for condition in conditions]
    return " {*} ".join(conditions_with_parentheses)


def _map_condition(energy_usage_model: dict) -> Optional[Union[str, int, float]]:
    if EcalcYamlKeywords.condition in energy_usage_model and EcalcYamlKeywords.conditions in energy_usage_model:
        raise DataValidationError(
            data=energy_usage_model,
            message=f"Either {EcalcYamlKeywords.condition} or {EcalcYamlKeywords.conditions}"
            f" should be specified, not both.",
        )

    if EcalcYamlKeywords.condition in energy_usage_model:
        condition_value = energy_usage_model.get(EcalcYamlKeywords.condition)
        if isinstance(condition_value, list):
            logger.warning(
                f"Usage of list with '{EcalcYamlKeywords.condition}'"
                f" keyword is deprecated. Use '{EcalcYamlKeywords.conditions}' instead."
            )
            return _handle_condition_list(condition_value)
        return condition_value
    elif EcalcYamlKeywords.conditions in energy_usage_model:
        return _handle_condition_list(energy_usage_model.get(EcalcYamlKeywords.conditions, []))
    else:
        return None


def _all_equal(items: Set) -> bool:
    return len(items) <= 1


def _get_compressor_train_energy_usage_type(
    compressor_train: dto.CompressorModel,
) -> EnergyUsageType:
    typ = compressor_train.typ

    if typ == EnergyModelType.COMPRESSOR_SAMPLED:
        energy_usage_type = compressor_train.energy_usage_type
    elif typ in (
        EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_KNOWN_STAGES,
        EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_UNKNOWN_STAGES,
        EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT,
    ):
        energy_usage_type = EnergyUsageType.POWER
    elif typ == EnergyModelType.COMPRESSOR_WITH_TURBINE:
        energy_usage_type = EnergyUsageType.FUEL
    elif (
        typ == EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
        or typ == EnergyModelType.SINGLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT
    ):
        energy_usage_type = EnergyUsageType.POWER
    else:
        raise ValueError(f"Invalid compressor model {compressor_train}")

    return energy_usage_type


def _compressor_system_mapper(
    energy_usage_model: Dict, references: References = None
) -> dto.CompressorSystemConsumerFunction:
    compressors = []
    compressor_power_usage_type = set()
    for compressor in energy_usage_model.get(EcalcYamlKeywords.compressor_system_compressors, []):
        compressor_train = resolve_reference(
            value=compressor.get(EcalcYamlKeywords.compressor_system_compressor_sampled_data),
            references=references.models,
        )

        compressors.append(
            dto.CompressorSystemCompressor(
                name=compressor.get(EcalcYamlKeywords.name),
                compressor_train=compressor_train,
            )
        )
        compressor_train_energy_usage_type = _get_compressor_train_energy_usage_type(compressor_train)
        compressor_power_usage_type.add(compressor_train_energy_usage_type)

    # Currently, compressor system (i.e. all of its compressors) is either electrical or turbine driven, and we
    # require all to have the same energy usage type
    # Later, we may allow the different compressors to have different energy usage types
    if not _all_equal(compressor_power_usage_type):
        raise ValueError("All compressors in a system must consume the same kind of energy")

    # Can't infer energy_usage_type when there are no compressors
    energy_usage_type = (
        compressor_power_usage_type.pop() if len(compressor_power_usage_type) == 1 else EnergyUsageType.POWER
    )
    return dto.CompressorSystemConsumerFunction(
        energy_usage_type=energy_usage_type,
        compressors=compressors,
        power_loss_factor=energy_usage_model.get(EcalcYamlKeywords.power_loss_factor),
        condition=_map_condition(energy_usage_model),
        total_system_rate=energy_usage_model.get(EcalcYamlKeywords.consumer_system_total_system_rate),
        operational_settings=[
            dto.CompressorSystemOperationalSetting(
                rates=operational_setting.get(EcalcYamlKeywords.consumer_system_operational_settings_rates),
                rate_fractions=operational_setting.get(
                    EcalcYamlKeywords.consumer_system_operational_settings_rate_fractions
                ),
                suction_pressure=operational_setting.get(
                    EcalcYamlKeywords.consumer_system_operational_settings_suction_pressure
                ),
                suction_pressures=operational_setting.get(
                    EcalcYamlKeywords.consumer_system_operational_settings_suction_pressures
                ),
                discharge_pressure=operational_setting.get(
                    EcalcYamlKeywords.consumer_system_operational_settings_discharge_pressure
                ),
                discharge_pressures=operational_setting.get(
                    EcalcYamlKeywords.consumer_system_operational_settings_discharge_pressures
                ),
                crossover=operational_setting.get(EcalcYamlKeywords.consumer_system_operational_settings_crossover),
            )
            for operational_setting in energy_usage_model.get(EcalcYamlKeywords.consumer_system_operational_settings)
        ],
    )


def _pump_system_mapper(energy_usage_model: Dict, references: References = None) -> dto.PumpSystemConsumerFunction:
    """Remove references from pump system and map yaml to DTO
    :param energy_usage_model: dict representing PumpSystem
    :return:
    """
    pumps = []
    for pump in energy_usage_model.get(EcalcYamlKeywords.pump_system_pumps, []):
        pump_model = resolve_reference(
            pump.get(EcalcYamlKeywords.pump_system_pump_model),
            references=references.models,
        )
        pumps.append(dto.PumpSystemPump(name=pump.get(EcalcYamlKeywords.name), pump_model=pump_model))

    return dto.PumpSystemConsumerFunction(
        power_loss_factor=energy_usage_model.get(EcalcYamlKeywords.power_loss_factor),
        condition=_map_condition(energy_usage_model),
        pumps=pumps,
        fluid_density=energy_usage_model.get(EcalcYamlKeywords.pump_system_fluid_density),
        total_system_rate=energy_usage_model.get(EcalcYamlKeywords.consumer_system_total_system_rate),
        operational_settings=[
            dto.PumpSystemOperationalSetting(
                fluid_densities=operational_setting.get(
                    EcalcYamlKeywords.pump_system_operational_settings_fluid_densities
                ),
                rates=operational_setting.get(EcalcYamlKeywords.consumer_system_operational_settings_rates),
                rate_fractions=operational_setting.get(
                    EcalcYamlKeywords.consumer_system_operational_settings_rate_fractions
                ),
                suction_pressure=operational_setting.get(
                    EcalcYamlKeywords.consumer_system_operational_settings_suction_pressure
                ),
                suction_pressures=operational_setting.get(
                    EcalcYamlKeywords.consumer_system_operational_settings_suction_pressures
                ),
                discharge_pressure=operational_setting.get(
                    EcalcYamlKeywords.consumer_system_operational_settings_discharge_pressure
                ),
                discharge_pressures=operational_setting.get(
                    EcalcYamlKeywords.consumer_system_operational_settings_discharge_pressures
                ),
                crossover=operational_setting.get(EcalcYamlKeywords.consumer_system_operational_settings_crossover),
            )
            for operational_setting in energy_usage_model.get(EcalcYamlKeywords.consumer_system_operational_settings)
        ],
    )


def _direct_mapper(energy_usage_model: Dict, references: References = None) -> dto.DirectConsumerFunction:
    """Change type to match DTOs, then pass the dict on to DTO to automatically create the correct DTO.
    :param energy_usage_model:
    :return:
    """
    is_power_consumer = EcalcYamlKeywords.load in energy_usage_model
    return dto.DirectConsumerFunction(
        energy_usage_type=EnergyUsageType.POWER if is_power_consumer else EnergyUsageType.FUEL,
        load=energy_usage_model.get(EcalcYamlKeywords.load),
        fuel_rate=energy_usage_model.get(EcalcYamlKeywords.fuel_rate),
        condition=_map_condition(energy_usage_model),
        power_loss_factor=energy_usage_model.get(EcalcYamlKeywords.power_loss_factor),
        consumption_rate_type=energy_usage_model.get(EcalcYamlKeywords.direct_consumer_consumption_rate_type)
        or RateType.STREAM_DAY,
    )


def _tabulated_mapper(energy_usage_model: Dict, references: References = None) -> dto.TabulatedConsumerFunction:
    energy_model = resolve_reference(
        energy_usage_model.get(EcalcYamlKeywords.energy_model),
        references.models,
    )
    return dto.TabulatedConsumerFunction(
        energy_usage_type=EnergyUsageType.POWER
        if EnergyUsageType.POWER.value in energy_model.headers
        else EnergyUsageType.FUEL,
        condition=_map_condition(energy_usage_model),
        power_loss_factor=energy_usage_model.get(EcalcYamlKeywords.power_loss_factor),
        model=energy_model,
        variables=[
            dto.Variables(
                name=variable.get(EcalcYamlKeywords.name),
                expression=variable.get(EcalcYamlKeywords.variable_expression),
            )
            for variable in energy_usage_model.get(EcalcYamlKeywords.variables, [])
        ],
    )


def _pump_mapper(energy_usage_model: Dict, references: References = None) -> dto.PumpConsumerFunction:
    energy_model = resolve_reference(
        energy_usage_model.get(EcalcYamlKeywords.energy_model),
        references=references.models,
    )
    return dto.PumpConsumerFunction(
        power_loss_factor=energy_usage_model.get(EcalcYamlKeywords.power_loss_factor),
        condition=_map_condition(energy_usage_model),
        rate_standard_m3_day=energy_usage_model.get(EcalcYamlKeywords.consumer_function_rate),
        suction_pressure=energy_usage_model.get(EcalcYamlKeywords.consumer_function_suction_pressure),
        discharge_pressure=energy_usage_model.get(EcalcYamlKeywords.consumer_function_discharge_pressure),
        fluid_density=energy_usage_model.get(EcalcYamlKeywords.pump_function_fluid_density),
        model=energy_model,
    )


def _variable_speed_compressor_train_multiple_streams_and_pressures_mapper(
    energy_usage_model: Dict, references: References = None
) -> dto.CompressorConsumerFunction:
    compressor_train_model = resolve_reference(
        energy_usage_model.get(EcalcYamlKeywords.models_type_compressor_train_compressor_train_model),
        references=references.models,
    )
    rates_per_stream_config = energy_usage_model.get(EcalcYamlKeywords.models_type_compressor_train_rate_per_stream)
    rates_per_stream = [
        Expression.setup_from_expression(value=rate_expression) for rate_expression in rates_per_stream_config
    ]
    interstage_control_pressure_config = energy_usage_model.get(
        EcalcYamlKeywords.models_type_compressor_train_interstage_control_pressure
    )
    if isinstance(compressor_train_model, CompressorWithTurbine):
        require_interstage_pressure_variable_expression = (
            compressor_train_model.compressor_train.has_interstage_pressure
        )
    elif isinstance(compressor_train_model, VariableSpeedCompressorTrainMultipleStreamsAndPressures):
        require_interstage_pressure_variable_expression = compressor_train_model.has_interstage_pressure
    else:
        require_interstage_pressure_variable_expression = None
    if require_interstage_pressure_variable_expression and interstage_control_pressure_config is None:
        raise ValueError(
            f"Energy model"
            f" {energy_usage_model.get(EcalcYamlKeywords.models_type_compressor_train_compressor_train_model)}"
            f" requires {EcalcYamlKeywords.models_type_compressor_train_interstage_control_pressure} to be defined"
        )
    elif not require_interstage_pressure_variable_expression and interstage_control_pressure_config is not None:
        raise ValueError(
            f"Energy model"
            f" {energy_usage_model.get(EcalcYamlKeywords.models_type_compressor_train_compressor_train_model)}"
            f" does not accept {EcalcYamlKeywords.models_type_compressor_train_interstage_control_pressure}"
            f" to be defined"
        )
    else:
        interstage_control_pressure = (
            Expression.setup_from_expression(value=interstage_control_pressure_config)
            if require_interstage_pressure_variable_expression
            else None
        )
    return dto.CompressorConsumerFunction(
        energy_usage_type=_get_compressor_train_energy_usage_type(compressor_train_model),
        power_loss_factor=energy_usage_model.get(EcalcYamlKeywords.power_loss_factor),
        condition=_map_condition(energy_usage_model),
        rate_standard_m3_day=rates_per_stream,
        suction_pressure=Expression.setup_from_expression(
            value=energy_usage_model.get(EcalcYamlKeywords.consumer_function_suction_pressure)
        ),
        discharge_pressure=Expression.setup_from_expression(
            value=energy_usage_model.get(EcalcYamlKeywords.consumer_function_discharge_pressure)
        ),
        model=compressor_train_model,
        interstage_control_pressure=interstage_control_pressure,
    )


def _compressor_mapper(energy_usage_model: Dict, references: References = None) -> dto.CompressorConsumerFunction:
    energy_model = resolve_reference(
        energy_usage_model.get(EcalcYamlKeywords.energy_model),
        references=references.models,
    )

    compressor_train_energy_usage_type = _get_compressor_train_energy_usage_type(compressor_train=energy_model)

    return dto.CompressorConsumerFunction(
        energy_usage_type=compressor_train_energy_usage_type,
        power_loss_factor=energy_usage_model.get(EcalcYamlKeywords.power_loss_factor),
        condition=_map_condition(energy_usage_model),
        rate_standard_m3_day=energy_usage_model.get(EcalcYamlKeywords.consumer_function_rate),
        suction_pressure=energy_usage_model.get(EcalcYamlKeywords.consumer_function_suction_pressure),
        discharge_pressure=energy_usage_model.get(EcalcYamlKeywords.consumer_function_discharge_pressure),
        model=energy_model,
    )


_consumer_function_mapper = {
    EcalcYamlKeywords.energy_usage_model_type_pump_system: _pump_system_mapper,
    EcalcYamlKeywords.energy_usage_model_type_compressor_system: _compressor_system_mapper,
    EcalcYamlKeywords.energy_usage_model_type_direct: _direct_mapper,
    EcalcYamlKeywords.energy_usage_model_type_tabulated: _tabulated_mapper,
    EcalcYamlKeywords.energy_usage_model_type_pump: _pump_mapper,
    EcalcYamlKeywords.energy_usage_model_type_compressor: _compressor_mapper,
    EcalcYamlKeywords.energy_usage_model_type_variable_speed_compressor_train_multiple_streams_and_pressures: _variable_speed_compressor_train_multiple_streams_and_pressures_mapper,
}


class ConsumerFunctionMapper:
    def __init__(self, references: References, target_period: Period):
        self.__references = references
        self._target_period = target_period

    @staticmethod
    def create_model(model: Dict, references: References = None):
        model_creator = _consumer_function_mapper.get(model[EcalcYamlKeywords.type])
        if model_creator is None:
            raise ValueError(f"Unknown model type: {model.get(EcalcYamlKeywords.type)}")
        return model_creator(model, references)

    def from_yaml_to_dto(self, data: dto.EnergyModel) -> Optional[Dict[datetime, dto.ConsumerFunction]]:
        if data is None:
            return None

        time_adjusted_model = define_time_model_for_period(data, target_period=self._target_period)

        return {
            start_date: ConsumerFunctionMapper.create_model(model, self.__references)
            for start_date, model in time_adjusted_model.items()
        }
