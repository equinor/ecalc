from typing import overload

from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.dto.types import ChartControlMarginUnit, ChartEfficiencyUnit, ChartPolytropicHeadUnit, ChartRateUnit
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
        raise DomainValidationException(msg)


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
        raise DomainValidationException(msg)


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
        raise DomainValidationException(msg)


def convert_temperature_to_kelvin(temperature_values: list[float], input_unit: Unit) -> list[float]:
    if input_unit == Unit.KELVIN:
        return temperature_values
    elif input_unit == Unit.CELSIUS:
        return [Unit.CELSIUS.to(Unit.KELVIN)(temperature) for temperature in temperature_values]
    else:
        raise DomainValidationException(
            f"Invalid input unit. Expected {Unit.KELVIN} or {Unit.CELSIUS}, got '{input_unit}'"
        )


def convert_efficiency_to_fraction(efficiency_values: list[float], input_unit: Unit) -> list[float]:
    """Convert efficiency from % or fraction to fraction."""
    if input_unit == Unit.FRACTION:
        return efficiency_values
    elif input_unit == Unit.PERCENTAGE:
        return [Unit.PERCENTAGE.to(Unit.FRACTION)(efficiency) for efficiency in efficiency_values]
    else:
        msg = f"Efficiency unit {input_unit} not supported. Must be one of {', '.join(list(ChartEfficiencyUnit))}"
        logger.error(msg)
        raise DomainValidationException(msg)


@overload
def convert_control_margin_to_fraction(control_margin: None, input_unit: Unit) -> None: ...


@overload
def convert_control_margin_to_fraction(control_margin: float, input_unit: Unit) -> float: ...


def convert_control_margin_to_fraction(control_margin: float | None, input_unit: Unit) -> float | None:
    """Convert control margin from % or fraction to fraction."""
    if control_margin is None:
        return None

    if input_unit == Unit.FRACTION:
        return control_margin
    elif input_unit == Unit.PERCENTAGE:
        return Unit.PERCENTAGE.to(Unit.FRACTION)(control_margin)
    else:
        msg = (
            f"Control margin unit {input_unit} not supported. Must be one of {', '.join(list(ChartControlMarginUnit))}"
        )
        logger.error(msg)
        raise DomainValidationException(msg)
