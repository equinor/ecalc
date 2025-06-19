import logging
from collections.abc import Callable
from typing import Any, Protocol, assert_never

from libecalc.common.consumer_type import ConsumerType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.common.utils.rates import RateType
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import ConsumerFunction
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.consumer_tabular_energy_function import (
    TabulatedConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.direct_expression_consumer_function import (
    DirectExpressionConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function_mapper import (
    create_compressor_consumer_function,
    create_compressor_system,
    create_pump_consumer_function,
    create_pump_system,
)
from libecalc.domain.process.compressor.dto import (
    CompressorConsumerFunction,
    CompressorWithTurbine,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.domain.process.compressor.dto.model_types import CompressorModelTypes
from libecalc.domain.process.core.tabulated import ConsumerTabularEnergyFunction, VariableExpression
from libecalc.domain.process.dto.consumer_system import (
    CompressorSystemCompressor,
    CompressorSystemConsumerFunction,
    CompressorSystemOperationalSetting,
    PumpSystemConsumerFunction,
    PumpSystemOperationalSetting,
    PumpSystemPump,
)
from libecalc.domain.process.pump.pump_consumer_function import PumpConsumerFunction
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model import (
    YamlElectricityEnergyUsageModel,
    YamlEnergyUsageModelCompressor,
    YamlEnergyUsageModelCompressorSystem,
    YamlEnergyUsageModelCompressorTrainMultipleStreams,
    YamlEnergyUsageModelDirectElectricity,
    YamlEnergyUsageModelDirectFuel,
    YamlEnergyUsageModelPump,
    YamlEnergyUsageModelPumpSystem,
    YamlEnergyUsageModelTabulated,
    YamlFuelEnergyUsageModel,
)
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_direct import (
    ConsumptionRateType,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel

logger = logging.getLogger(__name__)


class InvalidConsumptionType(Exception):
    def __init__(self, actual: ConsumptionType, expected: ConsumptionType):
        self.actual = actual
        self.expected = expected
        super().__init__(f"Invalid consumption type '{actual}', expected '{expected}'")


def _handle_condition_list(conditions: list[str]):
    conditions_with_parentheses = [f"({condition})" for condition in conditions]
    return " {*} ".join(conditions_with_parentheses)


class ConditionedModel(Protocol):
    condition: YamlExpressionType
    conditions: list[YamlExpressionType] | None


def _map_condition(energy_usage_model: ConditionedModel) -> str | int | float | None:
    if energy_usage_model.condition:
        condition_value = energy_usage_model.condition
        return condition_value
    elif energy_usage_model.conditions:
        return _handle_condition_list(energy_usage_model.conditions)  # type: ignore[arg-type]
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
    energy_usage_model: YamlEnergyUsageModelCompressorSystem,
    references: ReferenceService,
    consumes: ConsumptionType,
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

    energy_usage_type_as_consumption_type = (
        ConsumptionType.ELECTRICITY if energy_usage_type == EnergyUsageType.POWER else ConsumptionType.FUEL
    )

    if consumes != energy_usage_type_as_consumption_type:
        raise InvalidConsumptionType(actual=energy_usage_type_as_consumption_type, expected=consumes)

    return CompressorSystemConsumerFunction(
        energy_usage_type=energy_usage_type,
        compressors=compressors,
        power_loss_factor=energy_usage_model.power_loss_factor,  # type: ignore[arg-type]
        condition=_map_condition(energy_usage_model),  # type: ignore[arg-type]
        total_system_rate=energy_usage_model.total_system_rate,  # type: ignore[arg-type]
        operational_settings=[
            CompressorSystemOperationalSetting(
                rates=operational_setting.rates,  # type: ignore[arg-type]
                rate_fractions=operational_setting.rate_fractions,  # type: ignore[arg-type]
                suction_pressure=operational_setting.suction_pressure,  # type: ignore[arg-type]
                suction_pressures=operational_setting.suction_pressures,  # type: ignore[arg-type]
                discharge_pressure=operational_setting.discharge_pressure,  # type: ignore[arg-type]
                discharge_pressures=operational_setting.discharge_pressures,  # type: ignore[arg-type]
                crossover=operational_setting.crossover,
            )
            for operational_setting in energy_usage_model.operational_settings
        ],
    )


def _pump_system_mapper(
    energy_usage_model: YamlEnergyUsageModelPumpSystem,
    references: ReferenceService,
    consumes: ConsumptionType,
) -> PumpSystemConsumerFunction:
    """Remove references from pump system and map yaml to DTO
    :param energy_usage_model: dict representing PumpSystem
    :return:
    """
    if consumes != ConsumptionType.ELECTRICITY:
        raise InvalidConsumptionType(actual=ConsumptionType.ELECTRICITY, expected=consumes)

    pumps = []
    for pump in energy_usage_model.pumps:
        pump_model = references.get_pump_model(pump.chart)
        pumps.append(PumpSystemPump(name=pump.name, pump_model=pump_model))

    return PumpSystemConsumerFunction(
        power_loss_factor=energy_usage_model.power_loss_factor,  # type: ignore[arg-type]
        condition=_map_condition(energy_usage_model),  # type: ignore[arg-type]
        pumps=pumps,
        fluid_density=energy_usage_model.fluid_density,  # type: ignore[arg-type]
        total_system_rate=energy_usage_model.total_system_rate,  # type: ignore[arg-type]
        operational_settings=[
            PumpSystemOperationalSetting(
                fluid_densities=operational_setting.fluid_densities,  # type: ignore[arg-type]
                rates=operational_setting.rates,  # type: ignore[arg-type]
                rate_fractions=operational_setting.rate_fractions,  # type: ignore[arg-type]
                suction_pressure=operational_setting.suction_pressure,  # type: ignore[arg-type]
                suction_pressures=operational_setting.suction_pressures,  # type: ignore[arg-type]
                discharge_pressure=operational_setting.discharge_pressure,  # type: ignore[arg-type]
                discharge_pressures=operational_setting.discharge_pressures,  # type: ignore[arg-type]
                crossover=operational_setting.crossover,
            )
            for operational_setting in energy_usage_model.operational_settings
        ],
    )


def _pump_mapper(
    energy_usage_model: YamlEnergyUsageModelPump, references: ReferenceService, consumes: ConsumptionType
) -> PumpConsumerFunction:
    energy_model = references.get_pump_model(energy_usage_model.energy_function)

    if consumes != ConsumptionType.ELECTRICITY:
        raise InvalidConsumptionType(actual=ConsumptionType.ELECTRICITY, expected=consumes)

    return PumpConsumerFunction(
        power_loss_factor=energy_usage_model.power_loss_factor,  # type: ignore[arg-type]
        condition=_map_condition(energy_usage_model),  # type: ignore[arg-type]
        rate_standard_m3_day=energy_usage_model.rate,  # type: ignore[arg-type]
        suction_pressure=energy_usage_model.suction_pressure,  # type: ignore[arg-type]
        discharge_pressure=energy_usage_model.discharge_pressure,  # type: ignore[arg-type]
        fluid_density=energy_usage_model.fluid_density,  # type: ignore[arg-type]
        model=energy_model,
    )


def _variable_speed_compressor_train_multiple_streams_and_pressures_mapper(
    energy_usage_model: YamlEnergyUsageModelCompressorTrainMultipleStreams,
    references: ReferenceService,
    consumes: ConsumptionType,
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

    energy_usage_type = _get_compressor_train_energy_usage_type(compressor_train_model)

    energy_usage_type_as_consumption_type = (
        ConsumptionType.ELECTRICITY if energy_usage_type == EnergyUsageType.POWER else ConsumptionType.FUEL
    )

    if consumes != energy_usage_type_as_consumption_type:
        raise InvalidConsumptionType(actual=energy_usage_type_as_consumption_type, expected=consumes)

    return CompressorConsumerFunction(
        energy_usage_type=energy_usage_type,
        power_loss_factor=energy_usage_model.power_loss_factor,  # type: ignore[arg-type]
        condition=_map_condition(energy_usage_model),  # type: ignore[arg-type]
        rate_standard_m3_day=rates_per_stream,
        suction_pressure=Expression.setup_from_expression(
            value=energy_usage_model.suction_pressure,
        ),
        discharge_pressure=Expression.setup_from_expression(value=energy_usage_model.discharge_pressure),
        model=compressor_train_model,
        interstage_control_pressure=interstage_control_pressure,
    )


def _compressor_mapper(
    energy_usage_model: YamlEnergyUsageModelCompressor, references: ReferenceService, consumes: ConsumptionType
) -> CompressorConsumerFunction:
    energy_model = references.get_compressor_model(energy_usage_model.energy_function)
    compressor_train_energy_usage_type = _get_compressor_train_energy_usage_type(compressor_train=energy_model)

    energy_usage_type_as_consumption_type = (
        ConsumptionType.ELECTRICITY
        if compressor_train_energy_usage_type == EnergyUsageType.POWER
        else ConsumptionType.FUEL
    )

    if consumes != energy_usage_type_as_consumption_type:
        raise InvalidConsumptionType(actual=energy_usage_type_as_consumption_type, expected=consumes)

    return CompressorConsumerFunction(
        energy_usage_type=compressor_train_energy_usage_type,
        power_loss_factor=energy_usage_model.power_loss_factor,  # type: ignore[arg-type]
        condition=_map_condition(energy_usage_model),  # type: ignore[arg-type]
        rate_standard_m3_day=energy_usage_model.rate,  # type: ignore[arg-type]
        suction_pressure=energy_usage_model.suction_pressure,  # type: ignore[arg-type]
        discharge_pressure=energy_usage_model.discharge_pressure,  # type: ignore[arg-type]
        model=energy_model,
    )


ConsumerFunctionUnion = (
    CompressorConsumerFunction | CompressorSystemConsumerFunction | PumpSystemConsumerFunction | PumpConsumerFunction
)

_dto_map: dict[Any, Callable[[Any, ReferenceService, ConsumptionType], ConsumerFunctionUnion]] = {
    EcalcYamlKeywords.energy_usage_model_type_pump_system: _pump_system_mapper,
    EcalcYamlKeywords.energy_usage_model_type_compressor_system: _compressor_system_mapper,
    EcalcYamlKeywords.energy_usage_model_type_pump: _pump_mapper,
    EcalcYamlKeywords.energy_usage_model_type_compressor: _compressor_mapper,
    EcalcYamlKeywords.energy_usage_model_type_variable_speed_compressor_train_multiple_streams_and_pressures: _variable_speed_compressor_train_multiple_streams_and_pressures_mapper,
}


class InvalidEnergyUsageModelException(Exception): ...


class InvalidConsumptionTypeException(InvalidEnergyUsageModelException):
    def __init__(
        self,
        actual: ConsumptionType,
        expected: ConsumptionType,
        period: Period,
        model: YamlFuelEnergyUsageModel | YamlElectricityEnergyUsageModel,
    ):
        self.actual = actual
        self.expected = expected
        self.period = period
        self.model = model
        super().__init__(
            f"Invalid consumption type '{actual}', expected '{expected}' for energy usage model with start '{str(period.start)}' and type '{model.type}'"
        )


core_map: dict[ConsumerType, Callable[[ConsumerFunctionUnion], ConsumerFunction]] = {
    ConsumerType.PUMP_SYSTEM: create_pump_system,  # type: ignore[dict-item]
    ConsumerType.COMPRESSOR_SYSTEM: create_compressor_system,  # type: ignore[dict-item]
    ConsumerType.COMPRESSOR: create_compressor_consumer_function,  # type: ignore[dict-item]
    ConsumerType.PUMP: create_pump_consumer_function,  # type: ignore[dict-item]
}


def _invalid_energy_usage_type(energy_usage_model: Any) -> ConsumerFunction:
    try:
        msg = f"Unsupported consumer function type: {energy_usage_model.typ}."
        logger.error(msg)
        raise TypeError(msg)
    except AttributeError as e:
        msg = "Unsupported consumer function type."
        logger.exception(msg)
        raise TypeError(msg) from e


class ConsumerFunctionMapper:
    def __init__(self, references: ReferenceService, target_period: Period):
        self.__references = references
        self._target_period = target_period

    def _map_direct(
        self, model: YamlEnergyUsageModelDirectFuel | YamlEnergyUsageModelDirectElectricity, consumes: ConsumptionType
    ) -> DirectExpressionConsumerFunction:
        condition = convert_expression(_map_condition(model))
        consumption_rate_type = RateType((model.consumption_rate_type or ConsumptionRateType.STREAM_DAY).value)
        power_loss_factor = convert_expression(model.power_loss_factor)
        if isinstance(model, YamlEnergyUsageModelDirectFuel):
            if consumes != ConsumptionType.FUEL:
                raise InvalidConsumptionType(actual=ConsumptionType.FUEL, expected=consumes)
            return DirectExpressionConsumerFunction(
                energy_usage_type=EnergyUsageType.FUEL,
                fuel_rate=convert_expression(model.fuel_rate),  # type: ignore[arg-type]
                condition=condition,  # type: ignore[arg-type]
                power_loss_factor=power_loss_factor,  # type: ignore[arg-type]
                consumption_rate_type=consumption_rate_type,
            )
        else:
            assert isinstance(model, YamlEnergyUsageModelDirectElectricity)

            if consumes != ConsumptionType.ELECTRICITY:
                raise InvalidConsumptionType(actual=ConsumptionType.ELECTRICITY, expected=consumes)

            return DirectExpressionConsumerFunction(
                energy_usage_type=EnergyUsageType.POWER,
                load=convert_expression(model.load),  # type: ignore[arg-type]
                condition=condition,  # type: ignore[arg-type]
                power_loss_factor=power_loss_factor,  # type: ignore[arg-type]
                consumption_rate_type=consumption_rate_type,
            )

    def _map_tabular(
        self, model: YamlEnergyUsageModelTabulated, consumes: ConsumptionType
    ) -> TabulatedConsumerFunction:
        energy_model = self.__references.get_tabulated_model(model.energy_function)
        energy_usage_type = energy_model.get_energy_usage_type()
        energy_usage_type_as_consumption_type = (
            ConsumptionType.ELECTRICITY if energy_usage_type == EnergyUsageType.POWER else ConsumptionType.FUEL
        )

        if consumes != energy_usage_type_as_consumption_type:
            raise InvalidConsumptionType(actual=energy_usage_type_as_consumption_type, expected=consumes)

        condition = convert_expression(_map_condition(model))
        power_loss_factor = convert_expression(model.power_loss_factor)

        tabulated_energy_function = ConsumerTabularEnergyFunction(
            energy_model=energy_model,
        )

        return TabulatedConsumerFunction(
            tabulated_energy_function=tabulated_energy_function,
            variables_expressions=[
                VariableExpression(
                    name=variable.name,
                    expression=convert_expression(variable.expression),  # type: ignore[arg-type]
                )
                for variable in model.variables
            ],
            condition_expression=condition,  # type: ignore[arg-type]
            power_loss_factor_expression=power_loss_factor,  # type: ignore[arg-type]
        )

    def from_yaml_to_dto(
        self,
        data: (YamlTemporalModel[YamlFuelEnergyUsageModel] | YamlTemporalModel[YamlElectricityEnergyUsageModel]),
        consumes: ConsumptionType,
    ) -> TemporalModel[ConsumerFunction]:
        time_adjusted_model = define_time_model_for_period(data, target_period=self._target_period)

        temporal_dict: dict[Period, ConsumerFunction] = {}
        for period, model in time_adjusted_model.items():
            try:
                if isinstance(model, YamlEnergyUsageModelDirectElectricity | YamlEnergyUsageModelDirectFuel):
                    mapped_model = self._map_direct(model=model, consumes=consumes)
                elif isinstance(model, YamlEnergyUsageModelCompressor):
                    mapped_model = core_map[ConsumerType.COMPRESSOR](
                        _dto_map[model.type](model, self.__references, consumes)
                    )
                elif isinstance(model, YamlEnergyUsageModelPump):
                    mapped_model = core_map[ConsumerType.PUMP](_dto_map[model.type](model, self.__references, consumes))
                elif isinstance(model, YamlEnergyUsageModelCompressorSystem):
                    mapped_model = core_map[ConsumerType.COMPRESSOR_SYSTEM](
                        _dto_map[model.type](model, self.__references, consumes)
                    )
                elif isinstance(model, YamlEnergyUsageModelPumpSystem):
                    mapped_model = core_map[ConsumerType.PUMP_SYSTEM](
                        _dto_map[model.type](model, self.__references, consumes)
                    )
                elif isinstance(model, YamlEnergyUsageModelTabulated):
                    mapped_model = self._map_tabular(model=model, consumes=consumes)
                elif isinstance(model, YamlEnergyUsageModelCompressorTrainMultipleStreams):
                    mapped_model = core_map[ConsumerType.COMPRESSOR](
                        _dto_map[model.type](model, self.__references, consumes)
                    )
                else:
                    assert_never(model)
                temporal_dict[period] = mapped_model
            except InvalidConsumptionType as e:
                raise InvalidConsumptionTypeException(
                    actual=e.actual,
                    expected=e.expected,
                    period=period,
                    model=model,
                ) from e
        return TemporalModel(temporal_dict)
