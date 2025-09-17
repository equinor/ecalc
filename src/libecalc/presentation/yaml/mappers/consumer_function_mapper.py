import logging
from typing import Protocol, assert_never, overload

from pydantic import ValidationError

from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.serializable_chart import ChartDTO
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.common.units import Unit
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
    TabularEnergyFunction,
)
from libecalc.domain.infrastructure.energy_components.turbine import Turbine
from libecalc.domain.process.compressor.core import CompressorModel
from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft import CompressorTrainCommonShaft
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft_multiple_streams_and_pressures import (
    CompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.domain.process.compressor.core.train.simplified_train import (
    CompressorTrainSimplifiedKnownStages,
    CompressorTrainSimplifiedUnknownStages,
)
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage, UndefinedCompressorStage
from libecalc.domain.process.compressor.core.train.types import FluidStreamObjectForMultipleStreams
from libecalc.domain.process.compressor.dto import (
    InterstagePressureControl,
)
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.process.value_objects.chart.compressor import CompressorChart
from libecalc.domain.process.value_objects.chart.compressor.chart_creator import CompressorChartCreator
from libecalc.domain.process.value_objects.chart.compressor.compressor_chart_dto import CompressorChartDTO
from libecalc.domain.process.value_objects.chart.generic import GenericChartFromDesignPoint, GenericChartFromInput
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel
from libecalc.domain.regularity import Regularity
from libecalc.domain.resource import Resource, Resources
from libecalc.domain.time_series_flow_rate import TimeSeriesFlowRate
from libecalc.domain.time_series_variable import TimeSeriesVariable
from libecalc.expression import Expression
from libecalc.expression.expression import InvalidExpressionError
from libecalc.infrastructure.neqsim_fluid_provider.neqsim_fluid_factory import NeqSimFluidFactory
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
from libecalc.presentation.yaml.mappers.facility_input import (
    _create_pump_chart_variable_speed_dto_model_data,
    _create_pump_model_single_speed_dto_model_data,
    _get_adjustment_constant,
    _get_adjustment_factor,
    _get_float_column_or_none,
)
from libecalc.presentation.yaml.mappers.fluid_mapper import (
    _composition_fluid_model_mapper,
    _predefined_fluid_model_mapper,
)
from libecalc.presentation.yaml.mappers.model import (
    InvalidChartResourceException,
    _compressor_chart_mapper,
    _pressure_control_mapper,
    map_yaml_to_fixed_speed_pressure_control,
)
from libecalc.presentation.yaml.mappers.utils import (
    YAML_UNIT_MAPPING,
    convert_control_margin_to_fraction,
    convert_temperature_to_kelvin,
)
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.validation_errors import Location, ModelValidationError
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
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
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlCompressorTabularModel,
    YamlPumpChartSingleSpeed,
    YamlPumpChartVariableSpeed,
)
from libecalc.presentation.yaml.yaml_types.models import YamlCompressorWithTurbine
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import YamlUnknownCompressorStages
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_trains import (
    YamlMultipleStreamsStreamIngoing,
    YamlMultipleStreamsStreamOutgoing,
    YamlSimplifiedVariableSpeedCompressorTrain,
    YamlSingleSpeedCompressorTrain,
    YamlVariableSpeedCompressorTrain,
    YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_fluid import YamlCompositionFluidModel, YamlPredefinedFluidModel
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


@overload
def _create_fluid_factory(fluid_model: None) -> None: ...


@overload
def _create_fluid_factory(fluid_model: FluidModel) -> FluidFactoryInterface: ...


def _create_fluid_factory(fluid_model: FluidModel | None) -> FluidFactoryInterface | None:
    """Create a fluid factory from a fluid model."""
    if fluid_model is None:
        return None
    return NeqSimFluidFactory(fluid_model)


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


def _create_compressor_chart(
    chart_dto: CompressorChart,
) -> CompressorChart | None:
    if isinstance(chart_dto, ChartDTO):
        return CompressorChart(chart_dto)
    elif isinstance(chart_dto, GenericChartFromDesignPoint):
        return CompressorChartCreator.from_rate_and_head_design_point(
            design_actual_rate_m3_per_hour=chart_dto.design_rate_actual_m3_per_hour,
            design_head_joule_per_kg=chart_dto.design_polytropic_head_J_per_kg,
            polytropic_efficiency=chart_dto.polytropic_efficiency_fraction,
        )
    elif isinstance(chart_dto, GenericChartFromInput):
        return None
    else:
        raise NotImplementedError(f"Compressor chart type: {chart_dto.typ} has not been implemented.")


def _create_compressor_train_stage(
    compressor_chart,
    inlet_temperature_kelvin: float,
    remove_liquid_after_cooling: bool,
    pressure_drop_ahead_of_stage: float | None = None,
    interstage_pressure_control: InterstagePressureControl | None = None,
    control_margin: float = 0.0,
) -> CompressorTrainStage:
    if isinstance(compressor_chart, GenericChartFromInput):
        return UndefinedCompressorStage(
            polytropic_efficiency=compressor_chart.polytropic_efficiency_fraction,
            inlet_temperature_kelvin=inlet_temperature_kelvin,
            remove_liquid_after_cooling=remove_liquid_after_cooling,
            pressure_drop_ahead_of_stage=pressure_drop_ahead_of_stage,
        )
    compressor_chart = _create_compressor_chart(chart_dto=compressor_chart)
    if control_margin > 0 and compressor_chart is not None:
        compressor_chart = compressor_chart.get_chart_adjusted_for_control_margin(control_margin)
    return CompressorTrainStage(
        compressor_chart=compressor_chart,
        inlet_temperature_kelvin=inlet_temperature_kelvin,
        remove_liquid_after_cooling=remove_liquid_after_cooling,
        pressure_drop_ahead_of_stage=pressure_drop_ahead_of_stage,
        interstage_pressure_control=interstage_pressure_control,
    )


class CompressorModelMapper:
    def __init__(self, resources: Resources, reference_service: ReferenceService, configuration: YamlValidator):
        self._reference_service = reference_service
        self._resources = resources
        self._configuration = configuration

    def _create_error(self, message: str, reference: str, key: str | None = None):
        yaml_path = self._reference_service.get_yaml_path(reference)

        location_keys = [*yaml_path.keys[:-1], reference]  # Replace index with name

        if key is not None:
            key_path = yaml_path.append(key)
            location_keys.append(key)
        else:
            key_path = yaml_path

        file_context = self._configuration.get_file_context(key_path.keys)
        return ModelValidationError(
            message=message,
            location=Location(keys=location_keys),
            name=reference,
            file_context=file_context,
        )

    def _get_resource(self, resource_name: str, reference: str) -> Resource:
        resource = self._resources.get(resource_name)
        if resource is None:
            raise ModelValidationException(
                errors=[
                    self._create_error(
                        message=f"Unable to find resource '{resource_name}'", reference=reference, key="FILE"
                    )
                ]
            )
        return resource

    def _get_fluid_model(self, reference: str) -> FluidModel:
        model = self._reference_service.get_fluid(reference)
        try:
            if isinstance(model, YamlPredefinedFluidModel):
                return _predefined_fluid_model_mapper(model)
            elif isinstance(model, YamlCompositionFluidModel):
                return _composition_fluid_model_mapper(model)
            else:
                assert_never(model)
        except ValidationError as ve:
            raise ModelValidationException.from_pydantic(
                validation_error=ve,
                file_context=self._configuration.get_file_context(
                    self._reference_service.get_yaml_path(reference).keys
                ),
            ) from ve
        except DomainValidationException as e:
            raise ModelValidationException(errors=[self._create_error(str(e), reference)]) from e

    def _get_compressor_chart(self, reference: str) -> CompressorChartDTO:
        model = self._reference_service.get_compressor_chart(reference)
        try:
            return _compressor_chart_mapper(model_config=model, resources=self._resources)
        except ValidationError as ve:
            raise ModelValidationException.from_pydantic(
                validation_error=ve,
                file_context=self._configuration.get_file_context(
                    self._reference_service.get_yaml_path(reference).keys
                ),
            ) from ve
        except DomainValidationException as e:
            raise ModelValidationException(errors=[self._create_error(str(e), reference)]) from e

    def _create_simplified_variable_speed_compressor_train(self, model: YamlSimplifiedVariableSpeedCompressorTrain):
        fluid_model_reference: str = model.fluid_model
        fluid_model = self._get_fluid_model(fluid_model_reference)
        fluid_factory = _create_fluid_factory(fluid_model)
        if fluid_factory is None:
            raise ValueError("Fluid model is required for compressor train")

        train_spec = model.compressor_train

        if not isinstance(train_spec, YamlUnknownCompressorStages):
            # The stages are pre defined, known
            yaml_stages = train_spec.stages
            stages = [
                _create_compressor_train_stage(
                    inlet_temperature_kelvin=convert_temperature_to_kelvin(
                        [stage.inlet_temperature],
                        input_unit=Unit.CELSIUS,
                    )[0],
                    compressor_chart=self._get_compressor_chart(stage.compressor_chart),
                    pressure_drop_ahead_of_stage=0,
                    control_margin=0,
                    remove_liquid_after_cooling=True,
                )
                for stage in yaml_stages
            ]

            return CompressorTrainSimplifiedKnownStages(
                fluid_factory=fluid_factory,
                stages=stages,
                energy_usage_adjustment_constant=model.power_adjustment_constant,
                energy_usage_adjustment_factor=model.power_adjustment_factor,
                calculate_max_rate=model.calculate_max_rate,
                maximum_power=model.maximum_power,
            )
        else:
            # The stages are unknown, not defined
            compressor_chart_reference = train_spec.compressor_chart
            stage = _create_compressor_train_stage(
                compressor_chart=self._get_compressor_chart(compressor_chart_reference),
                inlet_temperature_kelvin=convert_temperature_to_kelvin(
                    [train_spec.inlet_temperature],
                    input_unit=Unit.CELSIUS,
                )[0],
                pressure_drop_ahead_of_stage=0,
                remove_liquid_after_cooling=True,
                # control_margin=0,  # mypy needs this?
            )

            return CompressorTrainSimplifiedUnknownStages(
                fluid_factory=fluid_factory,
                stage=stage,
                energy_usage_adjustment_constant=model.power_adjustment_constant,
                energy_usage_adjustment_factor=model.power_adjustment_factor,
                calculate_max_rate=model.calculate_max_rate,
                maximum_pressure_ratio_per_stage=train_spec.maximum_pressure_ratio_per_stage,  # type: ignore[arg-type]
                maximum_power=model.maximum_power,
            )

    def _create_variable_speed_compressor_train(
        self, model: YamlVariableSpeedCompressorTrain
    ) -> CompressorTrainCommonShaft:
        fluid_model_reference: str = model.fluid_model
        fluid_model = self._get_fluid_model(fluid_model_reference)

        train_spec = model.compressor_train

        # The stages are pre defined, known
        stages_data = train_spec.stages

        stages: list[CompressorTrainStage] = []
        for stage in stages_data:
            control_margin = convert_control_margin_to_fraction(
                stage.control_margin,
                YAML_UNIT_MAPPING[stage.control_margin_unit],
            )

            compressor_chart = self._get_compressor_chart(stage.compressor_chart)

            stages.append(
                _create_compressor_train_stage(
                    compressor_chart=compressor_chart,
                    inlet_temperature_kelvin=convert_temperature_to_kelvin(
                        [stage.inlet_temperature],
                        input_unit=Unit.CELSIUS,
                    )[0],
                    remove_liquid_after_cooling=True,
                    pressure_drop_ahead_of_stage=stage.pressure_drop_ahead_of_stage,
                    control_margin=control_margin,
                )
            )
        pressure_control = _pressure_control_mapper(model)
        fluid_factory = _create_fluid_factory(fluid_model)
        if fluid_factory is None:
            raise ValueError("Fluid model is required for compressor train")

        return CompressorTrainCommonShaft(
            fluid_factory=fluid_factory,
            stages=stages,
            energy_usage_adjustment_constant=model.power_adjustment_constant,
            energy_usage_adjustment_factor=model.power_adjustment_factor,
            calculate_max_rate=model.calculate_max_rate,  # type: ignore[arg-type]
            pressure_control=pressure_control,
            maximum_power=model.maximum_power,
        )

    def _create_single_speed_compressor_train(
        self, model: YamlSingleSpeedCompressorTrain
    ) -> CompressorTrainCommonShaft:
        fluid_model_reference = model.fluid_model
        fluid_model = self._get_fluid_model(fluid_model_reference)

        train_spec = model.compressor_train

        stages: list[CompressorTrainStage] = [
            _create_compressor_train_stage(
                compressor_chart=self._get_compressor_chart(stage.compressor_chart),
                inlet_temperature_kelvin=convert_temperature_to_kelvin(
                    [stage.inlet_temperature],
                    input_unit=Unit.CELSIUS,
                )[0],
                remove_liquid_after_cooling=True,
                pressure_drop_ahead_of_stage=stage.pressure_drop_ahead_of_stage,
                control_margin=convert_control_margin_to_fraction(
                    stage.control_margin,
                    YAML_UNIT_MAPPING[stage.control_margin_unit],
                ),
            )
            for stage in train_spec.stages
        ]
        pressure_control = _pressure_control_mapper(model)
        maximum_discharge_pressure = model.maximum_discharge_pressure
        if maximum_discharge_pressure and pressure_control != FixedSpeedPressureControl.DOWNSTREAM_CHOKE:
            raise DomainValidationException(
                f"Setting maximum discharge pressure for single speed compressor train is currently"
                f"only supported with {FixedSpeedPressureControl.DOWNSTREAM_CHOKE} pressure control"
                f"option. Pressure control option is {pressure_control}"
            )

        fluid_factory = _create_fluid_factory(fluid_model)
        if fluid_factory is None:
            raise ValueError("Fluid model is required for compressor train")

        return CompressorTrainCommonShaft(
            fluid_factory=fluid_factory,
            stages=stages,
            pressure_control=pressure_control,
            maximum_discharge_pressure=maximum_discharge_pressure,
            energy_usage_adjustment_constant=model.power_adjustment_constant,
            energy_usage_adjustment_factor=model.power_adjustment_factor,
            calculate_max_rate=model.calculate_max_rate,
            maximum_power=model.maximum_power,
        )

    def _create_turbine(self, reference: str) -> Turbine:
        model = self._reference_service.get_turbine(reference)
        try:
            return Turbine(
                lower_heating_value=model.lower_heating_value,
                loads=model.turbine_loads,
                efficiency_fractions=model.turbine_efficiencies,
                energy_usage_adjustment_constant=model.power_adjustment_constant,
                energy_usage_adjustment_factor=model.power_adjustment_factor,
            )
        except DomainValidationException as e:
            raise ModelValidationException(errors=[self._create_error(str(e), reference)]) from e

    def _create_compressor_with_turbine(self, model: YamlCompressorWithTurbine) -> CompressorWithTurbineModel:
        compressor_train_model = self.create_compressor_model(model.compressor_model)
        turbine_model = self._create_turbine(model.turbine_model)

        return CompressorWithTurbineModel(
            energy_usage_adjustment_constant=model.power_adjustment_constant,
            energy_usage_adjustment_factor=model.power_adjustment_factor,
            compressor_energy_function=compressor_train_model,
            turbine_model=turbine_model,
        )

    def _create_variable_speed_compressor_train_multiple_streams_and_pressures(
        self, model: YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures
    ) -> CompressorTrainCommonShaftMultipleStreamsAndPressures:
        stream_references = {stream.name for stream in model.streams}
        stages: list[CompressorTrainStage] = []

        stream_to_stage_map: dict[str, int] = {}

        for stage_index, stage_config in enumerate(model.stages):
            compressor_chart_reference = stage_config.compressor_chart
            compressor_chart = self._get_compressor_chart(compressor_chart_reference)
            inlet_temperature_kelvin = convert_temperature_to_kelvin(
                [stage_config.inlet_temperature],
                input_unit=Unit.CELSIUS,
            )[0]
            pressure_drop_ahead_of_stage = stage_config.pressure_drop_ahead_of_stage
            control_margin = stage_config.control_margin
            control_margin_unit = stage_config.control_margin_unit
            control_margin_fraction = convert_control_margin_to_fraction(
                control_margin,
                YAML_UNIT_MAPPING[control_margin_unit],
            )

            stream_references_this_stage = stage_config.stream
            if stream_references_this_stage is not None:
                for stream_reference in stream_references_this_stage:
                    if stream_reference not in stream_references:
                        raise DomainValidationException(f"Stream '{stream_reference}' not properly defined")

                    if stream_reference in stream_to_stage_map:
                        raise DomainValidationException(
                            f"Stream '{stream_reference}' used in multiple stages ({stream_to_stage_map[stream_reference]} and {stage_index})"
                        )

                    stream_to_stage_map[stream_reference] = stage_index

            interstage_pressure_control_config = stage_config.interstage_control_pressure
            interstage_pressure_control = None
            if interstage_pressure_control_config is not None:
                interstage_pressure_control = InterstagePressureControl(
                    upstream_pressure_control=map_yaml_to_fixed_speed_pressure_control(
                        interstage_pressure_control_config.upstream_pressure_control
                    ),
                    downstream_pressure_control=map_yaml_to_fixed_speed_pressure_control(
                        interstage_pressure_control_config.downstream_pressure_control
                    ),
                )

            stages.append(
                _create_compressor_train_stage(
                    compressor_chart=compressor_chart,
                    inlet_temperature_kelvin=inlet_temperature_kelvin,
                    pressure_drop_ahead_of_stage=pressure_drop_ahead_of_stage,
                    remove_liquid_after_cooling=True,
                    control_margin=control_margin_fraction,
                    interstage_pressure_control=interstage_pressure_control,
                )
            )

        pressure_control = _pressure_control_mapper(model)

        streams: list[FluidStreamObjectForMultipleStreams] = []
        for stream_config in model.streams:
            reference_name = stream_config.name
            stage_no = stream_to_stage_map[reference_name]
            if isinstance(stream_config, YamlMultipleStreamsStreamOutgoing):
                streams.append(
                    FluidStreamObjectForMultipleStreams(
                        name=reference_name,
                        fluid_model=None,
                        is_inlet_stream=False,
                        connected_to_stage_no=stage_no,
                    )
                )

            elif isinstance(stream_config, YamlMultipleStreamsStreamIngoing):
                fluid_model = self._get_fluid_model(stream_config.fluid_model)
                streams.append(
                    FluidStreamObjectForMultipleStreams(
                        name=reference_name,
                        fluid_model=fluid_model,
                        is_inlet_stream=True,
                        connected_to_stage_no=stage_no,
                    )
                )
            else:
                assert_never(stream_config)

        fluid_model_train_inlet: FluidModel | None = None
        for stream in streams:
            if stream.is_inlet_stream:
                assert stream.fluid_model is not None
                fluid_model_train_inlet = stream.fluid_model
                break

        if fluid_model_train_inlet is None:
            raise DomainValidationException("An inlet stream is required for this model")

        fluid_factory_train_inlet = _create_fluid_factory(fluid_model_train_inlet)

        interstage_pressures = {stage_index for stage_index, stage in enumerate(stages) if stage.has_control_pressure}
        assert len(interstage_pressures) <= 1
        has_interstage_pressure = len(interstage_pressures) == 1
        stage_number_interstage_pressure = interstage_pressures.pop() if has_interstage_pressure else None

        return CompressorTrainCommonShaftMultipleStreamsAndPressures(
            fluid_factory=fluid_factory_train_inlet,
            streams=streams,
            energy_usage_adjustment_constant=model.power_adjustment_constant,
            energy_usage_adjustment_factor=model.power_adjustment_factor,
            stages=stages,
            calculate_max_rate=False,  # TODO: Not supported?,
            maximum_power=model.maximum_power,
            pressure_control=pressure_control,
            stage_number_interstage_pressure=stage_number_interstage_pressure,
        )

    def _create_compressor_sampled(self, model: YamlCompressorTabularModel, reference: str) -> CompressorModelSampled:
        rate_header = EcalcYamlKeywords.consumer_function_rate
        suction_pressure_header = EcalcYamlKeywords.consumer_function_suction_pressure
        discharge_pressure_header = EcalcYamlKeywords.consumer_function_discharge_pressure
        power_header = EcalcYamlKeywords.consumer_tabular_power
        fuel_header = EcalcYamlKeywords.consumer_tabular_fuel

        resource = self._get_resource(model.file, reference)
        resource_headers = resource.get_headers()

        has_fuel = fuel_header in resource_headers

        energy_usage_header = fuel_header if has_fuel else power_header

        rate_values = _get_float_column_or_none(resource, rate_header)
        suction_pressure_values = _get_float_column_or_none(resource, suction_pressure_header)
        discharge_pressure_values = _get_float_column_or_none(resource, discharge_pressure_header)
        energy_usage_values = resource.get_float_column(energy_usage_header)

        # In case of a fuel-driven compressor, the user may provide power interpolation data to emulate turbine power usage in results
        power_interpolation_values = None
        if has_fuel:
            power_interpolation_values = _get_float_column_or_none(resource, power_header)

        return CompressorModelSampled(
            energy_usage_adjustment_constant=_get_adjustment_constant(data=model),
            energy_usage_adjustment_factor=_get_adjustment_factor(data=model),
            energy_usage_type=EnergyUsageType.FUEL if energy_usage_header == fuel_header else EnergyUsageType.POWER,
            energy_usage_values=energy_usage_values,
            rate_values=rate_values,
            suction_pressure_values=suction_pressure_values,
            discharge_pressure_values=discharge_pressure_values,
            power_interpolation_values=power_interpolation_values,
        )

    def create_compressor_model(self, reference: str) -> CompressorModel:
        model = self._reference_service.get_compressor_model(reference)
        try:
            if isinstance(model, YamlSimplifiedVariableSpeedCompressorTrain):
                return self._create_simplified_variable_speed_compressor_train(model)
            elif isinstance(model, YamlVariableSpeedCompressorTrain):
                return self._create_variable_speed_compressor_train(model)
            elif isinstance(model, YamlSingleSpeedCompressorTrain):
                return self._create_single_speed_compressor_train(model)
            elif isinstance(model, YamlCompressorWithTurbine):
                return self._create_compressor_with_turbine(model)
            elif isinstance(model, YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures):
                return self._create_variable_speed_compressor_train_multiple_streams_and_pressures(model)
            elif isinstance(model, YamlCompressorTabularModel):
                return self._create_compressor_sampled(model, reference)
            else:
                assert_never(model)
        except DomainValidationException as e:
            raise ModelValidationException(errors=[self._create_error(str(e), reference=reference)]) from e


class TabularModelMapper:
    def __init__(self, resources: Resources, reference_service: ReferenceService, configuration: YamlValidator):
        self._reference_service = reference_service
        self._resources = resources
        self._configuration = configuration

    def _create_error(self, message: str, reference: str, key: str | None = None):
        yaml_path = self._reference_service.get_yaml_path(reference)

        location_keys = [*yaml_path.keys[:-1], reference]  # Replace index with name

        if key is not None:
            key_path = yaml_path.append(key)
            location_keys.append(key)
        else:
            key_path = yaml_path

        file_context = self._configuration.get_file_context(key_path.keys)
        return ModelValidationError(
            message=message,
            location=Location(keys=location_keys),
            name=reference,
            file_context=file_context,
        )

    def _get_resource(self, resource_name: str, reference: str) -> Resource:
        resource = self._resources.get(resource_name)
        if resource is None:
            raise ModelValidationException(
                errors=[
                    self._create_error(
                        message=f"Unable to find resource '{resource_name}'", reference=reference, key="FILE"
                    )
                ]
            )
        return resource

    def create_tabular_model(self, reference: str) -> TabularEnergyFunction:
        tabular_model = self._reference_service.get_tabulated_model(reference)
        resource = self._get_resource(tabular_model.file, reference)

        try:
            resource_headers = resource.get_headers()
            resource_data = [resource.get_float_column(header) for header in resource_headers]

            return TabularEnergyFunction(
                headers=resource_headers,
                data=resource_data,
                energy_usage_adjustment_factor=_get_adjustment_factor(data=tabular_model),
                energy_usage_adjustment_constant=_get_adjustment_constant(data=tabular_model),
            )
        except DomainValidationException as e:
            raise ModelValidationException(errors=[self._create_error(str(e), reference=reference)]) from e


class PumpModelMapper:
    def __init__(self, resources: Resources, reference_service: ReferenceService, configuration: YamlValidator):
        self._reference_service = reference_service
        self._resources = resources
        self._configuration = configuration

    def _create_error(self, message: str, reference: str, key: str | None = None):
        yaml_path = self._reference_service.get_yaml_path(reference)

        location_keys = [*yaml_path.keys[:-1], reference]  # Replace index with name

        if key is not None:
            key_path = yaml_path.append(key)
            location_keys.append(key)
        else:
            key_path = yaml_path

        file_context = self._configuration.get_file_context(key_path.keys)
        return ModelValidationError(
            message=message,
            location=Location(keys=location_keys),
            name=reference,
            file_context=file_context,
        )

    def _get_resource(self, resource_name: str, reference: str) -> Resource:
        resource = self._resources.get(resource_name)
        if resource is None:
            raise ModelValidationException(
                errors=[
                    self._create_error(
                        message=f"Unable to find resource '{resource_name}'", reference=reference, key="FILE"
                    )
                ]
            )
        return resource

    def create_pump_model(self, reference: str) -> PumpModel:
        model = self._reference_service.get_pump_model(reference)
        resource_name = model.file
        resource = self._get_resource(resource_name, reference)
        try:
            if isinstance(model, YamlPumpChartSingleSpeed):
                return _create_pump_model_single_speed_dto_model_data(resource=resource, facility_data=model)
            elif isinstance(model, YamlPumpChartVariableSpeed):
                return _create_pump_chart_variable_speed_dto_model_data(resource=resource, facility_data=model)
        except DomainValidationException as e:
            raise ModelValidationException(errors=[self._create_error(str(e), reference=reference)]) from e
        except InvalidResourceException as e:
            raise InvalidChartResourceException(
                message=str(e), file_mark=e.file_mark, resource_name=resource_name
            ) from e


class ConsumerFunctionMapper:
    def __init__(
        self,
        configuration: YamlValidator,
        resources: Resources,
        references: ReferenceService,
        target_period: Period,
        expression_evaluator: ExpressionEvaluator,
        regularity: Regularity,
        energy_usage_model: YamlTemporalModel[YamlFuelEnergyUsageModel]
        | YamlTemporalModel[YamlElectricityEnergyUsageModel],
    ):
        self._configuration = configuration
        self._resources = resources
        self.__references = references
        self._compressor_model_mapper = CompressorModelMapper(
            resources=resources, configuration=configuration, reference_service=references
        )
        self._tabular_model_mapper = TabularModelMapper(
            resources=resources, configuration=configuration, reference_service=references
        )
        self._pump_model_mapper = PumpModelMapper(
            resources=resources, configuration=configuration, reference_service=references
        )
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
        energy_model = self._tabular_model_mapper.create_tabular_model(model.energy_function)
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
        pump_model = self._pump_model_mapper.create_pump_model(model.energy_function)
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
        compressor_train_model = self._compressor_model_mapper.create_compressor_model(model.compressor_train_model)
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
        compressor_model = self._compressor_model_mapper.create_compressor_model(model.energy_function)
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
            compressor_train = self._compressor_model_mapper.create_compressor_model(compressor.compressor_model)

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
            pump_model = self._pump_model_mapper.create_pump_model(pump.chart)
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
            except InvalidChartResourceException as e:
                raise ModelValidationException(
                    errors=[
                        ModelValidationError(
                            message=str(e),
                            location=e.location,
                            file_context=e.file_context,
                        ),
                    ],
                ) from e

        if len(temporal_dict) == 0:
            return None

        return TemporalModel(temporal_dict)
