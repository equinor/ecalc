from collections import namedtuple
from typing import Any, Dict, List, Optional, Sequence, TypeVar, Union

import pandas as pd
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.dto.types import (
    ChartControlMarginUnit,
    ChartEfficiencyUnit,
    ChartPolytropicHeadUnit,
    ChartRateUnit,
)
from libecalc.input.validation_errors import (
    ResourceValidationError,
    ValidationValueError,
)
from libecalc.input.yaml_entities import Resource
from libecalc.input.yaml_keywords import EcalcYamlKeywords

YAML_UNIT_MAPPING: Dict[str, Unit] = {
    EcalcYamlKeywords.consumer_chart_efficiency_unit_factor: Unit.FRACTION,
    EcalcYamlKeywords.consumer_chart_efficiency_unit_percentage: Unit.PERCENTAGE,
    EcalcYamlKeywords.consumer_chart_head_unit_kj_per_kg: Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
    EcalcYamlKeywords.consumer_chart_head_unit_joule_per_kg: Unit.POLYTROPIC_HEAD_JOULE_PER_KG,
    EcalcYamlKeywords.consumer_chart_head_unit_m: Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN,
    EcalcYamlKeywords.consumer_chart_rate_unit_actual_volume_rate: Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
    EcalcYamlKeywords.models_type_compressor_train_stage_control_margin_unit_factor: Unit.FRACTION,
    EcalcYamlKeywords.models_type_compressor_train_stage_control_margin_unit_percentage: Unit.PERCENTAGE,
}


def resolve_reference(
    value: Any,
    references: Dict[str, Any],
    none_if_not_found: bool = False,
) -> Any:
    """Check if value is a reference and return it, if not a reference return the original value
    :param none_if_not_found: return None if reference is not found
    :param value: reference or value
    :param references: mapping from reference name to reference data
        {
                reference1: value1,
                reference2: value2,
        }
    :return: the actual value either referenced or not.
    """
    if isinstance(value, str):
        resolved = references.get(value, None)
        if resolved is not None:
            return resolved
        elif none_if_not_found:
            return None
        else:
            return value
    else:
        return value


ReferenceValue = TypeVar("ReferenceValue")


def resolve_and_validate_reference(value: str, references: Dict[str, ReferenceValue]) -> ReferenceValue:
    model = references.get(value)
    if isinstance(model, str) or model is None:
        raise ValueError(f"Reference {value} not found in references \nAvailable: ({', '.join(references.keys())})")
    return model


def resolve_reference_and_raise_error_if_not_found(value: str, references: Dict[str, Any]):
    model = resolve_reference(value, references=references)
    if model is None or isinstance(model, str):
        raise ValueError(f"Value {value} not found in references ({', '.join(list(references.keys()))})")
    return model


def convert_rate_to_am3_per_hour(rate_values: List[float], input_unit: Unit) -> List[float]:
    """Convert rate from ay supported rate to Am3/h."""
    if input_unit == Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR:
        return rate_values
    else:
        msg = (
            f"Rate unit {input_unit} not (yet) supported for compressor chart."
            f"Needs to be one of {', '.join(list(ChartRateUnit))}"
        )
        logger.error(msg)
        raise ValueError(msg)


def convert_head_to_joule_per_kg(head_values: List[float], input_unit: Unit) -> List[float]:
    """Convert head from [KJ/kg] or [m] to [J/kg]."""
    if input_unit == Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG:
        return [Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG.to(Unit.POLYTROPIC_HEAD_JOULE_PER_KG)(h) for h in head_values]
    elif input_unit == Unit.POLYTROPIC_HEAD_JOULE_PER_KG:  # KJ/kg
        return head_values
    elif input_unit == Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN:  # m
        return [
            Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN.to(Unit.POLYTROPIC_HEAD_JOULE_PER_KG)(head) for head in head_values
        ]
    else:
        msg = (
            f"Chart head unit {input_unit} not (yet) supported."
            f"Must be one of {', '.join(list(ChartPolytropicHeadUnit))}"
        )
        logger.error(msg)
        raise ValueError(msg)


