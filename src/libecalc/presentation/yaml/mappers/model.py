from typing import Any, Dict, List, Union

from pydantic import ValidationError

from libecalc import dto
from libecalc.common.units import Unit
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
    get_units_from_chart_config,
    resolve_reference,
)
from libecalc.presentation.yaml.validation_errors import (
    DataValidationError,
    DtoValidationError,
    ValidationValueError,
)
from libecalc.presentation.yaml.yaml_entities import Resource, Resources
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


def _compressor_chart_mapper(
    model_config: Dict, input_models: Dict[str, Any], resources: Resources
) -> dto.CompressorChart:
    chart_type = model_config.get(EcalcYamlKeywords.consumer_chart_type)
    mapper = _compressor_chart_map.get(chart_type)
    if mapper is None:
        raise ValueError(f"Unknown chart type {chart_type}")
    return mapper(model_config=model_config, resources=resources)


def _pressure_control_mapper(model_config: Dict) -> dto.types.FixedSpeedPressureControl:
    pressure_control_data = model_config.get(
        EcalcYamlKeywords.models_type_compressor_train_pressure_control,
        EcalcYamlKeywords.models_type_compressor_train_pressure_control_downstream_choke,
    )
    if pressure_control_data == EcalcYamlKeywords.models_type_compressor_train_pressure_control_none:
        pressure_control = None
    else:
        pressure_control = dto.types.FixedSpeedPressureControl(pressure_control_data)
    if pressure_control not in SUPPORTED_PRESSURE_CONTROLS_SINGLE_SPEED_COMPRESSOR_TRAIN:
        raise ValueError(
            f"Pressure control {pressure_control} not supported, should be one of {', '.join(SUPPORTED_PRESSURE_CONTROLS_SINGLE_SPEED_COMPRESSOR_TRAIN)}"
        )
    return pressure_control


def _get_curve_data_from_resource(resource: Resource, speed: float = 0.0):
    rate_index = resource.headers.index(EcalcYamlKeywords.consumer_chart_rate)
    head_index = resource.headers.index(EcalcYamlKeywords.consumer_chart_head)
    efficiency_index = resource.headers.index(EcalcYamlKeywords.consumer_chart_efficiency)
    return {
        "speed": speed,
        "rate": resource.data[rate_index],
        "head": resource.data[head_index],
        "efficiency": resource.data[efficiency_index],
    }


def _single_speed_compressor_chart_mapper(model_config: Dict, resources: Resources) -> dto.SingleSpeedChart:
    units = get_units_from_chart_config(chart_config=model_config)
    curve_config = model_config.get(EcalcYamlKeywords.consumer_chart_curve)
    name = model_config.get(EcalcYamlKeywords.name)

    # Check if user has used CURVES (reserved for variable speed compressors)
    # instead of CURVE (should be used for single speed compressors),
    # and give clear error message.
    if EcalcYamlKeywords.consumer_chart_curves in model_config:
        raise DataValidationError(
            data=model_config,
            message=f"Compressor model {name}:\n"
            f"The keyword {EcalcYamlKeywords.consumer_chart_curves} should only be used for "
            f"variable speed compressor models.\n"
            f"{name} is a single speed compressor model and should use the keyword "
            f"{EcalcYamlKeywords.consumer_chart_curve}.",
        )

    if EcalcYamlKeywords.consumer_chart_curve not in model_config:
        raise DataValidationError(
            data=model_config,
            message=f"The keyword {EcalcYamlKeywords.consumer_chart_curve} is not specified "
            f"for the compressor model {name}.\n"
            f"{EcalcYamlKeywords.consumer_chart_curve} is a required keyword for "
            f"single speed compressor models.",
        )

    if not isinstance(curve_config, dict):
        raise DataValidationError(
            data=model_config,
            message=f"Compressor model {name}:"
            f"{EcalcYamlKeywords.consumer_chart_curve}"
            f" should be an object. Type given: {type(curve_config)}.",
        )

    if EcalcYamlKeywords.file in curve_config:
        resource_name = curve_config.get(EcalcYamlKeywords.file)
        resource = resources.get(resource_name)

        chart_data = get_single_speed_chart_data(resource=resource, resource_name=resource_name)
        curve_data = {
            "speed": chart_data.speed,
            "rate": chart_data.rate,
            "head": chart_data.head,
            "efficiency": chart_data.efficiency,
        }
    else:
        curve_data = {
            # Default to speed = 1 unless specified. This does not affect any calculations
            # but ensures we always have speed to handle charts in a generic way.
            "speed": curve_config.get(EcalcYamlKeywords.consumer_chart_speed, 1),
            "rate": curve_config.get(EcalcYamlKeywords.consumer_chart_rate),
            "head": curve_config.get(EcalcYamlKeywords.consumer_chart_head),
            "efficiency": curve_config.get(EcalcYamlKeywords.consumer_chart_efficiency),
        }

    return dto.SingleSpeedChart(
        speed_rpm=curve_data["speed"],
        rate_actual_m3_hour=convert_rate_to_am3_per_hour(
            rate_values=curve_data["rate"], input_unit=units[EcalcYamlKeywords.consumer_chart_rate]
        ),
        polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(
            head_values=curve_data["head"], input_unit=units[EcalcYamlKeywords.consumer_chart_head]
        ),
        efficiency_fraction=convert_efficiency_to_fraction(
            efficiency_values=curve_data["efficiency"],
            input_unit=units[EcalcYamlKeywords.consumer_chart_efficiency],
        ),
    )


