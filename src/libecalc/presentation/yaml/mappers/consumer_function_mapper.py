import logging
import uuid
from typing import Protocol, assert_never, overload

import numpy as np
from pydantic import ValidationError

from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl, InterstagePressureControl
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
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.direct_consumer_function import (
    DirectConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.consumer_function import (
    ConsumerSystemConsumerFunction,
    SystemComponent,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    ConsumerSystemOperationalSettingExpressions,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.types import ConsumerSystemComponent
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated import (
    TabularConsumerFunction,
    TabularEnergyFunction,
)
from libecalc.domain.infrastructure.energy_components.turbine import Turbine
from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel, calculate_pressure_ratio_per_stage
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft import CompressorTrainCommonShaft
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft_multiple_streams_and_pressures import (
    CompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.domain.process.compressor.core.train.simplified_train.simplified_train import CompressorTrainSimplified
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.compressor.core.train.types import FluidStreamObjectForMultipleStreams
from libecalc.domain.process.entities.process_units.compressor.compressor import Compressor
from libecalc.domain.process.entities.process_units.liquid_remover.liquid_remover import LiquidRemover
from libecalc.domain.process.entities.process_units.mixer.mixer import Mixer
from libecalc.domain.process.entities.process_units.pressure_modifier.pressure_modifier import (
    DifferentialPressureModifier,
)
from libecalc.domain.process.entities.process_units.rate_modifier.rate_modifier import RateModifier
from libecalc.domain.process.entities.process_units.splitter.splitter import Splitter
from libecalc.domain.process.entities.process_units.temperature_setter.temperature_setter import TemperatureSetter
from libecalc.domain.process.entities.shaft import SingleSpeedShaft, VariableSpeedShaft
from libecalc.domain.process.evaluation_input import (
    CompressorEvaluationInput,
    CompressorSampledEvaluationInput,
    PumpEvaluationInput,
)
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel
from libecalc.domain.regularity import Regularity
from libecalc.domain.resource import Resource, Resources
from libecalc.domain.time_series_flow_rate import TimeSeriesFlowRate
from libecalc.domain.time_series_variable import TimeSeriesVariable
from libecalc.expression import Expression
from libecalc.expression.expression import InvalidExpressionError
from libecalc.infrastructure.neqsim_fluid_provider.neqsim_fluid_factory import NeqSimFluidFactory
from libecalc.presentation.yaml.domain.ecalc_components import (
    CompressorProcessSystemComponent,
    CompressorSampledComponent,
    PumpProcessSystemComponent,
)
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
from libecalc.presentation.yaml.mappers.charts.generic_from_input_chart_data import GenericFromInputChartData
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
    _generic_from_design_point_compressor_chart_mapper,
    _pressure_control_mapper,
    _single_speed_compressor_chart_mapper,
    _variable_speed_compressor_chart_mapper,
    map_yaml_to_fixed_speed_pressure_control,
)
from libecalc.presentation.yaml.mappers.simplified_train_mapping_utils import (
    CompressorOperationalTimeSeries,
    calculate_number_of_stages,
)
from libecalc.presentation.yaml.mappers.utils import (
    YAML_UNIT_MAPPING,
    convert_control_margin_to_fraction,
    convert_efficiency_to_fraction,
    convert_temperature_to_kelvin,
)
from libecalc.presentation.yaml.mappers.yaml_mapping_context import MappingContext
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
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import (
    YamlGenericFromDesignPointChart,
    YamlGenericFromInputChart,
    YamlSingleSpeedChart,
    YamlVariableSpeedChart,
)
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


def _is_sampled_compressor(model: CompressorTrainModel | CompressorModelSampled | CompressorWithTurbineModel) -> bool:
    if isinstance(model, CompressorModelSampled):
        return True
    if isinstance(model, CompressorWithTurbineModel) and isinstance(model.compressor_model, CompressorModelSampled):
        return True
    return False


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
                        message=f"Invalid pressures at index {i + 1}: suction pressure ({sp}) must be less than intermediate pressure ({ip}), which must be less than discharge pressure ({dp})."
                    )
            else:
                if not (sp <= dp):
                    raise ProcessPressureRatioValidationException(
                        message=f"Invalid pressures at index {i + 1}: suction pressure ({sp}) must be less than discharge pressure ({dp})."
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

    def _get_compressor_chart(
        self,
        reference: str,
        control_margin: float | None,
    ) -> ChartData:
        model = self._reference_service.get_compressor_chart(reference)
        assert isinstance(model, YamlSingleSpeedChart | YamlVariableSpeedChart)  # Generic charts are handled separately
        try:
            if isinstance(model, YamlSingleSpeedChart):
                return _single_speed_compressor_chart_mapper(
                    model_config=model, resources=self._resources, control_margin=control_margin
                )
            elif isinstance(model, YamlVariableSpeedChart):
                return _variable_speed_compressor_chart_mapper(
                    model_config=model, resources=self._resources, control_margin=control_margin
                )
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

    def _create_compressor_train_stage(
        self,
        compressor_chart_reference: str,
        inlet_temperature_kelvin: float,
        remove_liquid_after_cooling: bool,
        number_of_mixer_ports_this_stage: int = 0,
        number_of_splitter_ports_this_stage: int = 0,
        pressure_drop_ahead_of_stage: float | None = None,
        interstage_pressure_control: InterstagePressureControl | None = None,
        control_margin: float | None = None,
    ) -> CompressorTrainStage:
        chart_data = self._get_compressor_chart(compressor_chart_reference, control_margin)

        return CompressorTrainStage(
            rate_modifier=RateModifier(),
            compressor=Compressor(chart_data),
            temperature_setter=TemperatureSetter(inlet_temperature_kelvin),
            liquid_remover=LiquidRemover() if remove_liquid_after_cooling else None,
            pressure_modifier=(
                DifferentialPressureModifier(pressure_drop_ahead_of_stage) if pressure_drop_ahead_of_stage else None
            ),
            interstage_pressure_control=interstage_pressure_control,
            splitter=(
                Splitter(number_of_splitter_ports_this_stage + 1) if number_of_splitter_ports_this_stage > 0 else None
            ),
            mixer=(Mixer(number_of_mixer_ports_this_stage + 1) if number_of_mixer_ports_this_stage > 0 else None),
        )

    def _create_variable_speed_compressor_train(
        self, model: YamlVariableSpeedCompressorTrain
    ) -> tuple[CompressorTrainCommonShaft, FluidFactoryInterface]:
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

            stages.append(
                self._create_compressor_train_stage(
                    compressor_chart_reference=stage.compressor_chart,
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
            raise DomainValidationException("Fluid model is required for compressor train")

        compressor_model = CompressorTrainCommonShaft(
            stages=stages,
            shaft=VariableSpeedShaft(),
            energy_usage_adjustment_constant=model.power_adjustment_constant,
            energy_usage_adjustment_factor=model.power_adjustment_factor,
            calculate_max_rate=model.calculate_max_rate,  # type: ignore[arg-type]
            pressure_control=pressure_control,
            maximum_power=model.maximum_power,
        )
        return compressor_model, fluid_factory

    def _create_single_speed_compressor_train(
        self, model: YamlSingleSpeedCompressorTrain
    ) -> tuple[CompressorTrainCommonShaft, FluidFactoryInterface]:
        fluid_model_reference = model.fluid_model
        fluid_model = self._get_fluid_model(fluid_model_reference)

        train_spec = model.compressor_train

        stages: list[CompressorTrainStage] = [
            self._create_compressor_train_stage(
                compressor_chart_reference=stage.compressor_chart,
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
            raise DomainValidationException("Fluid model is required for compressor train")

        compressor_model = CompressorTrainCommonShaft(
            stages=stages,
            shaft=SingleSpeedShaft(),
            pressure_control=pressure_control,
            maximum_discharge_pressure=maximum_discharge_pressure,
            energy_usage_adjustment_constant=model.power_adjustment_constant,
            energy_usage_adjustment_factor=model.power_adjustment_factor,
            calculate_max_rate=model.calculate_max_rate,
            maximum_power=model.maximum_power,
        )
        return compressor_model, fluid_factory

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

    def _create_compressor_with_turbine(
        self,
        model: YamlCompressorWithTurbine,
        operational_data: CompressorOperationalTimeSeries | None = None,
    ) -> tuple[CompressorWithTurbineModel, FluidFactoryInterface]:
        compressor_train_model, fluid_factory = self.create_compressor_model(
            model.compressor_model, operational_data=operational_data
        )
        assert isinstance(compressor_train_model, CompressorTrainModel | CompressorModelSampled)
        turbine_model = self._create_turbine(model.turbine_model)

        return CompressorWithTurbineModel(
            energy_usage_adjustment_constant=model.power_adjustment_constant,
            energy_usage_adjustment_factor=model.power_adjustment_factor,
            compressor_energy_function=compressor_train_model,
            turbine_model=turbine_model,
        ), fluid_factory

    def _create_simplified_model_with_prepared_stages(
        self,
        model: YamlSimplifiedVariableSpeedCompressorTrain,
        operational_data: CompressorOperationalTimeSeries | None,
    ) -> tuple[CompressorTrainSimplified, FluidFactoryInterface]:
        """Create simplified compressor model with stages prepared from operational data.

        Args:
            model: YAML simplified compressor model configuration
            operational_data: Operational time series data (rates and pressures)

        Returns:
            CompressorTrainSimplified with stages prepared for the given data

        Raises:
            DomainValidationException: If operational data is invalid (validated by dataclass)
        """
        # Create fluid factory - delegate to CompressorModelMapper
        fluid_model = self._get_fluid_model(model.fluid_model)
        fluid_factory = _create_fluid_factory(fluid_model)

        train_spec = model.compressor_train

        if isinstance(train_spec, YamlUnknownCompressorStages):
            assert operational_data is not None
            # For unknown stages, maximum_pressure_ratio_per_stage is required to determine stage count
            if train_spec.maximum_pressure_ratio_per_stage is None:
                raise DomainValidationException(
                    "MAXIMUM_PRESSURE_RATIO_PER_STAGE is required for unknown compressor stages"
                )

            suction_pressure = operational_data.suction_pressures
            discharge_pressure = operational_data.discharge_pressures
            if suction_pressure is None:
                raise DomainValidationException(
                    "SUCTION_PRESSURE is required for simplified compressor model. "
                    "Simplified models perform thermodynamic calculations that require pressure data."
                )
            if discharge_pressure is None:
                raise DomainValidationException(
                    "DISCHARGE_PRESSURE is required for simplified compressor model. "
                    "Simplified models perform thermodynamic calculations that require pressure data."
                )

            number_of_stages = calculate_number_of_stages(
                maximum_pressure_ratio_per_stage=train_spec.maximum_pressure_ratio_per_stage,
                suction_pressures=suction_pressure,
                discharge_pressures=discharge_pressure,
            )
            yaml_stages = [train_spec for _ in range(number_of_stages)]
        else:
            # Known stages: prepare charts for existing stages
            yaml_stages = train_spec.stages

        # operational_data might be None if simplified train with known stages and only generic from design point is used in a system.
        # That means it's a fully defined train without knowing operational data.
        stages: list[CompressorTrainStage] = []
        if operational_data is None:
            # Expect only generic from design point
            for yaml_stage in yaml_stages:
                yaml_chart = self._reference_service.get_compressor_chart(yaml_stage.compressor_chart)
                assert isinstance(yaml_chart, YamlGenericFromDesignPointChart)
                chart = _generic_from_design_point_compressor_chart_mapper(yaml_chart)
                inlet_temperature_kelvin = convert_temperature_to_kelvin(
                    [yaml_stage.inlet_temperature],
                    input_unit=Unit.CELSIUS,
                )[0]
                stages.append(
                    CompressorTrainStage(
                        rate_modifier=RateModifier(),
                        compressor=Compressor(chart),
                        temperature_setter=TemperatureSetter(required_temperature_kelvin=inlet_temperature_kelvin),
                        liquid_remover=LiquidRemover(),
                    )
                )
        else:
            # Expect generic from input, keep track of inlet and outlet pressures per stage since that is used to create generic from input charts
            suction_pressures = operational_data.suction_pressures
            discharge_pressures = operational_data.discharge_pressures
            if suction_pressures is None:
                raise DomainValidationException(
                    "SUCTION_PRESSURE is required for simplified compressor model. "
                    "Simplified models perform thermodynamic calculations that require pressure data."
                )
            if discharge_pressures is None:
                raise DomainValidationException(
                    "DISCHARGE_PRESSURE is required for simplified compressor model. "
                    "Simplified models perform thermodynamic calculations that require pressure data."
                )
            pressure_ratios_per_stage = np.asarray(
                [
                    calculate_pressure_ratio_per_stage(
                        suction_pressure=sp, discharge_pressure=dp, n_stages=len(yaml_stages)
                    )
                    for sp, dp in zip(suction_pressures, discharge_pressures)
                ]
            )

            stage_inlet_pressure = suction_pressures
            for yaml_stage in yaml_stages:
                stage_outlet_pressure = np.multiply(stage_inlet_pressure, pressure_ratios_per_stage)
                yaml_chart = self._reference_service.get_compressor_chart(yaml_stage.compressor_chart)
                inlet_temperature_kelvin = convert_temperature_to_kelvin(
                    [yaml_stage.inlet_temperature],
                    input_unit=Unit.CELSIUS,
                )[0]
                if isinstance(yaml_chart, YamlGenericFromDesignPointChart):
                    chart = _generic_from_design_point_compressor_chart_mapper(yaml_chart)
                else:
                    assert isinstance(yaml_chart, YamlGenericFromInputChart)
                    chart = GenericFromInputChartData(
                        fluid_factory=fluid_factory,
                        inlet_temperature=inlet_temperature_kelvin,
                        inlet_pressure=stage_inlet_pressure.tolist(),
                        standard_rates=operational_data.rates.tolist(),
                        outlet_pressure=stage_outlet_pressure.tolist(),
                        polytropic_efficiency=convert_efficiency_to_fraction(
                            efficiency_values=[yaml_chart.polytropic_efficiency],
                            input_unit=YAML_UNIT_MAPPING[yaml_chart.units.efficiency],
                        )[0],
                    )

                stage_inlet_pressure = stage_outlet_pressure

                stages.append(
                    CompressorTrainStage(
                        rate_modifier=RateModifier(),
                        compressor=Compressor(chart),
                        temperature_setter=TemperatureSetter(required_temperature_kelvin=inlet_temperature_kelvin),
                        liquid_remover=LiquidRemover(),
                    )
                )

        # Return unified model with immutable prepared stages
        return CompressorTrainSimplified(
            stages=stages,
            energy_usage_adjustment_constant=model.power_adjustment_constant,
            energy_usage_adjustment_factor=model.power_adjustment_factor,
            calculate_max_rate=model.calculate_max_rate,
            maximum_power=model.maximum_power,
        ), fluid_factory

    def _create_variable_speed_compressor_train_multiple_streams_and_pressures(
        self, model: YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures
    ) -> tuple[CompressorTrainCommonShaftMultipleStreamsAndPressures, list[FluidFactoryInterface | None]]:
        stream_references = {stream.name for stream in model.streams}
        stream_to_stage_map: dict[str, int] = {}
        for stage_index, stage_config in enumerate(model.stages):
            for stream_reference in stage_config.stream or []:
                if stream_reference in stream_references:
                    stream_to_stage_map.setdefault(stream_reference, stage_index)

        stages = [
            self._create_compressor_train_stage(
                number_of_mixer_ports_this_stage=(
                    sum(
                        1
                        for stream_name in (stage_config.stream or [])
                        for s in model.streams
                        if s.name == stream_name and isinstance(s, YamlMultipleStreamsStreamIngoing)
                    )
                    - (1 if stage_index == 0 else 0)
                ),
                number_of_splitter_ports_this_stage=sum(
                    1
                    for stream_name in (stage_config.stream or [])
                    for s in model.streams
                    if s.name == stream_name and isinstance(s, YamlMultipleStreamsStreamOutgoing)
                ),
                compressor_chart_reference=stage_config.compressor_chart,
                inlet_temperature_kelvin=convert_temperature_to_kelvin(
                    [stage_config.inlet_temperature], input_unit=Unit.CELSIUS
                )[0],
                pressure_drop_ahead_of_stage=stage_config.pressure_drop_ahead_of_stage,
                remove_liquid_after_cooling=True,
                control_margin=convert_control_margin_to_fraction(
                    stage_config.control_margin, YAML_UNIT_MAPPING[stage_config.control_margin_unit]
                ),
                interstage_pressure_control=(
                    InterstagePressureControl(
                        upstream_pressure_control=map_yaml_to_fixed_speed_pressure_control(
                            stage_config.interstage_control_pressure.upstream_pressure_control
                        ),
                        downstream_pressure_control=map_yaml_to_fixed_speed_pressure_control(
                            stage_config.interstage_control_pressure.downstream_pressure_control
                        ),
                    )
                    if stage_config.interstage_control_pressure
                    else None
                ),
            )
            for stage_index, stage_config in enumerate(model.stages)
            if not any(
                stream_to_stage_map.setdefault(stream_reference, stage_index) != stage_index
                for stream_reference in (stage_config.stream or [])
                if stream_reference not in stream_references or stream_reference in stream_to_stage_map
            )
        ]

        streams = [
            FluidStreamObjectForMultipleStreams(
                name=stream_config.name,
                fluid_model=(
                    self._get_fluid_model(stream_config.fluid_model)
                    if isinstance(stream_config, YamlMultipleStreamsStreamIngoing)
                    else None
                ),
                is_inlet_stream=isinstance(stream_config, YamlMultipleStreamsStreamIngoing),
                connected_to_stage_no=stream_to_stage_map[stream_config.name],
            )
            for stream_config in model.streams
        ]

        fluid_factory_streams = [
            _create_fluid_factory(stream.fluid_model) if stream.is_inlet_stream else None for stream in streams
        ]

        if not any(fluid_factory_streams):
            raise DomainValidationException("An inlet stream is required for this model")

        interstage_pressures = {i for i, stage in enumerate(stages) if stage.has_control_pressure}
        stage_number_interstage_pressure = interstage_pressures.pop() if interstage_pressures else None

        compressor_model = CompressorTrainCommonShaftMultipleStreamsAndPressures(
            streams=streams,
            energy_usage_adjustment_constant=model.power_adjustment_constant,
            energy_usage_adjustment_factor=model.power_adjustment_factor,
            stages=stages,
            shaft=VariableSpeedShaft(),
            calculate_max_rate=False,
            maximum_power=model.maximum_power,
            pressure_control=_pressure_control_mapper(model),
            stage_number_interstage_pressure=stage_number_interstage_pressure,
        )
        return compressor_model, fluid_factory_streams

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

    def create_compressor_model(
        self,
        reference: str,
        operational_data: CompressorOperationalTimeSeries | None = None,
    ) -> tuple[
        CompressorTrainModel | CompressorModelSampled | CompressorWithTurbineModel, FluidFactoryInterface | None
    ]:
        model = self._reference_service.get_compressor_model(reference)
        try:
            if isinstance(model, YamlSimplifiedVariableSpeedCompressorTrain):
                return self._create_simplified_model_with_prepared_stages(
                    model=model,
                    operational_data=operational_data,
                )
            elif isinstance(model, YamlVariableSpeedCompressorTrain):
                return self._create_variable_speed_compressor_train(model)
            elif isinstance(model, YamlSingleSpeedCompressorTrain):
                return self._create_single_speed_compressor_train(model)
            elif isinstance(model, YamlCompressorWithTurbine):
                return self._create_compressor_with_turbine(model, operational_data=operational_data)
            elif isinstance(model, YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures):
                return self._create_variable_speed_compressor_train_multiple_streams_and_pressures(model)
            elif isinstance(model, YamlCompressorTabularModel):
                return self._create_compressor_sampled(model, reference), None
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
        mapping_context: MappingContext,
        consumer_id: uuid.UUID,
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
        self._mapping_context = mapping_context
        self._process_service = mapping_context._process_service
        self._consumer_id = consumer_id
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
        self,
        model: YamlEnergyUsageModelPump,
        consumes: ConsumptionType,
        period: Period,
        consumer_id: uuid.UUID,
    ) -> PumpModel:
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

        evaluation_input = PumpEvaluationInput(
            rate=rate_standard_m3_day,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
            fluid_density=fluid_density,
            power_loss_factor=power_loss_factor,
        )
        # Register the pump model and its evaluation input in the mapping context
        model_id = uuid.uuid4()
        component = PumpProcessSystemComponent(id=model_id, name=model.energy_function, type=model.type)
        self._process_service.register_pump_process_system(ecalc_component=component, pump_process_system=pump_model)
        self._process_service.register_evaluation_input(ecalc_component=component, evaluation_input=evaluation_input)
        self._process_service.map_model_to_consumer(consumer_id=consumer_id, period=period, ecalc_component=component)

        return pump_model

    def _map_multiple_streams_compressor(
        self,
        model: YamlEnergyUsageModelCompressorTrainMultipleStreams,
        consumes: ConsumptionType,
        period: Period,
        consumer_id: uuid.UUID,
    ):
        process_system_id = uuid.uuid4()
        compressor_train_model, fluid_factories = self._compressor_model_mapper.create_compressor_model(
            model.compressor_train_model
        )
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

        assert fluid_factories is not None
        evaluation_input = CompressorEvaluationInput(
            rate=rates_per_stream,
            fluid_factory=fluid_factories,
            power_loss_factor=power_loss_factor,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
            intermediate_pressure=interstage_control_pressure,
        )

        # Register the compressor model and its evaluation input in the mapping context
        component = CompressorProcessSystemComponent(
            id=process_system_id, name=model.compressor_train_model, type=model.type
        )
        assert isinstance(compressor_train_model, CompressorTrainModel | CompressorWithTurbineModel)
        self._process_service.register_compressor_process_system(
            ecalc_component=component,
            compressor_process_system=compressor_train_model,
        )
        self._process_service.register_evaluation_input(ecalc_component=component, evaluation_input=evaluation_input)
        self._process_service.map_model_to_consumer(consumer_id=consumer_id, period=period, ecalc_component=component)

        return compressor_train_model

    def _map_compressor(
        self,
        model: YamlEnergyUsageModelCompressor,
        consumes: ConsumptionType,
        period: Period,
        consumer_id: uuid.UUID,
    ):
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
        operational_data = CompressorOperationalTimeSeries.from_time_series(
            rates=stream_day_rate,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
        )

        compressor_model, fluid_factory = self._compressor_model_mapper.create_compressor_model(
            model.energy_function, operational_data=operational_data
        )

        consumption_type = compressor_model.get_consumption_type()
        if consumes != consumption_type:
            raise InvalidConsumptionType(actual=consumption_type, expected=consumes)

        if suction_pressure is not None and discharge_pressure is not None:
            validate_increasing_pressure(
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )

        model_id = uuid.uuid4()
        # Register the compressor model and its evaluation input in the process service
        # - If it is a sampled model, or a turbine model wrapping a sampled model, treat as non-process.
        # - Otherwise, treat as a process model.
        if _is_sampled_compressor(compressor_model):
            evaluation_input = CompressorSampledEvaluationInput(
                rate=stream_day_rate,
                power_loss_factor=power_loss_factor,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )
            component = CompressorSampledComponent(id=model_id, name=model.energy_function, type=model.type)
            assert isinstance(compressor_model, CompressorModelSampled | CompressorWithTurbineModel)
            self._process_service.register_compressor_sampled(
                ecalc_component=component, compressor_sampled=compressor_model
            )
        else:
            assert suction_pressure is not None and discharge_pressure is not None and fluid_factory is not None
            evaluation_input = CompressorEvaluationInput(
                rate=stream_day_rate,
                fluid_factory=fluid_factory,
                power_loss_factor=power_loss_factor,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
                intermediate_pressure=None,
            )
            component = CompressorProcessSystemComponent(id=model_id, name=model.energy_function, type=model.type)
            assert isinstance(evaluation_input, CompressorEvaluationInput)
            self._process_service.register_compressor_process_system(
                ecalc_component=component, compressor_process_system=compressor_model
            )

        self._process_service.register_evaluation_input(ecalc_component=component, evaluation_input=evaluation_input)
        # Ensure that the process system ID is associated with the correct consumer ID and period
        self._process_service.map_model_to_consumer(consumer_id=consumer_id, period=period, ecalc_component=component)

        return compressor_model

    def _map_compressor_system(
        self, model: YamlEnergyUsageModelCompressorSystem, consumes: ConsumptionType, period: Period
    ) -> ConsumerSystemConsumerFunction:
        regularity, expression_evaluator = self._period_subsets[period]

        # Process operational settings - needed for return value and for simplified model envelope extraction
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

            core_setting = ConsumerSystemOperationalSettingExpressions(
                rates=rates,
                discharge_pressures=discharge_pressures,  # type: ignore[arg-type]
                suction_pressures=suction_pressures,  # type: ignore[arg-type]
                cross_overs=operational_setting.crossover,
            )
            operational_settings.append(core_setting)

        compressors: list[SystemComponent] = []
        compressor_consumption_types: set[ConsumptionType] = set()

        for compressor in model.compressors:
            model_ref = compressor.compressor_model
            compressor_train, fluid_factory = self._compressor_model_mapper.create_compressor_model(model_ref)

            compressors.append(
                ConsumerSystemComponent(
                    name=compressor.name,
                    fluid_factory=fluid_factory,
                    facility_model=compressor_train,
                )
            )
            compressor_consumption_types.add(compressor_train.get_consumption_type())

        # Validate consumption types and create result
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

        power_loss_factor_expression = TimeSeriesExpression(
            expression=model.power_loss_factor, expression_evaluator=expression_evaluator
        )
        power_loss_factor = ExpressionTimeSeriesPowerLossFactor(time_series_expression=power_loss_factor_expression)

        return ConsumerSystemConsumerFunction(
            consumer_components=compressors,
            operational_settings_expressions=operational_settings,
            power_loss_factor=power_loss_factor,
        )

    def _map_pump_system(
        self, model: YamlEnergyUsageModelPumpSystem, consumes: ConsumptionType, period: Period
    ) -> ConsumerSystemConsumerFunction:
        regularity, expression_evaluator = self._period_subsets[period]
        if consumes != ConsumptionType.ELECTRICITY:
            raise InvalidConsumptionType(actual=ConsumptionType.ELECTRICITY, expected=consumes)

        pumps: list[SystemComponent] = []
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
                ConsumerSystemOperationalSettingExpressions(
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

        return ConsumerSystemConsumerFunction(
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
                    mapped_model = self._map_compressor(
                        model, consumes=consumes, period=period, consumer_id=self._consumer_id
                    )
                elif isinstance(model, YamlEnergyUsageModelPump):
                    mapped_model = self._map_pump(
                        model, consumes=consumes, period=period, consumer_id=self._consumer_id
                    )
                elif isinstance(model, YamlEnergyUsageModelCompressorSystem):
                    mapped_model = self._map_compressor_system(model, consumes=consumes, period=period)
                elif isinstance(model, YamlEnergyUsageModelPumpSystem):
                    mapped_model = self._map_pump_system(model, consumes=consumes, period=period)
                elif isinstance(model, YamlEnergyUsageModelTabulated):
                    mapped_model = self._map_tabular(model=model, consumes=consumes, period=period)
                elif isinstance(model, YamlEnergyUsageModelCompressorTrainMultipleStreams):
                    mapped_model = self._map_multiple_streams_compressor(
                        model, consumes=consumes, period=period, consumer_id=self._consumer_id
                    )
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