def convert_head_to_meter_liquid_column(head_values: List[float], input_unit: Unit) -> List[float]:
    """Convert head from [KJ/kg], [J/kg] to meter liquid column [m]. This is used for pump charts."""
    if input_unit == Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG:
        return [
            Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG.to(Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN)(h) for h in head_values
        ]
    elif input_unit == Unit.POLYTROPIC_HEAD_JOULE_PER_KG:  # KJ/kg
        return [Unit.POLYTROPIC_HEAD_JOULE_PER_KG.to(Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN)(h) for h in head_values]
    elif input_unit == Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN:  # m
        return head_values
    else:
        msg = (
            f"Chart head unit {input_unit} not (yet) supported."
            f"Must be one of {', '.join(list(ChartPolytropicHeadUnit))}"
        )
        logger.error(msg)
        raise ValueError(msg)


def convert_temperature_to_kelvin(temperature_values: List[float], input_unit: Unit) -> List[float]:
    if input_unit == Unit.KELVIN:
        return temperature_values
    elif input_unit == Unit.CELSIUS:
        return [Unit.CELSIUS.to(Unit.KELVIN)(temperature) for temperature in temperature_values]
    else:
        raise ValueError(f"Invalid input unit. Expected {Unit.KELVIN} or {Unit.CELSIUS}, got '{input_unit}'")


def convert_efficiency_to_fraction(efficiency_values: List[float], input_unit: Unit) -> List[float]:
    """Convert efficiency from % or fraction to fraction."""
    if input_unit == Unit.FRACTION:
        return efficiency_values
    elif input_unit == Unit.PERCENTAGE:
        return [Unit.PERCENTAGE.to(Unit.FRACTION)(efficiency) for efficiency in efficiency_values]
    else:
        msg = f"Efficiency unit {input_unit} not supported." f"Must be one of {', '.join(list(ChartEfficiencyUnit))}"
        logger.error(msg)
        raise ValueError(msg)


def convert_control_margin_to_fraction(control_margin: Optional[float], input_unit: Unit) -> Optional[float]:
    """Convert control margin from % or fraction to fraction."""
    if control_margin is None:
        return None

    if input_unit == Unit.FRACTION:
        return control_margin
    elif input_unit == Unit.PERCENTAGE:
        return Unit.PERCENTAGE.to(Unit.FRACTION)(control_margin)
    else:
        msg = (
            f"Control margin unit {input_unit} not supported."
            f"Must be one of {', '.join(list(ChartControlMarginUnit))}"
        )
        logger.error(msg)
        raise ValueError(msg)


def chart_curves_as_resource_to_dto_format(resource: Resource, resource_name: str) -> List[Dict[str, List[float]]]:
    try:
        df = pd.DataFrame(data=resource.data, index=resource.headers).transpose().astype(float)
    except ValueError as e:
        msg = f"Resource {resource_name} contains non-numeric value: {e}"
        logger.error(msg)
        raise ValueError(msg) from e
    grouped_by_speed = df.groupby(EcalcYamlKeywords.consumer_chart_speed, sort=False)
    curves = [
        {
            "speed": group,
            "rate": list(grouped_by_speed.get_group(group)[EcalcYamlKeywords.consumer_chart_rate]),
            "head": list(grouped_by_speed.get_group(group)[EcalcYamlKeywords.consumer_chart_head]),
            "efficiency": list(grouped_by_speed.get_group(group)[EcalcYamlKeywords.consumer_chart_efficiency]),
        }
        for group in grouped_by_speed.groups
    ]

    return curves


SUPPORTED_CHART_EFFICIENCY_UNITS = [efficiency_unit.value for efficiency_unit in ChartEfficiencyUnit]

SUPPORTED_CHART_HEAD_UNITS = [head_unit.value for head_unit in ChartPolytropicHeadUnit]