def _variable_speed_compressor_chart_mapper(model_config: Dict, resources: Resources) -> dto.VariableSpeedChart:
    units = get_units_from_chart_config(chart_config=model_config)

    curve_config = model_config.get(EcalcYamlKeywords.consumer_chart_curves)

    name = model_config.get(EcalcYamlKeywords.name)

    # Check if user has used CURVE (reserved for single speed compressors)
    # instead of CURVES (should be used for variable speed compressors),
    # and give clear error message.
    if EcalcYamlKeywords.consumer_chart_curve in model_config:
        raise DataValidationError(
            data=model_config,
            message=f"Compressor model {name}:\n"
            f"The keyword {EcalcYamlKeywords.consumer_chart_curve} should only be used for "
            f"single speed compressor models.\n"
            f"{name} is a variable speed compressor model and should use the keyword "
            f"{EcalcYamlKeywords.consumer_chart_curves}.",
        )

    if EcalcYamlKeywords.consumer_chart_curves not in model_config:
        raise DataValidationError(
            data=model_config,
            message=f"The keyword {EcalcYamlKeywords.consumer_chart_curves} is not specified "
            f"for the compressor model {name}.\n"
            f"{EcalcYamlKeywords.consumer_chart_curves} is a required keyword for "
            f"variable speed compressor models.",
        )

    if isinstance(curve_config, dict) and EcalcYamlKeywords.file in curve_config:
        resource_name = curve_config.get(EcalcYamlKeywords.file)
        resource = resources.get(resource_name)
        curves_data = chart_curves_as_resource_to_dto_format(resource=resource, resource_name=resource_name)
    else:
        curves_data = [
            {
                "speed": curve.get(EcalcYamlKeywords.consumer_chart_speed),
                "rate": curve.get(EcalcYamlKeywords.consumer_chart_rate),
                "head": curve.get(EcalcYamlKeywords.consumer_chart_head),
                "efficiency": curve.get(EcalcYamlKeywords.consumer_chart_efficiency),
            }
            for curve in model_config.get(EcalcYamlKeywords.consumer_chart_curves)
        ]

    curves: List[dto.ChartCurve] = [
        dto.ChartCurve(
            speed_rpm=curve["speed"],
            rate_actual_m3_hour=convert_rate_to_am3_per_hour(
                rate_values=curve["rate"], input_unit=units[EcalcYamlKeywords.consumer_chart_rate]
            ),
            polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(
                head_values=curve["head"], input_unit=units[EcalcYamlKeywords.consumer_chart_head]
            ),
            efficiency_fraction=convert_efficiency_to_fraction(
                efficiency_values=curve["efficiency"],
                input_unit=units[EcalcYamlKeywords.consumer_chart_efficiency],
            ),
        )
        for curve in curves_data
    ]

    return dto.VariableSpeedChart(curves=curves)


