from collections import namedtuple
from collections.abc import Sequence
from typing import Any, TypeVar

import pandas as pd

from libecalc.common.errors.exceptions import (
    HeaderNotFoundException,
    InvalidColumnException,
)
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.domain.resource import Resource
from libecalc.dto.types import (
    ChartControlMarginUnit,
    ChartEfficiencyUnit,
    ChartPolytropicHeadUnit,
    ChartRateUnit,
)
from libecalc.presentation.yaml.domain.reference_service import InvalidReferenceException
from libecalc.presentation.yaml.validation_errors import (
    ValidationValueError,
)
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords

YAML_UNIT_MAPPING: dict[str, Unit] = {
    EcalcYamlKeywords.consumer_chart_efficiency_unit_factor: Unit.FRACTION,
    EcalcYamlKeywords.consumer_chart_efficiency_unit_percentage: Unit.PERCENTAGE,
    EcalcYamlKeywords.consumer_chart_head_unit_kj_per_kg: Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
    EcalcYamlKeywords.consumer_chart_head_unit_joule_per_kg: Unit.POLYTROPIC_HEAD_JOULE_PER_KG,
    EcalcYamlKeywords.consumer_chart_head_unit_m: Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN,
    EcalcYamlKeywords.consumer_chart_rate_unit_actual_volume_rate: Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
    EcalcYamlKeywords.models_type_compressor_train_stage_control_margin_unit_factor: Unit.FRACTION,
    EcalcYamlKeywords.models_type_compressor_train_stage_control_margin_unit_percentage: Unit.PERCENTAGE,
}


def is_reference(value: Any) -> bool:
    return isinstance(value, str)


ReferenceValue = TypeVar("ReferenceValue")


def resolve_model_reference(value: Any, references: dict[str, ReferenceValue]) -> ReferenceValue:
    """Check if value is a reference and return it.
    If not a reference return the original value
    If reference is invalid, raise InvalidReferenceException

    :param value: reference or value
    :param references: mapping from reference name to reference data
        {
                reference1: value1,
                reference2: value2,
        }
    :return: the actual value either referenced or not.
    """
    if not is_reference(value):
        return value

    if value not in references:
        available_references = ",\n".join(references.keys())
        raise InvalidReferenceException(
            reference_type="model", reference=value, available_references=available_references
        )

    return references[value]


def convert_rate_to_am3_per_hour(rate_values: list[float], input_unit: Unit) -> list[float]:
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


def convert_head_to_joule_per_kg(head_values: list[float], input_unit: Unit) -> list[float]:
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


def convert_head_to_meter_liquid_column(head_values: list[float], input_unit: Unit) -> list[float]:
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


def convert_temperature_to_kelvin(temperature_values: list[float], input_unit: Unit) -> list[float]:
    if input_unit == Unit.KELVIN:
        return temperature_values
    elif input_unit == Unit.CELSIUS:
        return [Unit.CELSIUS.to(Unit.KELVIN)(temperature) for temperature in temperature_values]
    else:
        raise ValueError(f"Invalid input unit. Expected {Unit.KELVIN} or {Unit.CELSIUS}, got '{input_unit}'")


def convert_efficiency_to_fraction(efficiency_values: list[float], input_unit: Unit) -> list[float]:
    """Convert efficiency from % or fraction to fraction."""
    if input_unit == Unit.FRACTION:
        return efficiency_values
    elif input_unit == Unit.PERCENTAGE:
        return [Unit.PERCENTAGE.to(Unit.FRACTION)(efficiency) for efficiency in efficiency_values]
    else:
        msg = f"Efficiency unit {input_unit} not supported. Must be one of {', '.join(list(ChartEfficiencyUnit))}"
        logger.error(msg)
        raise ValueError(msg)


def convert_control_margin_to_fraction(control_margin: float | None, input_unit: Unit) -> float | None:
    """Convert control margin from % or fraction to fraction."""
    if control_margin is None:
        return None

    if input_unit == Unit.FRACTION:
        return control_margin
    elif input_unit == Unit.PERCENTAGE:
        return Unit.PERCENTAGE.to(Unit.FRACTION)(control_margin)
    else:
        msg = f"Control margin unit {input_unit} not supported.Must be one of {', '.join(list(ChartControlMarginUnit))}"
        logger.error(msg)
        raise ValueError(msg)


def chart_curves_as_resource_to_dto_format(resource: Resource) -> list[dict[str, list[float]]]:
    resource_headers = resource.get_headers()

    if "SPEED" not in resource_headers:
        raise InvalidColumnException(message="Resource is missing SPEED header!", header="SPEED")

    resource_data = []
    for header in resource_headers:
        column = resource.get_column(header)
        resource_data.append(column)
        try:
            pd.Series(column).astype(float)
        except ValueError as e:
            msg = f"Resource contains non-numeric value: {e}"
            logger.error(msg)
            raise InvalidColumnException(message=msg, header=header) from e
    df = pd.DataFrame(data=resource_data, index=resource_headers).transpose().astype(float)
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
    chart_config: dict,
    units_to_include: Sequence[str] = (
        EcalcYamlKeywords.consumer_chart_rate,
        EcalcYamlKeywords.consumer_chart_head,
        EcalcYamlKeywords.consumer_chart_efficiency,
    ),
) -> dict[str, Unit]:
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


def get_single_speed_chart_data(resource: Resource) -> ChartData:
    try:
        speed_values = _get_float_column(resource=resource, header=EcalcYamlKeywords.consumer_chart_speed)

        if not _all_numbers_equal(speed_values):
            raise InvalidColumnException(
                header=EcalcYamlKeywords.consumer_chart_speed,
                message="All speeds should be equal when creating a single-speed chart.",
            )
        # Get first speed, all are equal.
        speed = speed_values[0]
    except HeaderNotFoundException:
        logger.debug("Speed not specified for single speed chart, setting speed to 1.")
        speed = 1

    efficiency_values = _get_float_column(
        resource=resource,
        header=EcalcYamlKeywords.consumer_chart_efficiency,
    )
    rate_values = _get_float_column(
        resource=resource,
        header=EcalcYamlKeywords.consumer_chart_rate,
    )
    head_values = _get_float_column(
        resource=resource,
        header=EcalcYamlKeywords.consumer_chart_head,
    )
    return ChartData(speed, rate_values, head_values, efficiency_values)


def _get_float_column(resource: Resource, header: str) -> list[float]:
    try:
        column = resource.get_column(header)
        column = [float(value) for value in column]
    except ValueError as e:
        msg = f"Resource contains non-numeric value: {e}"
        logger.error(msg)
        raise InvalidColumnException(header=header, message=msg) from e
    return column


def _all_numbers_equal(values: list[int | float]) -> bool:
    return len(set(values)) == 1
