import logging
from typing import Protocol, assert_never

from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.component_validation_error import (
    DomainValidationException,
    ProcessPressureRatioValidationException,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import ConsumerFunction
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.compressor_consumer_function import (
    CompressorConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.direct_consumer_function import (
    DirectConsumerFunction,
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
from libecalc.domain.regularity import Regularity
from libecalc.domain.time_series_flow_rate import TimeSeriesFlowRate
from libecalc.domain.time_series_variable import TimeSeriesVariable
from libecalc.expression import Expression
from libecalc.expression.expression import InvalidExpressionError
from libecalc.presentation.yaml.domain.expression_time_series_flow_rate import ExpressionTimeSeriesFlowRate
from libecalc.presentation.yaml.domain.expression_time_series_fluid_density import ExpressionTimeSeriesFluidDensity
from libecalc.presentation.yaml.domain.expression_time_series_power import ExpressionTimeSeriesPower
from libecalc.presentation.yaml.domain.expression_time_series_power_loss_factor import (
    ExpressionTimeSeriesPowerLossFactor,
)
from libecalc.presentation.yaml.domain.expression_time_series_pressure import ExpressionTimeSeriesPressure
from libecalc.presentation.yaml.domain.expression_time_series_variable import ExpressionTimeSeriesVariable
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
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


def validate_increasing_pressure(
    suction_pressure: ExpressionTimeSeriesPressure,
    discharge_pressure: ExpressionTimeSeriesPressure,
    intermediate_pressure: ExpressionTimeSeriesPressure | None = None,
):
    validation_mask = suction_pressure.get_validation_mask()
    assert validation_mask == discharge_pressure.get_validation_mask()
    suction_pressure_values = suction_pressure.get_values()
    discharge_pressure_values = discharge_pressure.get_values()

    if intermediate_pressure is not None:
        assert validation_mask == intermediate_pressure.get_validation_mask()
        intermediate_pressure_values = intermediate_pressure.get_values()
    else:
        intermediate_pressure_values = None

    for i in range(len(suction_pressure_values)):
        if validation_mask[i]:
            sp = suction_pressure_values[i]
            dp = discharge_pressure_values[i]
            if intermediate_pressure_values is not None:
                ip = intermediate_pressure_values[i]
                if not (sp <= ip <= dp):
                    raise ProcessPressureRatioValidationException(
                        message=f"Invalid pressures at index {i+1}: suction pressure ({sp}) must be less than intermediate pressure ({ip}), which must be less than discharge pressure ({dp})."
                    )
            else:
                if not (sp <= dp):
                    raise ProcessPressureRatioValidationException(
                        message=f"Invalid pressures at index {i+1}: suction pressure ({sp}) must be less than discharge pressure ({dp})."
                    )


class ConsumerFunctionMapper:
    def __init__(
        self,
        references: ReferenceService,
        target_period: Period,
        expression_evaluator: ExpressionEvaluator,
        regularity: Regularity,
        energy_usage_model: YamlTemporalModel[YamlFuelEnergyUsageModel]
        | YamlTemporalModel[YamlElectricityEnergyUsageModel],
    ):
        self.__references = references
        self._target_period = target_period
        self._expression_evaluator = expression_evaluator
        self._regularity = regularity
        self._period_subsets = {}
        self._time_adjusted_model = define_time_model_for_period(energy_usage_model, target_period=target_period)
        for period in self._time_adjusted_model:
            start_index, end_index = period.get_period_indices(expression_evaluator.get_periods())
            period_regularity = regularity.get_subset(start_index, end_index)
            period_evaluator = expression_evaluator.get_subset(start_index, end_index)
            self._period_subsets[period] = (period_regularity, period_evaluator)

    def _map_direct(
        self,
        model: YamlEnergyUsageModelDirectFuel | YamlEnergyUsageModelDirectElectricity,
        consumes: ConsumptionType,
        period: Period,
    ) -> DirectConsumerFunction:
        period_regularity, period_evaluator = self._period_subsets[period]

        power_loss_factor_expression = TimeSeriesExpression(
            expression=model.power_loss_factor, expression_evaluator=period_evaluator
        )
        power_loss_factor = ExpressionTimeSeriesPowerLossFactor(time_series_expression=power_loss_factor_expression)

        consumption_rate_type = RateType((model.consumption_rate_type or ConsumptionRateType.STREAM_DAY).value)

        if isinstance(model, YamlEnergyUsageModelDirectFuel):
            if consumes != ConsumptionType.FUEL:
                raise InvalidConsumptionType(actual=ConsumptionType.FUEL, expected=consumes)
            fuel_rate_expression = TimeSeriesExpression(
                expression=model.fuel_rate, expression_evaluator=period_evaluator, condition=_map_condition(model)
            )
            fuel_rate = ExpressionTimeSeriesFlowRate(
                time_series_expression=fuel_rate_expression,
                regularity=period_regularity,
                consumption_rate_type=consumption_rate_type,
            )
            return DirectConsumerFunction(
                energy_usage_type=EnergyUsageType.FUEL,
                fuel_rate=fuel_rate,
                power_loss_factor=power_loss_factor,
            )
        else:
            assert isinstance(model, YamlEnergyUsageModelDirectElectricity)

            if consumes != ConsumptionType.ELECTRICITY:
                raise InvalidConsumptionType(actual=ConsumptionType.ELECTRICITY, expected=consumes)

            load_expression = TimeSeriesExpression(
                expression=model.load, expression_evaluator=period_evaluator, condition=_map_condition(model)
            )
            load = ExpressionTimeSeriesPower(
                time_series_expression=load_expression,
                regularity=period_regularity,
                consumption_rate_type=consumption_rate_type,
            )
            return DirectConsumerFunction(
                energy_usage_type=EnergyUsageType.POWER,
                load=load,
                power_loss_factor=power_loss_factor,
            )

    def _map_tabular(
        self, model: YamlEnergyUsageModelTabulated, consumes: ConsumptionType, period: Period
    ) -> TabularConsumerFunction:
        period_regularity, period_evaluator = self._period_subsets[period]
        energy_model = self.__references.get_tabulated_model(model.energy_function)
        energy_usage_type = energy_model.get_energy_usage_type()
        energy_usage_type_as_consumption_type = (
            ConsumptionType.ELECTRICITY if energy_usage_type == EnergyUsageType.POWER else ConsumptionType.FUEL
        )

        if consumes != energy_usage_type_as_consumption_type:
            raise InvalidConsumptionType(actual=energy_usage_type_as_consumption_type, expected=consumes)

        power_loss_factor_expression = TimeSeriesExpression(
            expression=model.power_loss_factor, expression_evaluator=period_evaluator
        )
        power_loss_factor = ExpressionTimeSeriesPowerLossFactor(time_series_expression=power_loss_factor_expression)

        variables: list[TimeSeriesVariable] = [
            ExpressionTimeSeriesVariable(
                name=variable.name,
                time_series_expression=TimeSeriesExpression(
                    expression=variable.expression,
                    expression_evaluator=period_evaluator,
                    condition=_map_condition(model),
                ),
                regularity=period_regularity,
                is_rate=(variable.name.lower() == "rate"),
            )
            for variable in model.variables
        ]

        return TabularConsumerFunction(
            headers=energy_model.headers,
            data=energy_model.data,
            energy_usage_adjustment_constant=energy_model.energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=energy_model.energy_usage_adjustment_factor,
            variables=variables,
            power_loss_factor=power_loss_factor,
        )

    def _map_pump(
        self, model: YamlEnergyUsageModelPump, consumes: ConsumptionType, period: Period
    ) -> PumpConsumerFunction:
        pump_model = self.__references.get_pump_model(model.energy_function)
        period_regularity, period_evaluator = self._period_subsets[period]
        if consumes != ConsumptionType.ELECTRICITY:
            raise InvalidConsumptionType(actual=ConsumptionType.ELECTRICITY, expected=consumes)

        power_loss_factor_expression = TimeSeriesExpression(
            expression=model.power_loss_factor, expression_evaluator=period_evaluator
        )
        power_loss_factor = ExpressionTimeSeriesPowerLossFactor(time_series_expression=power_loss_factor_expression)

        rate_expression = TimeSeriesExpression(
            expression=model.rate, expression_evaluator=period_evaluator, condition=_map_condition(model)
        )
        rate_standard_m3_day = ExpressionTimeSeriesFlowRate(
            time_series_expression=rate_expression,
            regularity=period_regularity,
        )

        fluid_density_expression = TimeSeriesExpression(
            expression=model.fluid_density, expression_evaluator=period_evaluator
        )
        fluid_density = ExpressionTimeSeriesFluidDensity(time_series_expression=fluid_density_expression)

        pressure_validation_mask = [
            bool(_rate * _regularity > 0)
            for _rate, _regularity in zip(rate_standard_m3_day.get_stream_day_values(), period_regularity.values)
            if _rate is not None
        ]

        suction_pressure_expression = TimeSeriesExpression(
            expression=model.suction_pressure, expression_evaluator=period_evaluator
        )
        suction_pressure = ExpressionTimeSeriesPressure(
            time_series_expression=suction_pressure_expression,
            validation_mask=pressure_validation_mask,
        )

        discharge_pressure_expression = TimeSeriesExpression(
            expression=model.discharge_pressure, expression_evaluator=period_evaluator
        )
        discharge_pressure = ExpressionTimeSeriesPressure(
            time_series_expression=discharge_pressure_expression,
            validation_mask=pressure_validation_mask,
        )

        validate_increasing_pressure(
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
        )

        return PumpConsumerFunction(
            power_loss_factor=power_loss_factor,
            pump_function=pump_model,
            rate=rate_standard_m3_day,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
            fluid_density=fluid_density,
        )

    def _map_multiple_streams_compressor(
        self, model: YamlEnergyUsageModelCompressorTrainMultipleStreams, consumes: ConsumptionType, period: Period
    ):
        compressor_train_model = self.__references.get_compressor_model(model.compressor_train_model)
        consumption_type = compressor_train_model.get_consumption_type()

        if consumes != consumption_type:
            raise InvalidConsumptionType(actual=consumption_type, expected=consumes)

        regularity, expression_evaluator = self._period_subsets[period]

        power_loss_factor = (
            ExpressionTimeSeriesPowerLossFactor(
                time_series_expression=TimeSeriesExpression(
                    model.power_loss_factor, expression_evaluator=expression_evaluator
                )
            )
            if model.power_loss_factor is not None
            else None
        )

        rates_per_stream: list[TimeSeriesFlowRate] = [
            ExpressionTimeSeriesFlowRate(
                time_series_expression=TimeSeriesExpression(
                    rate_expression, expression_evaluator=expression_evaluator, condition=_map_condition(model)
                ),
                regularity=regularity,
                consumption_rate_type=RateType.CALENDAR_DAY,
            )
            for rate_expression in model.rate_per_stream
        ]

        rates_per_stream_values = [rates.get_stream_day_values() for rates in rates_per_stream]
        sum_of_rates = [sum(values) for values in zip(*rates_per_stream_values)]

        validation_mask = [bool(_rate * _regularity > 0) for _rate, _regularity in zip(sum_of_rates, regularity.values)]

        suction_pressure = ExpressionTimeSeriesPressure(
            time_series_expression=TimeSeriesExpression(
                model.suction_pressure, expression_evaluator=expression_evaluator
            ),
            validation_mask=validation_mask,
        )
        discharge_pressure = ExpressionTimeSeriesPressure(
            time_series_expression=TimeSeriesExpression(
                model.discharge_pressure, expression_evaluator=expression_evaluator
            ),
            validation_mask=validation_mask,
        )
        interstage_control_pressure = (
            ExpressionTimeSeriesPressure(
                time_series_expression=TimeSeriesExpression(
                    model.interstage_control_pressure, expression_evaluator=expression_evaluator
                ),
                validation_mask=validation_mask,
            )
            if model.interstage_control_pressure is not None
            else None
        )

        validate_increasing_pressure(
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
            intermediate_pressure=interstage_control_pressure,
        )

        return CompressorConsumerFunction(
            power_loss_factor_expression=power_loss_factor,
            compressor_function=compressor_train_model,
            rate_expression=rates_per_stream,
            suction_pressure_expression=suction_pressure,
            discharge_pressure_expression=discharge_pressure,
            intermediate_pressure_expression=interstage_control_pressure,
        )

    def _map_compressor(
        self,
        model: YamlEnergyUsageModelCompressor,
        consumes: ConsumptionType,
        period: Period,
    ) -> CompressorConsumerFunction:
        compressor_model = self.__references.get_compressor_model(model.energy_function)
        consumption_type = compressor_model.get_consumption_type()

        if consumes != consumption_type:
            raise InvalidConsumptionType(actual=consumption_type, expected=consumes)

        regularity, expression_evaluator = self._period_subsets[period]

        power_loss_factor = (
            ExpressionTimeSeriesPowerLossFactor(
                time_series_expression=TimeSeriesExpression(
                    model.power_loss_factor, expression_evaluator=expression_evaluator
                )
            )
            if model.power_loss_factor is not None
            else None
        )

        stream_day_rate = ExpressionTimeSeriesFlowRate(
            time_series_expression=TimeSeriesExpression(
                model.rate, expression_evaluator=expression_evaluator, condition=_map_condition(model)
            ),
            consumption_rate_type=RateType.CALENDAR_DAY,
            regularity=regularity,
        )

        validation_mask = [
            bool(_rate * _regularity > 0)
            for _rate, _regularity in zip(stream_day_rate.get_stream_day_values(), regularity.values)
            if _rate is not None
        ]
        suction_pressure = (
            ExpressionTimeSeriesPressure(
                time_series_expression=TimeSeriesExpression(
                    model.suction_pressure, expression_evaluator=expression_evaluator
                ),
                validation_mask=validation_mask,
            )
            if model.suction_pressure
            else None
        )

        discharge_pressure = (
            ExpressionTimeSeriesPressure(
                time_series_expression=TimeSeriesExpression(
                    model.discharge_pressure, expression_evaluator=expression_evaluator
                ),
                validation_mask=validation_mask,
            )
            if model.discharge_pressure
            else None
        )

        if (
            suction_pressure is not None and discharge_pressure is not None
        ):  # to handle compressor sampled which may not have pressures
            validate_increasing_pressure(
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )

        return CompressorConsumerFunction(
            power_loss_factor_expression=power_loss_factor,
            compressor_function=compressor_model,
            rate_expression=stream_day_rate,
            suction_pressure_expression=suction_pressure,
            discharge_pressure_expression=discharge_pressure,
            intermediate_pressure_expression=None,
        )

    def _map_compressor_system(
        self, model: YamlEnergyUsageModelCompressorSystem, consumes: ConsumptionType, period: Period
    ) -> CompressorSystemConsumerFunction:
        regularity, expression_evaluator = self._period_subsets[period]
        compressors = []
        compressor_consumption_types: set[ConsumptionType] = set()
        for compressor in model.compressors:
            compressor_train = self.__references.get_compressor_model(compressor.compressor_model)

            compressors.append(
                ConsumerSystemComponent(
                    name=compressor.name,
                    facility_model=compressor_train,
                )
            )
            compressor_consumption_types.add(compressor_train.get_consumption_type())

        # Currently, compressor system (i.e. all of its compressors) is either electrical or turbine driven, and we
        # require all to have the same energy usage type
        # Later, we may allow the different compressors to have different energy usage types
        if not _all_equal(compressor_consumption_types):
            raise DomainValidationException("All compressors in a system must consume the same kind of energy")

        # Can't infer energy_usage_type when there are no compressors
        consumption_type = (
            compressor_consumption_types.pop()
            if len(compressor_consumption_types) == 1
            else ConsumptionType.ELECTRICITY
        )

        if consumes != consumption_type:
            raise InvalidConsumptionType(actual=consumption_type, expected=consumes)

        operational_settings: list[ConsumerSystemOperationalSettingExpressions] = []
        for operational_setting in model.operational_settings:
            if operational_setting.rate_fractions is not None:
                assert model.total_system_rate is not None
                rate_expressions = [
                    f"({model.total_system_rate}) {{*}} ({rate_fraction})"
                    for rate_fraction in operational_setting.rate_fractions
                ]

                rates: list[TimeSeriesFlowRate] = [
                    ExpressionTimeSeriesFlowRate(
                        time_series_expression=TimeSeriesExpression(
                            expression=rate_expression,
                            expression_evaluator=expression_evaluator,
                            condition=_map_condition(model),
                        ),
                        regularity=regularity,
                    )
                    for rate_expression in rate_expressions
                ]
            else:
                rates = [
                    ExpressionTimeSeriesFlowRate(
                        time_series_expression=TimeSeriesExpression(
                            expression=rate_expr,
                            expression_evaluator=expression_evaluator,
                            condition=_map_condition(model),
                        ),
                        regularity=regularity,
                    )
                    for rate_expr in operational_setting.rates
                ]

            validation_mask = [
                [
                    bool(_rate * _regularity > 0)
                    for _rate, _regularity in zip(rate.get_stream_day_values(), regularity.values)
                    if _rate is not None
                ]
                for rate in rates
            ]

            if operational_setting.suction_pressure is not None:
                suction_pressures = [
                    ExpressionTimeSeriesPressure(
                        time_series_expression=TimeSeriesExpression(
                            expression=operational_setting.suction_pressure,
                            expression_evaluator=expression_evaluator,
                        ),
                        validation_mask=mask,
                    )
                    for mask in validation_mask
                ]
            else:
                assert operational_setting.suction_pressures is not None
                suction_pressures = [
                    ExpressionTimeSeriesPressure(
                        time_series_expression=TimeSeriesExpression(
                            expression=pressure_expr, expression_evaluator=expression_evaluator
                        ),
                        validation_mask=mask,
                    )
                    for pressure_expr, mask in zip(
                        operational_setting.suction_pressures,
                        validation_mask,
                    )
                ]

            if operational_setting.discharge_pressure is not None:
                discharge_pressures = [
                    ExpressionTimeSeriesPressure(
                        time_series_expression=TimeSeriesExpression(
                            expression=operational_setting.discharge_pressure,
                            expression_evaluator=expression_evaluator,
                        ),
                        validation_mask=mask,
                    )
                    for mask in validation_mask
                ]
            else:
                assert operational_setting.discharge_pressures is not None
                discharge_pressures = [
                    ExpressionTimeSeriesPressure(
                        time_series_expression=TimeSeriesExpression(
                            expression=pressure_expr, expression_evaluator=expression_evaluator
                        ),
                        validation_mask=mask,
                    )
                    for pressure_expr, mask in zip(
                        operational_setting.discharge_pressures,
                        validation_mask,
                    )
                ]

            for suction_pressure, discharge_pressure in zip(suction_pressures, discharge_pressures):
                validate_increasing_pressure(
                    suction_pressure=suction_pressure,
                    discharge_pressure=discharge_pressure,
                )

            core_setting = CompressorSystemOperationalSettingExpressions(
                rates=rates,
                discharge_pressures=discharge_pressures,  # type: ignore[arg-type]
                suction_pressures=suction_pressures,  # type: ignore[arg-type]
                cross_overs=operational_setting.crossover,
            )
            operational_settings.append(core_setting)

        power_loss_factor_expression = TimeSeriesExpression(
            expression=model.power_loss_factor, expression_evaluator=expression_evaluator
        )
        power_loss_factor = ExpressionTimeSeriesPowerLossFactor(time_series_expression=power_loss_factor_expression)

        return CompressorSystemConsumerFunction(
            consumer_components=compressors,
            operational_settings_expressions=operational_settings,
            power_loss_factor=power_loss_factor,
        )

    def _map_pump_system(
        self, model: YamlEnergyUsageModelPumpSystem, consumes: ConsumptionType, period: Period
    ) -> PumpSystemConsumerFunction:
        regularity, expression_evaluator = self._period_subsets[period]
        if consumes != ConsumptionType.ELECTRICITY:
            raise InvalidConsumptionType(actual=ConsumptionType.ELECTRICITY, expected=consumes)

        pumps = []
        for pump in model.pumps:
            pump_model = self.__references.get_pump_model(pump.chart)
            pumps.append(ConsumerSystemComponent(name=pump.name, facility_model=pump_model))

        operational_settings: list[ConsumerSystemOperationalSettingExpressions] = []
        for operational_setting in model.operational_settings:
            if operational_setting.rate_fractions is not None:
                assert model.total_system_rate is not None
                rate_expressions = [
                    f"({model.total_system_rate}) {{*}} ({rate_fraction})"
                    for rate_fraction in operational_setting.rate_fractions
                ]

                rates: list[TimeSeriesFlowRate] = [
                    ExpressionTimeSeriesFlowRate(
                        time_series_expression=TimeSeriesExpression(
                            expression=rate_expression,
                            expression_evaluator=expression_evaluator,
                            condition=_map_condition(model),
                        ),
                        regularity=regularity,
                    )
                    for rate_expression in rate_expressions
                ]
            else:
                rates = [
                    ExpressionTimeSeriesFlowRate(
                        time_series_expression=TimeSeriesExpression(
                            expression=rate_expr,
                            expression_evaluator=expression_evaluator,
                            condition=_map_condition(model),
                        ),
                        regularity=regularity,
                    )
                    for rate_expr in operational_setting.rates
                ]

            number_of_pumps = len(pumps)

            if operational_setting.suction_pressure is not None:
                suction_pressures = [
                    ExpressionTimeSeriesPressure(
                        time_series_expression=TimeSeriesExpression(
                            expression=operational_setting.suction_pressure, expression_evaluator=expression_evaluator
                        )
                    )
                ] * number_of_pumps
            else:
                assert operational_setting.suction_pressures is not None
                suction_pressures = [
                    ExpressionTimeSeriesPressure(
                        time_series_expression=TimeSeriesExpression(
                            expression=pressure_expr, expression_evaluator=expression_evaluator
                        )
                    )
                    for pressure_expr in operational_setting.suction_pressures
                ]

            if operational_setting.discharge_pressure is not None:
                discharge_pressures = [
                    ExpressionTimeSeriesPressure(
                        time_series_expression=TimeSeriesExpression(
                            expression=operational_setting.discharge_pressure,
                            expression_evaluator=expression_evaluator,
                        )
                    )
                ] * number_of_pumps
            else:
                assert operational_setting.discharge_pressures is not None
                discharge_pressures = [
                    ExpressionTimeSeriesPressure(
                        time_series_expression=TimeSeriesExpression(
                            expression=pressure_expr, expression_evaluator=expression_evaluator
                        )
                    )
                    for pressure_expr in operational_setting.discharge_pressures
                ]

            if operational_setting.fluid_densities:
                fluid_densities = [
                    ExpressionTimeSeriesFluidDensity(
                        time_series_expression=TimeSeriesExpression(
                            expression=fluid_density_expr, expression_evaluator=expression_evaluator
                        )
                    )
                    for fluid_density_expr in operational_setting.fluid_densities
                ]
            else:
                assert model.fluid_density is not None
                fluid_densities = [
                    ExpressionTimeSeriesFluidDensity(
                        time_series_expression=TimeSeriesExpression(
                            expression=model.fluid_density, expression_evaluator=expression_evaluator
                        )
                    )
                ] * number_of_pumps

            for suction_pressure, discharge_pressure in zip(suction_pressures, discharge_pressures):
                validate_increasing_pressure(
                    suction_pressure=suction_pressure,
                    discharge_pressure=discharge_pressure,
                )
            operational_settings.append(
                PumpSystemOperationalSettingExpressions(
                    rates=rates,
                    suction_pressures=suction_pressures,  # type: ignore[arg-type]
                    discharge_pressures=discharge_pressures,  # type: ignore[arg-type]
                    cross_overs=operational_setting.crossover,
                    fluid_densities=fluid_densities,  # type: ignore[arg-type]
                )
            )

        power_loss_factor_expression = TimeSeriesExpression(
            expression=model.power_loss_factor, expression_evaluator=expression_evaluator
        )
        power_loss_factor = ExpressionTimeSeriesPowerLossFactor(time_series_expression=power_loss_factor_expression)

        return PumpSystemConsumerFunction(
            power_loss_factor=power_loss_factor,
            consumer_components=pumps,
            operational_settings_expressions=operational_settings,
        )

    def from_yaml_to_dto(
        self,
        consumes: ConsumptionType,
    ) -> TemporalModel[ConsumerFunction] | None:
        temporal_dict: dict[Period, ConsumerFunction] = {}
        for period, model in self._time_adjusted_model.items():
            try:
                if isinstance(model, YamlEnergyUsageModelDirectElectricity | YamlEnergyUsageModelDirectFuel):
                    mapped_model = self._map_direct(model=model, consumes=consumes, period=period)
                elif isinstance(model, YamlEnergyUsageModelCompressor):
                    mapped_model = self._map_compressor(model, consumes=consumes, period=period)
                elif isinstance(model, YamlEnergyUsageModelPump):
                    mapped_model = self._map_pump(model, consumes=consumes, period=period)
                elif isinstance(model, YamlEnergyUsageModelCompressorSystem):
                    mapped_model = self._map_compressor_system(model, consumes=consumes, period=period)
                elif isinstance(model, YamlEnergyUsageModelPumpSystem):
                    mapped_model = self._map_pump_system(model, consumes=consumes, period=period)
                elif isinstance(model, YamlEnergyUsageModelTabulated):
                    mapped_model = self._map_tabular(model=model, consumes=consumes, period=period)
                elif isinstance(model, YamlEnergyUsageModelCompressorTrainMultipleStreams):
                    mapped_model = self._map_multiple_streams_compressor(model, consumes=consumes, period=period)
                else:
                    assert_never(model)
                temporal_dict[period] = mapped_model
            except (InvalidConsumptionType, ValueError, InvalidExpressionError, DomainValidationException) as e:
                raise InvalidEnergyUsageModelException(
                    message=str(e),
                    period=period,
                    model=model,
                ) from e

        if len(temporal_dict) == 0:
            return None

        return TemporalModel(temporal_dict)