def _generic_from_input_compressor_chart_mapper(model_config: Dict, resources: Resources) -> dto.GenericChartFromInput:
    units = get_units_from_chart_config(
        chart_config=model_config, units_to_include=[EcalcYamlKeywords.consumer_chart_efficiency]
    )
    polytropic_efficiency = model_config.get(EcalcYamlKeywords.consumer_chart_polytropic_efficiency)
    polytropic_efficiency_fraction = convert_efficiency_to_fraction(
        efficiency_values=[polytropic_efficiency],
        input_unit=units[EcalcYamlKeywords.consumer_chart_efficiency],
    )[0]

    return dto.GenericChartFromInput(polytropic_efficiency_fraction=polytropic_efficiency_fraction)


def _generic_from_design_point_compressor_chart_mapper(
    model_config: Dict, resources: Resources
) -> dto.GenericChartFromDesignPoint:
    units = get_units_from_chart_config(chart_config=model_config)
    design_rate = model_config.get(EcalcYamlKeywords.consumer_chart_design_rate)
    design_polytropic_head = model_config.get(EcalcYamlKeywords.consumer_chart_design_head)
    polytropic_efficiency = model_config.get(EcalcYamlKeywords.consumer_chart_polytropic_efficiency)

    design_rate_actual_m3_per_hour = convert_rate_to_am3_per_hour(
        rate_values=[design_rate], input_unit=units[EcalcYamlKeywords.consumer_chart_rate]
    )[0]
    design_polytropic_head_joule_per_kg = convert_head_to_joule_per_kg(
        head_values=[design_polytropic_head], input_unit=units[EcalcYamlKeywords.consumer_chart_head]
    )[0]
    polytropic_efficiency_fraction = convert_efficiency_to_fraction(
        efficiency_values=[polytropic_efficiency],
        input_unit=units[EcalcYamlKeywords.consumer_chart_efficiency],
    )[0]

    return dto.GenericChartFromDesignPoint(
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


def _resolve_and_validate_chart(compressor_chart_reference, input_models: Dict[str, Any]) -> dto.CompressorChart:
    compressor_chart = resolve_reference(
        value=compressor_chart_reference,
        references=input_models,
    )
    if compressor_chart is None:
        raise ValueError(f"Compressor chart {compressor_chart_reference} not found in input models")
    return compressor_chart


def _replace_compressor_chart_with_reference(stage_spec, input_models) -> Dict:
    reference = stage_spec.get(EcalcYamlKeywords.models_type_compressor_train_compressor_chart)
    stage_with_resolved_reference = dict(stage_spec)
    stage_with_resolved_reference[EcalcYamlKeywords.models_type_compressor_train_compressor_chart] = input_models.get(
        reference
    )
    return stage_with_resolved_reference


def _variable_speed_compressor_train_multiple_streams_and_pressures_stream_mapper(
    stream_config: Dict,
    input_models: Dict[str, Any],
) -> dto.MultipleStreamsAndPressureStream:
    reference_name = stream_config.get(EcalcYamlKeywords.name)
    stream_type = stream_config.get(EcalcYamlKeywords.type)
    fluid_model_reference = stream_config.get(EcalcYamlKeywords.models_type_fluid_model)
    if fluid_model_reference is not None:
        fluid_model = resolve_reference(value=fluid_model_reference, references=input_models)
        return dto.MultipleStreamsAndPressureStream(
            name=reference_name,
            fluid_model=fluid_model,
            typ=stream_type,
        )
    else:
        return dto.MultipleStreamsAndPressureStream(
            name=reference_name,
            typ=stream_type,
        )


def _variable_speed_compressor_train_multiple_streams_and_pressures_stage_mapper(
    stage_config: Dict,
    stream_references: List[str],
    input_models: Dict[str, Any],
) -> dto.MultipleStreamsCompressorStage:
    compressor_chart_reference = stage_config.get(EcalcYamlKeywords.models_type_compressor_train_compressor_chart)
    compressor_chart = resolve_reference(value=compressor_chart_reference, references=input_models)
    inlet_temperature_kelvin = convert_temperature_to_kelvin(
        [stage_config.get(EcalcYamlKeywords.models_type_compressor_train_inlet_temperature)],
        input_unit=Unit.CELSIUS,
    )[0]
    pressure_drop_before_stage = stage_config.get(
        EcalcYamlKeywords.models_type_compressor_train_pressure_drop_ahead_of_stage, 0.0
    )
    control_margin = stage_config.get(EcalcYamlKeywords.models_type_compressor_train_stage_control_margin, 0.0)
    control_margin_unit = stage_config.get(
        EcalcYamlKeywords.models_type_compressor_train_stage_control_margin_unit,
        EcalcYamlKeywords.models_type_compressor_train_stage_control_margin_unit_percentage,
    )
    control_margin_fraction = convert_control_margin_to_fraction(
        control_margin,
        YAML_UNIT_MAPPING[control_margin_unit],
    )

    mapped_stage = {
        "compressor_chart": compressor_chart,
        "inlet_temperature_kelvin": inlet_temperature_kelvin,
        "remove_liquid_after_cooling": True,
        "pressure_drop_before_stage": pressure_drop_before_stage,
        "control_margin": control_margin_fraction,
    }
    stream_references_this_stage = stage_config.get(EcalcYamlKeywords.models_type_compressor_train_stream)
    if stream_references_this_stage is not None:
        stream_reference_not_present = [
            stream_ref for stream_ref in stream_references_this_stage if stream_ref not in stream_references
        ]
        if any(stream_reference_not_present):
            raise ValueError(f"Streams {', '.join(stream_reference_not_present)} not properly defined")
        mapped_stage.update({"stream_reference": stream_references_this_stage})
    interstage_pressure_control_config = stage_config.get(
        EcalcYamlKeywords.models_type_compressor_train_interstage_control_pressure
    )
    if interstage_pressure_control_config is not None:
        interstage_pressure_control = dto.InterstagePressureControl(
            upstream_pressure_control=interstage_pressure_control_config.get(
                EcalcYamlKeywords.models_type_compressor_train_upstream_pressure_control
            ),
            downstream_pressure_control=interstage_pressure_control_config.get(
                EcalcYamlKeywords.models_type_compressor_train_downstream_pressure_control
            ),
        )
        mapped_stage.update({"interstage_pressure_control": interstage_pressure_control})
    return dto.MultipleStreamsCompressorStage.parse_obj(mapped_stage)


def _variable_speed_compressor_train_multiple_streams_and_pressures_mapper(
    model_config: Dict,
    input_models: Dict[str, Any],
    resources: Resources,
) -> dto.VariableSpeedCompressorTrainMultipleStreamsAndPressures:
    streams_config = model_config.get(EcalcYamlKeywords.models_type_compressor_train_streams)
    streams = [
        _variable_speed_compressor_train_multiple_streams_and_pressures_stream_mapper(
            stream_config, input_models=input_models
        )
        for stream_config in streams_config
    ]
    stages_config = model_config.get(EcalcYamlKeywords.models_type_compressor_train_stages)
    stages = [
        _variable_speed_compressor_train_multiple_streams_and_pressures_stage_mapper(
            stage_config, stream_references=[stream.name for stream in streams], input_models=input_models
        )
        for stage_config in stages_config
    ]
    pressure_control = _pressure_control_mapper(model_config)

    return dto.VariableSpeedCompressorTrainMultipleStreamsAndPressures(
        streams=streams,
        stages=stages,
        energy_usage_adjustment_constant=model_config.get(EcalcYamlKeywords.models_power_adjustment_constant_mw, 0),
        energy_usage_adjustment_factor=1.0,
        calculate_max_rate=model_config.get(EcalcYamlKeywords.calculate_max_rate, False),
        pressure_control=pressure_control,
        maximum_power=model_config.get(EcalcYamlKeywords.models_maximum_power, None),
    )


SUPPORTED_PRESSURE_CONTROLS_SINGLE_SPEED_COMPRESSOR_TRAIN = [
    dto.types.FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE,
    dto.types.FixedSpeedPressureControl.UPSTREAM_CHOKE,
    dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
    dto.types.FixedSpeedPressureControl.COMMON_ASV,
    dto.types.FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
    None,
]


def _single_speed_compressor_train_mapper(
    model_config: Dict,
    input_models: Dict[str, Any],
    resources: Resources,
) -> dto.SingleSpeedCompressorTrain:
    fluid_model_reference: str = model_config.get(EcalcYamlKeywords.models_type_fluid_model)
    fluid_model = input_models.get(fluid_model_reference)
    if fluid_model is None:
        raise DataValidationError(
            data=model_config, message=f"Fluid model reference {fluid_model_reference} not found."
        )

    train_spec = model_config.get(EcalcYamlKeywords.models_type_compressor_train)
    if train_spec is None:
        raise DataValidationError(
            data=model_config,
            message=f"Missing keyword {EcalcYamlKeywords.models_type_compressor_train}"
            f" for {model_config.get(EcalcYamlKeywords.type)} {model_config.get(EcalcYamlKeywords.name)}",
        )
    # The stages are pre defined, known
    stages_data = train_spec.get(EcalcYamlKeywords.models_type_compressor_train_stages)
    if stages_data is None:
        raise DataValidationError(
            data=model_config,
            message=f"Missing keyword {EcalcYamlKeywords.models_type_compressor_train_stages}"
            f" for {model_config.get(EcalcYamlKeywords.type)} {model_config.get(EcalcYamlKeywords.name)}",
        )
    stages: List[dto.CompressorStage] = [
        dto.CompressorStage(
            compressor_chart=input_models.get(
                stage.get(EcalcYamlKeywords.models_type_compressor_train_compressor_chart)
            ),
            inlet_temperature_kelvin=convert_temperature_to_kelvin(
                [stage.get(EcalcYamlKeywords.models_type_compressor_train_inlet_temperature)],
                input_unit=Unit.CELSIUS,
            )[0],
            remove_liquid_after_cooling=True,
            pressure_drop_before_stage=stage.get(
                EcalcYamlKeywords.models_type_compressor_train_pressure_drop_ahead_of_stage, 0.0
            ),
            control_margin=0,
        )
        for stage in stages_data
    ]
    pressure_control = _pressure_control_mapper(model_config)
    maximum_discharge_pressure = model_config.get(EcalcYamlKeywords.maximum_discharge_pressure)
    if maximum_discharge_pressure and pressure_control != dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE:
        raise ValueError(
            f"Setting maximum discharge pressure for single speed compressor train is currently"
            f"only supported with {dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE} pressure control"
            f"option. Pressure control option is {pressure_control}"
        )

    return dto.SingleSpeedCompressorTrain(
        fluid_model=fluid_model,
        stages=stages,
        pressure_control=pressure_control,
        maximum_discharge_pressure=maximum_discharge_pressure,
        energy_usage_adjustment_constant=model_config.get(EcalcYamlKeywords.models_power_adjustment_constant_mw, 0),
        energy_usage_adjustment_factor=1.0,
        calculate_max_rate=model_config.get(EcalcYamlKeywords.calculate_max_rate, False),
        maximum_power=model_config.get(EcalcYamlKeywords.models_maximum_power, None),
    )


def _variable_speed_compressor_train_mapper(
    model_config: Dict,
    input_models: Dict[str, Any],
    resources: Resources,
) -> dto.VariableSpeedCompressorTrain:
    fluid_model_reference: str = model_config.get(EcalcYamlKeywords.models_type_fluid_model)
    fluid_model = input_models.get(fluid_model_reference)
    if fluid_model is None:
        raise DataValidationError(
            data=model_config, message=f"Fluid model reference {fluid_model_reference} not found."
        )

    train_spec = model_config.get(EcalcYamlKeywords.models_type_compressor_train)
    if train_spec is None:
        raise DataValidationError(
            data=model_config,
            message=f"Missing keyword {EcalcYamlKeywords.models_type_compressor_train}"
            f" for {model_config.get(EcalcYamlKeywords.type)} {model_config.get(EcalcYamlKeywords.name)}",
        )
    # The stages are pre defined, known
    stages_data = train_spec.get(EcalcYamlKeywords.models_type_compressor_train_stages)
    if stages_data is None:
        raise DataValidationError(
            data=model_config,
            message=f"Missing keyword {EcalcYamlKeywords.models_type_compressor_train_stages}"
            f" for {model_config.get(EcalcYamlKeywords.type)} {model_config.get(EcalcYamlKeywords.name)}",
        )

    stages: List[dto.CompressorStage] = []
    for stage in stages_data:
        control_margin = convert_control_margin_to_fraction(
            stage.get(EcalcYamlKeywords.models_type_compressor_train_stage_control_margin, 0.0),
            YAML_UNIT_MAPPING[
                stage.get(
                    EcalcYamlKeywords.models_type_compressor_train_stage_control_margin_unit,
                    EcalcYamlKeywords.models_type_compressor_train_stage_control_margin_unit_percentage,
                )
            ],
        )

        compressor_chart: dto.VariableSpeedChart = input_models.get(
            stage.get(EcalcYamlKeywords.models_type_compressor_train_compressor_chart)
        )

        stages.append(
            dto.CompressorStage(
                compressor_chart=compressor_chart,
                inlet_temperature_kelvin=convert_temperature_to_kelvin(
                    [stage.get(EcalcYamlKeywords.models_type_compressor_train_inlet_temperature)],
                    input_unit=Unit.CELSIUS,
                )[0],
                remove_liquid_after_cooling=True,
                pressure_drop_before_stage=stage.get(
                    EcalcYamlKeywords.models_type_compressor_train_pressure_drop_ahead_of_stage, 0.0
                ),
                control_margin=control_margin,
            )
        )
    pressure_control = _pressure_control_mapper(model_config)

    return dto.VariableSpeedCompressorTrain(
        fluid_model=fluid_model,
        stages=stages,
        energy_usage_adjustment_constant=model_config.get(EcalcYamlKeywords.models_power_adjustment_constant_mw, 0),
        energy_usage_adjustment_factor=1.0,
        calculate_max_rate=model_config.get(EcalcYamlKeywords.calculate_max_rate, False),
        pressure_control=pressure_control,
        maximum_power=model_config.get(EcalcYamlKeywords.models_maximum_power, None),
    )


def _simplified_variable_speed_compressor_train_mapper(
    model_config: Dict,
    input_models: Dict[str, Any],
    resources: Resources,
) -> Union[dto.CompressorTrainSimplifiedWithKnownStages, dto.CompressorTrainSimplifiedWithUnknownStages,]:
    fluid_model_reference: str = model_config.get(EcalcYamlKeywords.models_type_fluid_model)
    fluid_model = input_models.get(fluid_model_reference)
    if fluid_model is None:
        raise ValueError(f"Fluid model reference {fluid_model_reference} not found.")

    train_spec: dict = model_config.get(EcalcYamlKeywords.models_type_compressor_train)

    if EcalcYamlKeywords.models_type_compressor_train_stages in train_spec:
        # The stages are pre defined, known
        stages = train_spec.get(EcalcYamlKeywords.models_type_compressor_train_stages)
        return dto.CompressorTrainSimplifiedWithKnownStages(
            fluid_model=fluid_model,
            stages=[
                dto.CompressorStage(
                    inlet_temperature_kelvin=convert_temperature_to_kelvin(
                        [stage.get(EcalcYamlKeywords.models_type_compressor_train_inlet_temperature)],
                        input_unit=Unit.CELSIUS,
                    )[0],
                    compressor_chart=input_models.get(
                        stage.get(EcalcYamlKeywords.models_type_compressor_train_compressor_chart)
                    ),
                    pressure_drop_before_stage=0,
                    control_margin=0,
                    remove_liquid_after_cooling=True,
                )
                for stage in stages
            ],
            energy_usage_adjustment_constant=model_config.get(EcalcYamlKeywords.models_power_adjustment_constant_mw, 0),
            energy_usage_adjustment_factor=1.0,
            calculate_max_rate=model_config.get(EcalcYamlKeywords.calculate_max_rate, False),
            maximum_power=model_config.get(EcalcYamlKeywords.models_maximum_power, None),
        )
    else:
        # The stages are unknown, not defined
        compressor_chart_reference = train_spec[EcalcYamlKeywords.models_type_compressor_train_compressor_chart]
        return dto.CompressorTrainSimplifiedWithUnknownStages(
            fluid_model=fluid_model,
            stage=dto.CompressorStage(
                compressor_chart=input_models.get(compressor_chart_reference),
                inlet_temperature_kelvin=convert_temperature_to_kelvin(
                    [train_spec.get(EcalcYamlKeywords.models_type_compressor_train_inlet_temperature)],
                    input_unit=Unit.CELSIUS,
                )[0],
                pressure_drop_before_stage=0,
                remove_liquid_after_cooling=True,
            ),
            energy_usage_adjustment_constant=model_config.get(EcalcYamlKeywords.models_power_adjustment_constant_mw, 0),
            energy_usage_adjustment_factor=1.0,
            calculate_max_rate=model_config.get(EcalcYamlKeywords.calculate_max_rate, False),
            maximum_pressure_ratio_per_stage=train_spec.get(
                EcalcYamlKeywords.models_type_compressor_train_maximum_pressure_ratio_per_stage
            ),
            maximum_power=model_config.get(EcalcYamlKeywords.models_maximum_power, None),
        )


def _turbine_mapper(model_config: Dict, input_models: Dict[str, Any], resources: Resources) -> dto.Turbine:
    energy_usage_adjustment_constant = model_config.get(EcalcYamlKeywords.models_power_adjustment_constant_mw, 0)

    return dto.Turbine(
        lower_heating_value=model_config.get(EcalcYamlKeywords.fuel_lower_heating_value),
        turbine_loads=model_config.get(EcalcYamlKeywords.models_turbine_efficiency_table_load_values),
        turbine_efficiency_fractions=model_config.get(
            EcalcYamlKeywords.models_turbine_efficiency_table_efficiency_values
        ),
        energy_usage_adjustment_constant=energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=1.0,
    )


def _compressor_with_turbine_mapper(
    model_config: Dict, input_models: Dict[str, Any], resources: Resources
) -> dto.CompressorWithTurbine:
    compressor_train_model_reference = model_config.get(EcalcYamlKeywords.models_compressor_model)
    turbine_model_reference = model_config.get(EcalcYamlKeywords.models_turbine_model)
    compressor_train_model = resolve_reference(
        value=compressor_train_model_reference,
        references=input_models,
    )
    turbine_model = resolve_reference(
        value=turbine_model_reference,
        references=input_models,
    )
    for attr_reference, attr in (
        (compressor_train_model_reference, compressor_train_model),
        (turbine_model_reference, turbine_model),
    ):
        if attr is None:
            raise ValueError(f"{attr_reference} not found in input models")
    energy_usage_adjustment_constant = model_config.get(EcalcYamlKeywords.models_power_adjustment_constant_mw, 0)

    return dto.CompressorWithTurbine(
        compressor_train=compressor_train_model,
        turbine=turbine_model,
        energy_usage_adjustment_constant=energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=1.0,
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
    def create_model(model: Dict, input_models: Dict[str, Any], resources: Resources):
        model_creator = _model_mapper.get(model.get(EcalcYamlKeywords.type))
        if model_creator is None:
            raise ValueError(f"Unknown model type: {model.get(EcalcYamlKeywords.type)}")
        return model_creator(model_config=model, input_models=input_models, resources=resources)

    def from_yaml_to_dto(self, model_config: Dict, input_models: Dict[str, Any]) -> dto.EnergyModel:
        try:
            model_data = ModelMapper.create_model(
                model=model_config, input_models=input_models, resources=self.__resources
            )
            return model_data
        except ValidationError as ve:
            raise DtoValidationError(data=model_config, validation_error=ve) from ve
        except ValidationValueError as vve:
            raise DataValidationError(
                data=model_config,
                message=str(vve),
            ) from vve