def get_units_from_chart_config(
    chart_config: Dict,
    units_to_include: Sequence[
        Union[
            EcalcYamlKeywords.consumer_chart_rate,
            EcalcYamlKeywords.consumer_chart_head,
            EcalcYamlKeywords.consumer_chart_efficiency,
        ]
    ] = (
        EcalcYamlKeywords.consumer_chart_rate,
        EcalcYamlKeywords.consumer_chart_head,
        EcalcYamlKeywords.consumer_chart_efficiency,
    ),
) -> Dict[str, Unit]:
    """:param chart_config:
    :param units_to_include: Allow only some units to support charts that only takes efficiency as input.
    """
    units_config = chart_config.get(EcalcYamlKeywords.consumer_chart_units, {})

    units_not_in_units_to_include = [unit_key for unit_key in units_config if unit_key not in units_to_include]

    file_info = ""
    file = chart_config.get(EcalcYamlKeywords.file)
    if file is not None:
        file_info = f" for the file '{file}' "

    if len(units_not_in_units_to_include) != 0:
        error_message = f"You cannot specify units for: {', '.join(units_not_in_units_to_include)} in this context. You can only specify units for: {', '.join(units_to_include)}"
        error_message += file_info
        error_message += f" for '{chart_config.get(EcalcYamlKeywords.name)}'"
        raise ValidationValueError(error_message)

    units = {}
    for unit in units_to_include:
        provided_unit = units_config.get(unit)

        if unit == EcalcYamlKeywords.consumer_chart_efficiency:
            if provided_unit not in SUPPORTED_CHART_EFFICIENCY_UNITS:
                raise ValidationValueError(
                    f"Chart unit {EcalcYamlKeywords.consumer_chart_efficiency} for '{chart_config.get(EcalcYamlKeywords.name)}' {file_info}"
                    f" must be one of {', '.join(SUPPORTED_CHART_EFFICIENCY_UNITS)}. "
                    f"Given {EcalcYamlKeywords.consumer_chart_efficiency} was '{provided_unit}.",
                    key=EcalcYamlKeywords.consumer_chart_efficiency,
                )

            units[unit] = YAML_UNIT_MAPPING[provided_unit]
        elif unit == EcalcYamlKeywords.consumer_chart_head:
            if provided_unit not in SUPPORTED_CHART_HEAD_UNITS:
                raise ValidationValueError(
                    f"Chart unit {EcalcYamlKeywords.consumer_chart_head} for '{chart_config.get(EcalcYamlKeywords.name)}' {file_info}"
                    f" must be one of {', '.join(SUPPORTED_CHART_HEAD_UNITS)}. "
                    f"Given {EcalcYamlKeywords.consumer_chart_head} was '{provided_unit}.'",
                    key=EcalcYamlKeywords.consumer_chart_head,
                )

            units[unit] = YAML_UNIT_MAPPING[provided_unit]

        elif unit == EcalcYamlKeywords.consumer_chart_rate:
            if provided_unit != ChartRateUnit.AM3_PER_HOUR:
                raise ValidationValueError(
                    f"Chart unit {EcalcYamlKeywords.consumer_chart_rate} for '{chart_config.get(EcalcYamlKeywords.name)}' {file_info}"
                    f" must be '{ChartRateUnit.AM3_PER_HOUR}'. "
                    f"Given {EcalcYamlKeywords.consumer_chart_rate} was '{provided_unit}'.",
                    key=EcalcYamlKeywords.consumer_chart_rate,
                )

            units[unit] = YAML_UNIT_MAPPING[provided_unit]
    return units


ChartData = namedtuple(
    "ChartData",
    ["speed", "rate", "head", "efficiency"],
)


def get_single_speed_chart_data(resource: Resource, resource_name: str) -> ChartData:
    try:
        speed_values = _get_float_column(
            resource=resource, header=EcalcYamlKeywords.consumer_chart_speed, resource_name=resource_name
        )

        if not _all_numbers_equal(speed_values):
            raise ResourceValidationError(
                resource=resource,
                resource_name=resource_name,
                message="All speeds should be equal when creating a single-speed chart.",
            )
        # Get first speed, all are equal.
        speed = speed_values[0]
    except ValueError:
        logger.debug(f"Speed not specified for single speed chart {resource_name}, setting speed to 1.")
        speed = 1

    efficiency_values = _get_float_column(
        resource=resource,
        header=EcalcYamlKeywords.consumer_chart_efficiency,
        resource_name=resource_name,
    )
    rate_values = _get_float_column(
        resource=resource,
        header=EcalcYamlKeywords.consumer_chart_rate,
        resource_name=resource_name,
    )
    head_values = _get_float_column(
        resource=resource,
        header=EcalcYamlKeywords.consumer_chart_head,
        resource_name=resource_name,
    )
    return ChartData(speed, rate_values, head_values, efficiency_values)


def _get_float_column(resource: Resource, header: str, resource_name: str) -> List[float]:
    column_index = resource.headers.index(header)
    column = resource.data[column_index]
    try:
        column = [float(value) for value in column]
    except ValueError as e:
        msg = f"Resource {resource_name} contains non-numeric value: {e}"
        logger.error(msg)
        raise ResourceValidationError(resource=resource, resource_name=resource_name, message=msg) from e
    return column


def _all_numbers_equal(values: List[Union[int, float]]) -> bool:
    return len(set(values)) == 1
