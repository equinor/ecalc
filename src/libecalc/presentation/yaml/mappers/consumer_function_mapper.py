from typing import Protocol

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.common.utils.rates import RateType
from libecalc.domain.process.compressor.dto import (
    CompressorConsumerFunction,
    CompressorWithTurbine,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.domain.process.compressor.dto.model_types import CompressorModelTypes
from libecalc.domain.process.dto import (
    ConsumerFunction,
    DirectConsumerFunction,
    TabulatedConsumerFunction,
    Variables,
)
from libecalc.domain.process.dto.consumer_system import (
    CompressorSystemCompressor,
    CompressorSystemConsumerFunction,
    CompressorSystemOperationalSetting,
    PumpSystemConsumerFunction,
    PumpSystemOperationalSetting,
    PumpSystemPump,
)
from libecalc.domain.process.pump.pump_consumer_function import PumpConsumerFunction
from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model import (
    YamlElectricityEnergyUsageModel,
    YamlEnergyUsageModelCompressor,
    YamlEnergyUsageModelCompressorSystem,
    YamlEnergyUsageModelCompressorTrainMultipleStreams,
    YamlEnergyUsageModelDirect,
    YamlEnergyUsageModelPump,
    YamlEnergyUsageModelPumpSystem,
    YamlEnergyUsageModelTabulated,
    YamlFuelEnergyUsageModel,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


def _handle_condition_list(conditions: list[str]):
    conditions_with_parentheses = [f"({condition})" for condition in conditions]
    return " {*} ".join(conditions_with_parentheses)


class ConditionedModel(Protocol):
    condition: YamlExpressionType
    conditions: list[YamlExpressionType]


def _map_condition(energy_usage_model: ConditionedModel) -> str | int | float | None:
    if energy_usage_model.condition:
        condition_value = energy_usage_model.condition
        return condition_value
    elif energy_usage_model.conditions:
        return _handle_condition_list(energy_usage_model.conditions)
    else:
        return None


def _all_equal(items: set) -> bool:
    return len(items) <= 1


def _get_compressor_train_energy_usage_type(
    compressor_train: CompressorModelTypes,
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
    energy_usage_model: YamlEnergyUsageModelCompressorSystem, references: ReferenceService
) -> CompressorSystemConsumerFunction:
    compressors = []
    compressor_power_usage_type = set()
    for compressor in energy_usage_model.compressors:
        compressor_train = references.get_compressor_model(compressor.compressor_model)

        compressors.append(
            CompressorSystemCompressor(
                name=compressor.name,
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
    return CompressorSystemConsumerFunction(
        energy_usage_type=energy_usage_type,
        compressors=compressors,
        power_loss_factor=energy_usage_model.power_loss_factor,
        condition=_map_condition(energy_usage_model),
        total_system_rate=energy_usage_model.total_system_rate,
        operational_settings=[
            CompressorSystemOperationalSetting(
                rates=operational_setting.rates,
                rate_fractions=operational_setting.rate_fractions,
                suction_pressure=operational_setting.suction_pressure,
                suction_pressures=operational_setting.suction_pressures,
                discharge_pressure=operational_setting.discharge_pressure,
                discharge_pressures=operational_setting.discharge_pressures,
                crossover=operational_setting.crossover,
            )
            for operational_setting in energy_usage_model.operational_settings
        ],
    )


def _pump_system_mapper(
    energy_usage_model: YamlEnergyUsageModelPumpSystem, references: ReferenceService
) -> PumpSystemConsumerFunction:
    """Remove references from pump system and map yaml to DTO
    :param energy_usage_model: dict representing PumpSystem
    :return:
    """
    pumps = []
    for pump in energy_usage_model.pumps:
        pump_model = references.get_pump_model(pump.chart)
        pumps.append(PumpSystemPump(name=pump.name, pump_model=pump_model))

    return PumpSystemConsumerFunction(
        power_loss_factor=energy_usage_model.power_loss_factor,
        condition=_map_condition(energy_usage_model),
        pumps=pumps,
        fluid_density=energy_usage_model.fluid_density,
        total_system_rate=energy_usage_model.total_system_rate,
        operational_settings=[
            PumpSystemOperationalSetting(
                fluid_densities=operational_setting.fluid_densities,
                rates=operational_setting.rates,
                rate_fractions=operational_setting.rate_fractions,
                suction_pressure=operational_setting.suction_pressure,
                suction_pressures=operational_setting.suction_pressures,
                discharge_pressure=operational_setting.discharge_pressure,
                discharge_pressures=operational_setting.discharge_pressures,
                crossover=operational_setting.crossover,
            )
            for operational_setting in energy_usage_model.operational_settings
        ],
    )


def _direct_mapper(
    energy_usage_model: YamlEnergyUsageModelDirect, references: ReferenceService
) -> DirectConsumerFunction:
    """Change type to match DTOs, then pass the dict on to DTO to automatically create the correct DTO.
    :param energy_usage_model:
    :return:
    """
    is_power_consumer = energy_usage_model.load is not None
    return DirectConsumerFunction(
        energy_usage_type=EnergyUsageType.POWER if is_power_consumer else EnergyUsageType.FUEL,
        load=energy_usage_model.load,
        fuel_rate=energy_usage_model.fuel_rate,
        condition=_map_condition(energy_usage_model),
        power_loss_factor=energy_usage_model.power_loss_factor,
        consumption_rate_type=energy_usage_model.consumption_rate_type or RateType.STREAM_DAY,
    )


def _tabulated_mapper(
    energy_usage_model: YamlEnergyUsageModelTabulated, references: ReferenceService
) -> TabulatedConsumerFunction:
    energy_model = references.get_tabulated_model(energy_usage_model.energy_function)
    return TabulatedConsumerFunction(
        energy_usage_type=EnergyUsageType.POWER
        if EnergyUsageType.POWER.value in energy_model.headers
        else EnergyUsageType.FUEL,
        condition=_map_condition(energy_usage_model),
        power_loss_factor=energy_usage_model.power_loss_factor,
        model=energy_model,
        variables=[
            Variables(
                name=variable.name,
                expression=variable.expression,
            )
            for variable in energy_usage_model.variables
        ],
    )


def _pump_mapper(energy_usage_model: YamlEnergyUsageModelPump, references: ReferenceService) -> PumpConsumerFunction:
    energy_model = references.get_pump_model(energy_usage_model.energy_function)
    return PumpConsumerFunction(
        power_loss_factor=energy_usage_model.power_loss_factor,
        condition=_map_condition(energy_usage_model),
        rate_standard_m3_day=energy_usage_model.rate,
        suction_pressure=energy_usage_model.suction_pressure,
        discharge_pressure=energy_usage_model.discharge_pressure,
        fluid_density=energy_usage_model.fluid_density,
        model=energy_model,
    )


def _variable_speed_compressor_train_multiple_streams_and_pressures_mapper(
    energy_usage_model: YamlEnergyUsageModelCompressorTrainMultipleStreams, references: ReferenceService
) -> CompressorConsumerFunction:
    compressor_train_model = references.get_compressor_model(energy_usage_model.compressor_train_model)
    rates_per_stream = [
        Expression.setup_from_expression(value=rate_expression)
        for rate_expression in energy_usage_model.rate_per_stream
    ]
    interstage_control_pressure_config = energy_usage_model.interstage_control_pressure
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
            f" {energy_usage_model.compressor_train_model}"
            f" requires {EcalcYamlKeywords.models_type_compressor_train_interstage_control_pressure} to be defined"
        )
    elif not require_interstage_pressure_variable_expression and interstage_control_pressure_config is not None:
        raise ValueError(
            f"Energy model"
            f" {energy_usage_model.compressor_train_model}"
            f" does not accept {EcalcYamlKeywords.models_type_compressor_train_interstage_control_pressure}"
            f" to be defined"
        )
    else:
        interstage_control_pressure = (
            Expression.setup_from_expression(value=interstage_control_pressure_config)
            if require_interstage_pressure_variable_expression
            else None
        )
    return CompressorConsumerFunction(
        energy_usage_type=_get_compressor_train_energy_usage_type(compressor_train_model),
        power_loss_factor=energy_usage_model.power_loss_factor,
        condition=_map_condition(energy_usage_model),
        rate_standard_m3_day=rates_per_stream,
        suction_pressure=Expression.setup_from_expression(
            value=energy_usage_model.suction_pressure,
        ),
        discharge_pressure=Expression.setup_from_expression(value=energy_usage_model.discharge_pressure),
        model=compressor_train_model,
        interstage_control_pressure=interstage_control_pressure,
    )


def _compressor_mapper(
    energy_usage_model: YamlEnergyUsageModelCompressor, references: ReferenceService
) -> CompressorConsumerFunction:
    energy_model = references.get_compressor_model(energy_usage_model.energy_function)
    compressor_train_energy_usage_type = _get_compressor_train_energy_usage_type(compressor_train=energy_model)

    return CompressorConsumerFunction(
        energy_usage_type=compressor_train_energy_usage_type,
        power_loss_factor=energy_usage_model.power_loss_factor,
        condition=_map_condition(energy_usage_model),
        rate_standard_m3_day=energy_usage_model.rate,
        suction_pressure=energy_usage_model.suction_pressure,
        discharge_pressure=energy_usage_model.discharge_pressure,
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
    def __init__(self, references: ReferenceService, target_period: Period):
        self.__references = references
        self._target_period = target_period

    @staticmethod
    def create_model(
        model: YamlFuelEnergyUsageModel | YamlElectricityEnergyUsageModel,
        references: ReferenceService,
    ):
        model_creator = _consumer_function_mapper.get(model.type)
        if model_creator is None:
            raise ValueError(f"Unknown model type: {model.type}")
        return model_creator(model, references)

    def from_yaml_to_dto(
        self,
        data: (YamlTemporalModel[YamlFuelEnergyUsageModel] | YamlTemporalModel[YamlElectricityEnergyUsageModel]),
    ) -> dict[Period, ConsumerFunction] | None:
        if data is None:
            return None

        time_adjusted_model = define_time_model_for_period(data, target_period=self._target_period)

        return {
            period: ConsumerFunctionMapper.create_model(model, self.__references)
            for period, model in time_adjusted_model.items()
        }
