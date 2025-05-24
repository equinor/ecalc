from typing import Any, cast

from pydantic import ValidationError

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.fluid import MultipleStreamsAndPressureStream
from libecalc.common.serializable_chart import ChartCurveDTO, SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.common.units import Unit
from libecalc.domain.process.chart.compressor.compressor_chart_dto import CompressorChart
from libecalc.domain.process.chart.generic import GenericChartFromDesignPoint, GenericChartFromInput
from libecalc.domain.process.compressor.dto import (
    CompressorStage,
    CompressorTrainSimplifiedWithKnownStages,
    CompressorTrainSimplifiedWithUnknownStages,
    CompressorWithTurbine,
    InterstagePressureControl,
    SingleSpeedCompressorTrain,
    VariableSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.domain.process.dto import (
    EnergyModel,
    Turbine,
)
from libecalc.domain.resource import Resources
from libecalc.presentation.yaml.mappers.fluid_mapper import fluid_model_mapper
from libecalc.presentation.yaml.mappers.utils import (
    YAML_UNIT_MAPPING,
    chart_curves_as_resource_to_dto_format,
    convert_control_margin_to_fraction,
    convert_efficiency_to_fraction,
    convert_head_to_joule_per_kg,
    convert_rate_to_am3_per_hour,
    convert_temperature_to_kelvin,
    get_single_speed_chart_data,
    resolve_model_reference,
)
from libecalc.presentation.yaml.validation_errors import (
    DataValidationError,
    DtoValidationError,
    ValidationValueError,
)
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.models import (
    YamlCompressorChart,
    YamlCompressorWithTurbine,
    YamlConsumerModel,
    YamlTurbine,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import (
    YamlCurve,
    YamlGenericFromDesignPointChart,
    YamlGenericFromInputChart,
    YamlSingleSpeedChart,
    YamlVariableSpeedChart,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import (
    YamlCompressorStageMultipleStreams,
    YamlUnknownCompressorStages,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_trains import (
    YamlMultipleStreamsStream,
    YamlSimplifiedVariableSpeedCompressorTrain,
    YamlSingleSpeedCompressorTrain,
    YamlVariableSpeedCompressorTrain,
    YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlPressureControl
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile


def _compressor_chart_mapper(
    model_config: YamlCompressorChart, input_models: dict[str, Any], resources: Resources
) -> CompressorChart:
    chart_type = model_config.chart_type
    mapper = _compressor_chart_map.get(chart_type)
    if mapper is None:
        raise ValueError(f"Unknown chart type {chart_type}")
    return mapper(model_config=model_config, resources=resources)


def _pressure_control_mapper(
    model_config: (
        YamlVariableSpeedCompressorTrain
        | YamlSingleSpeedCompressorTrain
        | YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures
    ),
) -> FixedSpeedPressureControl:
    return FixedSpeedPressureControl(model_config.pressure_control.value)


def _single_speed_compressor_chart_mapper(
    model_config: YamlSingleSpeedChart, resources: Resources
) -> SingleSpeedChartDTO:
    curve_config = model_config.curve

    if isinstance(curve_config, YamlFile):
        resource_name = curve_config.file
        resource = resources.get(resource_name)

        chart_data = get_single_speed_chart_data(resource=resource)
        curve_data = {
            "speed": chart_data.speed,
            "rate": chart_data.rate,
            "head": chart_data.head,
            "efficiency": chart_data.efficiency,
        }
    else:
        curve_config = cast(YamlCurve, curve_config)
        curve_data = {
            # Default to speed = 1 unless specified. This does not affect any calculations
            # but ensures we always have speed to handle charts in a generic way.
            "speed": curve_config.speed,
            "rate": curve_config.rate,
            "head": curve_config.head,
            "efficiency": curve_config.efficiency,
        }

    return SingleSpeedChartDTO(
        speed_rpm=curve_data["speed"],
        rate_actual_m3_hour=convert_rate_to_am3_per_hour(
            rate_values=curve_data["rate"], input_unit=YAML_UNIT_MAPPING[model_config.units.rate]
        ),
        polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(
            head_values=curve_data["head"], input_unit=YAML_UNIT_MAPPING[model_config.units.head]
        ),
        efficiency_fraction=convert_efficiency_to_fraction(
            efficiency_values=curve_data["efficiency"],
            input_unit=YAML_UNIT_MAPPING[model_config.units.efficiency],
        ),
    )


def _variable_speed_compressor_chart_mapper(
    model_config: YamlVariableSpeedChart, resources: Resources
) -> VariableSpeedChartDTO:
    curve_config = model_config.curves

    if isinstance(curve_config, YamlFile):
        resource_name = curve_config.file
        resource = resources.get(resource_name)
        curves_data = chart_curves_as_resource_to_dto_format(resource=resource)
    else:
        curve_config = cast(list[YamlCurve], curve_config)
        curves_data = [
            {
                "speed": curve.speed,
                "rate": curve.rate,
                "head": curve.head,
                "efficiency": curve.efficiency,
            }
            for curve in curve_config
        ]

    units = model_config.units

    curves: list[ChartCurveDTO] = [
        ChartCurveDTO(
            speed_rpm=curve["speed"],
            rate_actual_m3_hour=convert_rate_to_am3_per_hour(
                rate_values=curve["rate"],
                input_unit=YAML_UNIT_MAPPING[units.rate],
            ),
            polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(
                head_values=curve["head"], input_unit=YAML_UNIT_MAPPING[units.head]
            ),
            efficiency_fraction=convert_efficiency_to_fraction(
                efficiency_values=curve["efficiency"],
                input_unit=YAML_UNIT_MAPPING[units.efficiency],
            ),
        )
        for curve in curves_data
    ]

    return VariableSpeedChartDTO(curves=curves)


def _generic_from_input_compressor_chart_mapper(
    model_config: YamlGenericFromInputChart, resources: Resources
) -> GenericChartFromInput:
    units = model_config.units

    polytropic_efficiency = model_config.polytropic_efficiency
    polytropic_efficiency_fraction = convert_efficiency_to_fraction(
        efficiency_values=[polytropic_efficiency],
        input_unit=YAML_UNIT_MAPPING[units.efficiency],
    )[0]

    return GenericChartFromInput(polytropic_efficiency_fraction=polytropic_efficiency_fraction)


def _generic_from_design_point_compressor_chart_mapper(
    model_config: YamlGenericFromDesignPointChart, resources: Resources
) -> GenericChartFromDesignPoint:
    design_rate = model_config.design_rate
    design_polytropic_head = model_config.design_head
    polytropic_efficiency = model_config.polytropic_efficiency

    units = model_config.units
    design_rate_actual_m3_per_hour = convert_rate_to_am3_per_hour(
        rate_values=[design_rate], input_unit=YAML_UNIT_MAPPING[units.rate]
    )[0]
    design_polytropic_head_joule_per_kg = convert_head_to_joule_per_kg(
        head_values=[design_polytropic_head], input_unit=YAML_UNIT_MAPPING[units.head]
    )[0]
    polytropic_efficiency_fraction = convert_efficiency_to_fraction(
        efficiency_values=[polytropic_efficiency],
        input_unit=YAML_UNIT_MAPPING[units.efficiency],
    )[0]

    return GenericChartFromDesignPoint(
        polytropic_efficiency_fraction=polytropic_efficiency_fraction,
        design_rate_actual_m3_per_hour=design_rate_actual_m3_per_hour,
        design_polytropic_head_J_per_kg=design_polytropic_head_joule_per_kg,
    )


_compressor_chart_map = {
    EcalcYamlKeywords.consumer_chart_type_variable_speed: _variable_speed_compressor_chart_mapper,
    EcalcYamlKeywords.consumer_chart_type_generic_from_input: _generic_from_input_compressor_chart_mapper,
    EcalcYamlKeywords.consumer_chart_type_generic_from_design_point: _generic_from_design_point_compressor_chart_mapper,
    EcalcYamlKeywords.consumer_chart_type_single_speed: _single_speed_compressor_chart_mapper,
}


def _resolve_and_validate_chart(compressor_chart_reference, input_models: dict[str, Any]) -> CompressorChart:
    compressor_chart = resolve_model_reference(
        value=compressor_chart_reference,
        references=input_models,
    )
    if compressor_chart is None:
        raise ValueError(f"Compressor chart {compressor_chart_reference} not found in input models")
    return compressor_chart


def _replace_compressor_chart_with_reference(stage_spec, input_models) -> dict:
    reference = stage_spec.get(EcalcYamlKeywords.models_type_compressor_train_compressor_chart)
    stage_with_resolved_reference = dict(stage_spec)
    stage_with_resolved_reference[EcalcYamlKeywords.models_type_compressor_train_compressor_chart] = input_models.get(
        reference
    )
    return stage_with_resolved_reference


def _variable_speed_compressor_train_multiple_streams_and_pressures_stream_mapper(
    stream_config: YamlMultipleStreamsStream,
    input_models: dict[str, Any],
) -> MultipleStreamsAndPressureStream:
    reference_name = stream_config.name
    stream_type = stream_config.type
    fluid_model_reference = stream_config.fluid_model
    if fluid_model_reference is not None:
        fluid_model = resolve_model_reference(value=fluid_model_reference, references=input_models)
        return MultipleStreamsAndPressureStream(
            name=reference_name,
            fluid_model=fluid_model,
            typ=stream_type,
        )
    else:
        return MultipleStreamsAndPressureStream(
            name=reference_name,
            typ=stream_type,
        )


def _variable_speed_compressor_train_multiple_streams_and_pressures_stage_mapper(
    stage_config: YamlCompressorStageMultipleStreams,
    stream_references: list[str],
    input_models: dict[str, Any],
) -> CompressorStage:
    compressor_chart_reference = stage_config.compressor_chart
    compressor_chart = resolve_model_reference(value=compressor_chart_reference, references=input_models)
    inlet_temperature_kelvin = convert_temperature_to_kelvin(
        [stage_config.inlet_temperature],
        input_unit=Unit.CELSIUS,
    )[0]
    pressure_drop_before_stage = stage_config.pressure_drop_ahead_of_stage
    control_margin = stage_config.control_margin
    control_margin_unit = stage_config.control_margin_unit
    control_margin_fraction = convert_control_margin_to_fraction(
        control_margin,
        YAML_UNIT_MAPPING[control_margin_unit],
    )

    stream_references_this_stage = (
        stage_config.stream
    )  # TODO: seems to be a bug if stream is a single string? Should we remove that option?
    if stream_references_this_stage is not None:
        stream_reference_not_present = [
            stream_ref for stream_ref in stream_references_this_stage if stream_ref not in stream_references
        ]
        if any(stream_reference_not_present):
            raise ValueError(f"Streams {', '.join(stream_reference_not_present)} not properly defined")

    interstage_pressure_control_config = stage_config.interstage_control_pressure
    interstage_pressure_control = None
    if interstage_pressure_control_config is not None:
        interstage_pressure_control = InterstagePressureControl(
            upstream_pressure_control=map_yaml_to_fixed_speed_pressure_control(
                interstage_pressure_control_config.upstream_pressure_control
            ),
            downstream_pressure_control=map_yaml_to_fixed_speed_pressure_control(
                interstage_pressure_control_config.upstream_pressure_control
            ),
        )

    return CompressorStage(
        compressor_chart=compressor_chart,
        inlet_temperature_kelvin=inlet_temperature_kelvin,
        pressure_drop_before_stage=pressure_drop_before_stage,
        remove_liquid_after_cooling=True,
        control_margin=control_margin_fraction,
        stream_reference=stream_references_this_stage,
        interstage_pressure_control=interstage_pressure_control,
    )


def map_yaml_to_fixed_speed_pressure_control(yaml_control: YamlPressureControl) -> FixedSpeedPressureControl:
    mapping = {
        YamlPressureControl.UPSTREAM_CHOKE: FixedSpeedPressureControl.UPSTREAM_CHOKE,
        YamlPressureControl.DOWNSTREAM_CHOKE: FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        YamlPressureControl.INDIVIDUAL_ASV_PRESSURE: FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
        YamlPressureControl.INDIVIDUAL_ASV_RATE: FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE,
        YamlPressureControl.COMMON_ASV: FixedSpeedPressureControl.COMMON_ASV,
    }
    return mapping[yaml_control]


def _variable_speed_compressor_train_multiple_streams_and_pressures_mapper(
    model_config: YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures,
    input_models: dict[str, Any],
    resources: Resources,
) -> VariableSpeedCompressorTrainMultipleStreamsAndPressures:
    streams_config = model_config.streams
    streams = [
        _variable_speed_compressor_train_multiple_streams_and_pressures_stream_mapper(
            stream_config, input_models=input_models
        )
        for stream_config in streams_config
    ]
    stages_config = model_config.stages
    stages = [
        _variable_speed_compressor_train_multiple_streams_and_pressures_stage_mapper(
            stage_config, stream_references=[stream.name for stream in streams], input_models=input_models
        )
        for stage_config in stages_config
    ]
    pressure_control = _pressure_control_mapper(model_config)

    return VariableSpeedCompressorTrainMultipleStreamsAndPressures(
        streams=streams,
        stages=stages,
        energy_usage_adjustment_constant=model_config.power_adjustment_constant,
        energy_usage_adjustment_factor=model_config.power_adjustment_factor,
        calculate_max_rate=False,  # TODO: Not supported?
        pressure_control=pressure_control,
        maximum_power=model_config.maximum_power,
    )


SUPPORTED_PRESSURE_CONTROLS_SINGLE_SPEED_COMPRESSOR_TRAIN = [
    FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE,
    FixedSpeedPressureControl.UPSTREAM_CHOKE,
    FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
    FixedSpeedPressureControl.COMMON_ASV,
    FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
    None,
]


def _single_speed_compressor_train_mapper(
    model_config: YamlSingleSpeedCompressorTrain,
    input_models: dict[str, Any],
    resources: Resources,
) -> SingleSpeedCompressorTrain:
    fluid_model_reference = model_config.fluid_model
    fluid_model = input_models.get(fluid_model_reference)
    if fluid_model is None:
        raise DataValidationError(
            data=model_config.model_dump(), message=f"Fluid model reference {fluid_model_reference} not found."
        )

    train_spec = model_config.compressor_train

    stages: list[CompressorStage] = [
        CompressorStage(
            compressor_chart=input_models.get(stage.compressor_chart),
            inlet_temperature_kelvin=convert_temperature_to_kelvin(
                [stage.inlet_temperature],
                input_unit=Unit.CELSIUS,
            )[0],
            remove_liquid_after_cooling=True,
            pressure_drop_before_stage=stage.pressure_drop_ahead_of_stage,
            control_margin=convert_control_margin_to_fraction(
                stage.control_margin,
                YAML_UNIT_MAPPING[stage.control_margin_unit],
            ),
        )
        for stage in train_spec.stages
    ]
    pressure_control = _pressure_control_mapper(model_config)
    maximum_discharge_pressure = model_config.maximum_discharge_pressure
    if maximum_discharge_pressure and pressure_control != FixedSpeedPressureControl.DOWNSTREAM_CHOKE:
        raise ValueError(
            f"Setting maximum discharge pressure for single speed compressor train is currently"
            f"only supported with {FixedSpeedPressureControl.DOWNSTREAM_CHOKE} pressure control"
            f"option. Pressure control option is {pressure_control}"
        )

    return SingleSpeedCompressorTrain(
        fluid_model=fluid_model,
        stages=stages,
        pressure_control=pressure_control,
        maximum_discharge_pressure=maximum_discharge_pressure,
        energy_usage_adjustment_constant=model_config.power_adjustment_constant,
        energy_usage_adjustment_factor=model_config.power_adjustment_factor,
        calculate_max_rate=model_config.calculate_max_rate,
        maximum_power=model_config.maximum_power,
    )


def _variable_speed_compressor_train_mapper(
    model_config: YamlVariableSpeedCompressorTrain,
    input_models: dict[str, Any],
    resources: Resources,
) -> VariableSpeedCompressorTrain:
    fluid_model_reference: str = model_config.fluid_model
    fluid_model = input_models.get(fluid_model_reference)
    if fluid_model is None:
        raise DataValidationError(
            data=model_config.model_dump(), message=f"Fluid model reference {fluid_model_reference} not found."
        )

    train_spec = model_config.compressor_train

    # The stages are pre defined, known
    stages_data = train_spec.stages

    stages: list[CompressorStage] = []
    for stage in stages_data:
        control_margin = convert_control_margin_to_fraction(
            stage.control_margin,
            YAML_UNIT_MAPPING[stage.control_margin_unit],
        )

        compressor_chart: VariableSpeedChartDTO = input_models.get(stage.compressor_chart)

        stages.append(
            CompressorStage(
                compressor_chart=compressor_chart,
                inlet_temperature_kelvin=convert_temperature_to_kelvin(
                    [stage.inlet_temperature],
                    input_unit=Unit.CELSIUS,
                )[0],
                remove_liquid_after_cooling=True,
                pressure_drop_before_stage=stage.pressure_drop_ahead_of_stage,
                control_margin=control_margin,
            )
        )
    pressure_control = _pressure_control_mapper(model_config)

    return VariableSpeedCompressorTrain(
        fluid_model=fluid_model,
        stages=stages,
        energy_usage_adjustment_constant=model_config.power_adjustment_constant,
        energy_usage_adjustment_factor=model_config.power_adjustment_factor,
        calculate_max_rate=model_config.calculate_max_rate,
        pressure_control=pressure_control,
        maximum_power=model_config.maximum_power,
    )


def _simplified_variable_speed_compressor_train_mapper(
    model_config: YamlSimplifiedVariableSpeedCompressorTrain,
    input_models: dict[str, Any],
    resources: Resources,
) -> CompressorTrainSimplifiedWithKnownStages | CompressorTrainSimplifiedWithUnknownStages:
    fluid_model_reference: str = model_config.fluid_model
    fluid_model = input_models.get(fluid_model_reference)
    if fluid_model is None:
        raise ValueError(f"Fluid model reference {fluid_model_reference} not found.")

    train_spec = model_config.compressor_train

    if not isinstance(train_spec, YamlUnknownCompressorStages):
        # The stages are pre defined, known
        stages = train_spec.stages
        return CompressorTrainSimplifiedWithKnownStages(
            fluid_model=fluid_model,
            stages=[
                CompressorStage(
                    inlet_temperature_kelvin=convert_temperature_to_kelvin(
                        [stage.inlet_temperature],
                        input_unit=Unit.CELSIUS,
                    )[0],
                    compressor_chart=input_models.get(stage.compressor_chart),
                    pressure_drop_before_stage=0,
                    control_margin=0,
                    remove_liquid_after_cooling=True,
                )
                for stage in stages
            ],
            energy_usage_adjustment_constant=model_config.power_adjustment_constant,
            energy_usage_adjustment_factor=model_config.power_adjustment_factor,
            calculate_max_rate=model_config.calculate_max_rate,
            maximum_power=model_config.maximum_power,
        )
    else:
        # The stages are unknown, not defined
        compressor_chart_reference = train_spec.compressor_chart
        return CompressorTrainSimplifiedWithUnknownStages(
            fluid_model=fluid_model,
            stage=CompressorStage(
                compressor_chart=input_models.get(compressor_chart_reference),
                inlet_temperature_kelvin=convert_temperature_to_kelvin(
                    [train_spec.inlet_temperature],
                    input_unit=Unit.CELSIUS,
                )[0],
                pressure_drop_before_stage=0,
                remove_liquid_after_cooling=True,
            ),
            energy_usage_adjustment_constant=model_config.power_adjustment_constant,
            energy_usage_adjustment_factor=model_config.power_adjustment_factor,
            calculate_max_rate=model_config.calculate_max_rate,
            maximum_pressure_ratio_per_stage=train_spec.maximum_pressure_ratio_per_stage,
            maximum_power=model_config.maximum_power,
        )


def _turbine_mapper(model_config: YamlTurbine, input_models: dict[str, Any], resources: Resources) -> Turbine:
    return Turbine(
        lower_heating_value=model_config.lower_heating_value,
        turbine_loads=model_config.turbine_loads,
        turbine_efficiency_fractions=model_config.turbine_efficiencies,
        energy_usage_adjustment_constant=model_config.power_adjustment_constant,
        energy_usage_adjustment_factor=model_config.power_adjustment_factor,
    )


def _compressor_with_turbine_mapper(
    model_config: YamlCompressorWithTurbine, input_models: dict[str, Any], resources: Resources
) -> CompressorWithTurbine:
    compressor_train_model = resolve_model_reference(
        value=model_config.compressor_model,
        references=input_models,
    )
    turbine_model = resolve_model_reference(
        value=model_config.turbine_model,
        references=input_models,
    )

    return CompressorWithTurbine(
        compressor_train=compressor_train_model,
        turbine=turbine_model,
        energy_usage_adjustment_constant=model_config.power_adjustment_constant,
        energy_usage_adjustment_factor=model_config.power_adjustment_factor,
    )


_model_mapper = {
    EcalcYamlKeywords.models_type_fluid: fluid_model_mapper,
    EcalcYamlKeywords.models_type_compressor_chart: _compressor_chart_mapper,
    EcalcYamlKeywords.models_type_compressor_train_simplified: _simplified_variable_speed_compressor_train_mapper,
    EcalcYamlKeywords.models_type_compressor_train_variable_speed: _variable_speed_compressor_train_mapper,
    EcalcYamlKeywords.models_type_compressor_train_single_speed: _single_speed_compressor_train_mapper,
    EcalcYamlKeywords.models_type_turbine: _turbine_mapper,
    EcalcYamlKeywords.models_type_compressor_with_turbine: _compressor_with_turbine_mapper,
    EcalcYamlKeywords.models_type_compressor_train_variable_speed_multiple_streams_and_pressures: _variable_speed_compressor_train_multiple_streams_and_pressures_mapper,
}


class ModelMapper:
    def __init__(self, resources: Resources):
        self.__resources = resources

    @staticmethod
    def create_model(model: YamlConsumerModel, input_models: dict[str, Any], resources: Resources):
        model_creator = _model_mapper.get(model.type)
        if model_creator is None:
            raise ValueError(f"Unknown model type: {model.name}")
        return model_creator(model_config=model, input_models=input_models, resources=resources)

    def from_yaml_to_dto(self, model_config: YamlConsumerModel, input_models: dict[str, Any]) -> EnergyModel:
        try:
            model_data = ModelMapper.create_model(
                model=model_config, input_models=input_models, resources=self.__resources
            )
            return model_data
        except ValidationError as ve:
            raise DtoValidationError(data=model_config.model_dump(), validation_error=ve) from ve
        except ValidationValueError as vve:
            raise DataValidationError(
                data=model_config.model_dump(),
                message=str(vve),
            ) from vve
