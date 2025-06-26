import logging
from typing import Protocol, assert_never

from libecalc.common.chart_type import ChartType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.common.utils.rates import RateType
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import ConsumerFunction
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.compressor_consumer_function import (
    CompressorConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.direct_expression_consumer_function import (
    DirectExpressionConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.pump_consumer_function import (
    PumpConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.consumer_function import (
    CompressorSystemConsumerFunction,
    PumpSystemConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    CompressorSystemOperationalSettingExpressions,
    ConsumerSystemOperationalSettingExpressions,
    PumpSystemOperationalSettingExpressions,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.types import ConsumerSystemComponent
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated import (
    TabularConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated.common import VariableExpression
from libecalc.domain.process.compressor.core import create_compressor_model
from libecalc.domain.process.compressor.dto import (
    CompressorTrainSimplifiedWithKnownStages,
    CompressorTrainSimplifiedWithUnknownStages,
    CompressorWithTurbine,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.domain.process.compressor.dto.model_types import CompressorModelTypes
from libecalc.domain.process.pump.factory import create_pump_model
from libecalc.dto.utils.validators import convert_expression, convert_expressions
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
        message = f"Invalid consumption type: expected a model that consumes {expected.value.lower()}, got {actual.value.lower()}."
        super().__init__(message)


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


def check_for_generic_from_input_compressor_chart_in_simplified_train_compressor_system(
    compressor_train: CompressorModelTypes,
    name: str,
):
    if isinstance(compressor_train, CompressorTrainSimplifiedWithKnownStages):
        for i, stage in enumerate(compressor_train.stages):
            if stage.compressor_chart.typ == ChartType.GENERIC_FROM_INPUT:
                logger.warning(
                    f"Stage number {i + 1} in {name} uses GENERIC_FROM_INPUT. "
                    f"Beware that when splitting rates on several compressor trains in a compressor system, "
                    f"the rate input used to generate a specific compressor chart will also change. Consider"
                    f" to define a design point yourself instead of letting an algorithm find one based on"
                    f" changing rates!"
                )
    elif isinstance(compressor_train, CompressorTrainSimplifiedWithUnknownStages):
        if compressor_train.stage.compressor_chart.typ == ChartType.GENERIC_FROM_INPUT:
            logger.warning(
                f"Compressor chart in {name} uses GENERIC_FROM_INPUT. "
                f"Beware that when splitting rates on several compressor trains in a compressor system, "
                f"the rate input used to generate a specific compressor chart will also change. Consider"
                f" to define a design point yourself instead of letting an algorithm find one based on"
                f" changing rates!"
            )


class InvalidEnergyUsageModelException(Exception):
    def __init__(self, period: Period, model: YamlFuelEnergyUsageModel | YamlElectricityEnergyUsageModel, message: str):
        self.period = period
        self.model = model
        self.message = message
        super().__init__(f"Invalid energy usage model '{model.type}' with start '{period}'. \n Message: {message}")


def map_rate_fractions(
    rate_fractions: list[Expression],
    system_rate: Expression,
) -> list[Expression]:
    # Multiply rate_fractions with total system rate to get rates
    return [
        Expression.multiply(
            system_rate,
            rate_fraction,
        )
        for rate_fraction in rate_fractions
    ]


class ConsumerFunctionMapper:
    def __init__(
        self,
        references: ReferenceService,
        target_period: Period,
    ):
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

    def _map_tabular(self, model: YamlEnergyUsageModelTabulated, consumes: ConsumptionType) -> TabularConsumerFunction:
        energy_model = self.__references.get_tabulated_model(model.energy_function)
        energy_usage_type = energy_model.get_energy_usage_type()
        energy_usage_type_as_consumption_type = (
            ConsumptionType.ELECTRICITY if energy_usage_type == EnergyUsageType.POWER else ConsumptionType.FUEL
        )

        if consumes != energy_usage_type_as_consumption_type:
            raise InvalidConsumptionType(actual=energy_usage_type_as_consumption_type, expected=consumes)

        condition = convert_expression(_map_condition(model))
        power_loss_factor = convert_expression(model.power_loss_factor)

        return TabularConsumerFunction(
            headers=energy_model.headers,
            data=energy_model.data,
            energy_usage_adjustment_constant=energy_model.energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=energy_model.energy_usage_adjustment_factor,
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

    def _map_pump(self, model: YamlEnergyUsageModelPump, consumes: ConsumptionType) -> PumpConsumerFunction:
        energy_model = self.__references.get_pump_model(model.energy_function)

        if consumes != ConsumptionType.ELECTRICITY:
            raise InvalidConsumptionType(actual=ConsumptionType.ELECTRICITY, expected=consumes)

        power_loss_factor = convert_expression(model.power_loss_factor)
        condition = convert_expression(_map_condition(model))
        rate_standard_m3_day = convert_expression(model.rate)
        suction_pressure = convert_expression(model.suction_pressure)
        discharge_pressure = convert_expression(model.discharge_pressure)
        fluid_density = convert_expression(model.fluid_density)
        pump_model = create_pump_model(pump_model_dto=energy_model)
        return PumpConsumerFunction(
            condition_expression=condition,  # type: ignore[arg-type]
            power_loss_factor_expression=power_loss_factor,  # type: ignore[arg-type]
            pump_function=pump_model,
            rate_expression=rate_standard_m3_day,  # type: ignore[arg-type]
            suction_pressure_expression=suction_pressure,  # type: ignore[arg-type]
            discharge_pressure_expression=discharge_pressure,  # type: ignore[arg-type]
            fluid_density_expression=fluid_density,  # type: ignore[arg-type]
        )

    def _map_multiple_streams_compressor(
        self, model: YamlEnergyUsageModelCompressorTrainMultipleStreams, consumes: ConsumptionType
    ):
        compressor_train_model = self.__references.get_compressor_model(model.compressor_train_model)
        rates_per_stream = [
            Expression.setup_from_expression(value=rate_expression) for rate_expression in model.rate_per_stream
        ]
        interstage_control_pressure_config = model.interstage_control_pressure
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
                f" {model.compressor_train_model}"
                f" requires {EcalcYamlKeywords.models_type_compressor_train_interstage_control_pressure} to be defined"
            )
        elif not require_interstage_pressure_variable_expression and interstage_control_pressure_config is not None:
            raise ValueError(
                f"Energy model"
                f" {model.compressor_train_model}"
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

        power_loss_factor = convert_expression(model.power_loss_factor)
        condition = convert_expression(_map_condition(model))
        suction_pressure = convert_expression(model.suction_pressure)
        discharge_pressure = convert_expression(model.discharge_pressure)
        interstage_control_pressure = convert_expression(interstage_control_pressure)
        compressor_model = create_compressor_model(compressor_model_dto=compressor_train_model)
        return CompressorConsumerFunction(
            condition_expression=condition,  # type: ignore[arg-type]
            power_loss_factor_expression=power_loss_factor,  # type: ignore[arg-type]
            compressor_function=compressor_model,
            rate_expression=rates_per_stream,
            suction_pressure_expression=suction_pressure,  # type: ignore[arg-type]
            discharge_pressure_expression=discharge_pressure,  # type: ignore[arg-type]
            intermediate_pressure_expression=interstage_control_pressure,
        )

    def _map_compressor(
        self, model: YamlEnergyUsageModelCompressor, consumes: ConsumptionType
    ) -> CompressorConsumerFunction:
        energy_model = self.__references.get_compressor_model(model.energy_function)
        compressor_train_energy_usage_type = _get_compressor_train_energy_usage_type(compressor_train=energy_model)

        energy_usage_type_as_consumption_type = (
            ConsumptionType.ELECTRICITY
            if compressor_train_energy_usage_type == EnergyUsageType.POWER
            else ConsumptionType.FUEL
        )

        if consumes != energy_usage_type_as_consumption_type:
            raise InvalidConsumptionType(actual=energy_usage_type_as_consumption_type, expected=consumes)

        power_loss_factor = convert_expression(model.power_loss_factor)
        condition = convert_expression(_map_condition(model))
        rate_standard_m3_day = convert_expression(model.rate)
        suction_pressure = convert_expression(model.suction_pressure)
        discharge_pressure = convert_expression(model.discharge_pressure)
        compressor_model = create_compressor_model(compressor_model_dto=energy_model)
        return CompressorConsumerFunction(
            condition_expression=condition,  # type: ignore[arg-type]
            power_loss_factor_expression=power_loss_factor,  # type: ignore[arg-type]
            compressor_function=compressor_model,
            rate_expression=rate_standard_m3_day,  # type: ignore[arg-type]
            suction_pressure_expression=suction_pressure,  # type: ignore[arg-type]
            discharge_pressure_expression=discharge_pressure,  # type: ignore[arg-type]
            intermediate_pressure_expression=None,
        )

    def _map_compressor_system(
        self, model: YamlEnergyUsageModelCompressorSystem, consumes: ConsumptionType
    ) -> CompressorSystemConsumerFunction:
        compressors = []
        compressor_power_usage_type = set()
        for compressor in model.compressors:
            compressor_train = self.__references.get_compressor_model(compressor.compressor_model)

            check_for_generic_from_input_compressor_chart_in_simplified_train_compressor_system(
                compressor_train, name=compressor.name
            )

            compressors.append(
                ConsumerSystemComponent(
                    name=compressor.name,
                    facility_model=create_compressor_model(compressor_train),
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

        operational_settings: list[ConsumerSystemOperationalSettingExpressions] = []
        for operational_setting in model.operational_settings:
            if operational_setting.rate_fractions is not None:
                rate_fractions = convert_expressions(operational_setting.rate_fractions)  # type: ignore[arg-type]
                total_system_rate = convert_expression(model.total_system_rate)
                assert total_system_rate is not None
                rates = map_rate_fractions(rate_fractions, total_system_rate)  # type: ignore[arg-type]
            else:
                rates = convert_expressions(operational_setting.rates)  # type: ignore[arg-type]

            number_of_compressors = len(compressors)

            if operational_setting.suction_pressure is not None:
                suction_pressures = [convert_expression(operational_setting.suction_pressure)] * number_of_compressors
            else:
                assert operational_setting.suction_pressures is not None
                suction_pressures = convert_expressions(operational_setting.suction_pressures)

            if operational_setting.discharge_pressure is not None:
                discharge_pressures = [
                    convert_expression(operational_setting.discharge_pressure)
                ] * number_of_compressors
            else:
                assert operational_setting.discharge_pressures is not None
                discharge_pressures = convert_expressions(operational_setting.discharge_pressures)

            core_setting = CompressorSystemOperationalSettingExpressions(
                rates=rates,
                discharge_pressures=discharge_pressures,  # type: ignore[arg-type]
                suction_pressures=suction_pressures,  # type: ignore[arg-type]
                cross_overs=operational_setting.crossover,
            )
            operational_settings.append(core_setting)

        power_loss_factor = convert_expression(model.power_loss_factor)
        condition = convert_expression(_map_condition(model))
        return CompressorSystemConsumerFunction(
            consumer_components=compressors,
            operational_settings_expressions=operational_settings,
            power_loss_factor_expression=power_loss_factor,  # type: ignore[arg-type]
            condition_expression=condition,  # type: ignore[arg-type]
        )

    def _map_pump_system(
        self, model: YamlEnergyUsageModelPumpSystem, consumes: ConsumptionType
    ) -> PumpSystemConsumerFunction:
        if consumes != ConsumptionType.ELECTRICITY:
            raise InvalidConsumptionType(actual=ConsumptionType.ELECTRICITY, expected=consumes)

        pumps = []
        for pump in model.pumps:
            pump_model = self.__references.get_pump_model(pump.chart)
            pumps.append(ConsumerSystemComponent(name=pump.name, facility_model=create_pump_model(pump_model)))

        operational_settings: list[ConsumerSystemOperationalSettingExpressions] = []
        for operational_setting in model.operational_settings:
            if operational_setting.rate_fractions is not None:
                rate_fractions = convert_expressions(operational_setting.rate_fractions)  # type: ignore[arg-type]
                total_system_rate = convert_expression(model.total_system_rate)
                assert total_system_rate is not None
                rates = map_rate_fractions(rate_fractions, total_system_rate)  # type: ignore[arg-type]
            else:
                rates = convert_expressions(operational_setting.rates)  # type: ignore[arg-type]

            number_of_pumps = len(pumps)

            if operational_setting.suction_pressure is not None:
                suction_pressures = [convert_expression(operational_setting.suction_pressure)] * number_of_pumps
            else:
                assert operational_setting.suction_pressures is not None
                suction_pressures = convert_expressions(operational_setting.suction_pressures)

            if operational_setting.discharge_pressure is not None:
                discharge_pressures = [convert_expression(operational_setting.discharge_pressure)] * number_of_pumps
            else:
                assert operational_setting.discharge_pressures is not None
                discharge_pressures = convert_expressions(operational_setting.discharge_pressures)

            if operational_setting.fluid_densities:
                fluid_densities = convert_expressions(operational_setting.fluid_densities)  # type: ignore[arg-type]
            else:
                assert model.fluid_density is not None
                fluid_densities = [convert_expression(model.fluid_density)] * number_of_pumps

            operational_settings.append(
                PumpSystemOperationalSettingExpressions(
                    rates=rates,
                    suction_pressures=suction_pressures,  # type: ignore[arg-type]
                    discharge_pressures=discharge_pressures,  # type: ignore[arg-type]
                    cross_overs=operational_setting.crossover,
                    fluid_densities=fluid_densities,  # type: ignore[arg-type]
                )
            )

        power_loss_factor = convert_expression(model.power_loss_factor)
        condition = convert_expression(_map_condition(model))
        return PumpSystemConsumerFunction(
            power_loss_factor_expression=power_loss_factor,  # type: ignore[arg-type]
            condition_expression=condition,  # type: ignore[arg-type]
            consumer_components=pumps,
            operational_settings_expressions=operational_settings,
        )

    def from_yaml_to_dto(
        self,
        data: YamlTemporalModel[YamlFuelEnergyUsageModel] | YamlTemporalModel[YamlElectricityEnergyUsageModel],
        consumes: ConsumptionType,
    ) -> TemporalModel[ConsumerFunction]:
        time_adjusted_model = define_time_model_for_period(data, target_period=self._target_period)

        temporal_dict: dict[Period, ConsumerFunction] = {}
        for period, model in time_adjusted_model.items():
            try:
                if isinstance(model, YamlEnergyUsageModelDirectElectricity | YamlEnergyUsageModelDirectFuel):
                    mapped_model = self._map_direct(model=model, consumes=consumes)
                elif isinstance(model, YamlEnergyUsageModelCompressor):
                    mapped_model = self._map_compressor(model, consumes=consumes)
                elif isinstance(model, YamlEnergyUsageModelPump):
                    mapped_model = self._map_pump(model, consumes=consumes)
                elif isinstance(model, YamlEnergyUsageModelCompressorSystem):
                    mapped_model = self._map_compressor_system(model, consumes=consumes)
                elif isinstance(model, YamlEnergyUsageModelPumpSystem):
                    mapped_model = self._map_pump_system(model, consumes=consumes)
                elif isinstance(model, YamlEnergyUsageModelTabulated):
                    mapped_model = self._map_tabular(model=model, consumes=consumes)
                elif isinstance(model, YamlEnergyUsageModelCompressorTrainMultipleStreams):
                    mapped_model = self._map_multiple_streams_compressor(model, consumes=consumes)
                else:
                    assert_never(model)
                temporal_dict[period] = mapped_model
            except InvalidConsumptionType as e:
                raise InvalidEnergyUsageModelException(
                    message=str(e),
                    period=period,
                    model=model,
                ) from e
            except ValueError as e:
                raise InvalidEnergyUsageModelException(
                    message=str(e),
                    period=period,
                    model=model,
                ) from e
        return TemporalModel(temporal_dict)
