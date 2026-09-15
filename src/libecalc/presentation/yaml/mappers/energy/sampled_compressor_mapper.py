"""Reimplements legacy's CSV column-header auto-detection for the sampled compressor
facility model.

Which of RATE, SUCTION_PRESSURE, and DISCHARGE_PRESSURE apply, and whether energy usage
is FUEL or POWER (or both), is not declared in YAML - it's detected from which columns
are present in FILE, matching legacy's COMPRESSOR_TABULAR convention (see
YamlSampledCompressor's docstring).

The YAML schema alone permits a SAMPLED_COMPRESSOR unit's INPUT to be fuel gas,
electrical, or mechanical, since the actual choice depends on FILE's columns (and, when
FILE has only POWER, on what INPUT itself provides) and is unknowable at schema
validation time. validate_input_energy_type re-checks that choice once FILE has been
read.
"""

from dataclasses import dataclass

from libecalc.common.errors.ecalc_validation_error import ProcessHeaderValidationException
from libecalc.common.errors.exceptions import InvalidColumnException
from libecalc.domain.resource import Resource
from libecalc.energy.models.sampled_compressor import SampledCompressor
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import EnergyType

RATE_HEADER = "RATE"
SUCTION_PRESSURE_HEADER = "SUCTION_PRESSURE"
DISCHARGE_PRESSURE_HEADER = "DISCHARGE_PRESSURE"
FUEL_HEADER = "FUEL"
POWER_HEADER = "POWER"

_VARIABLE_HEADERS = (RATE_HEADER, SUCTION_PRESSURE_HEADER, DISCHARGE_PRESSURE_HEADER)


@dataclass
class SampledCompressorModel:
    """Result of build_sampled_compressor_model."""

    compressor: SampledCompressor
    consumes_fuel: bool


def get_sampled_compressor_topology(resource: Resource) -> tuple[bool, bool]:
    """Returns (has_fuel, has_power) from FILE's headers only — cheap enough to call at
    topology-mapping time, before the full model needs to be built."""
    headers = {header.upper() for header in resource.get_headers()}
    has_fuel = FUEL_HEADER in headers
    has_power = POWER_HEADER in headers
    if not has_fuel and not has_power:
        raise ProcessHeaderValidationException(message=f"FILE must have a '{FUEL_HEADER}' or '{POWER_HEADER}' header")
    return has_fuel, has_power


def build_sampled_compressor_model(resource: Resource) -> SampledCompressorModel:
    """Parse a tabular Resource into a SampledCompressorModel.

    Expected columns (case-insensitive, at least one of the three variables plus
    at least one of FUEL/POWER):
        RATE, SUCTION_PRESSURE, DISCHARGE_PRESSURE (independent variables, any subset)
        FUEL: the sampled fuel usage (Sm3/d). Primary energy usage when present.
        POWER: the sampled power (MW). Primary energy usage when FUEL is absent;
            when both FUEL and POWER are present, POWER is instead treated as data
            sampled at the same operating points, used to derive a dedicated
            turbine's power-to-fuel curve.
    """
    headers = {header.upper() for header in resource.get_headers()}

    variable_headers = [header for header in _VARIABLE_HEADERS if header in headers]
    if not variable_headers:
        raise InvalidColumnException(
            header=RATE_HEADER,
            message=f"Sampled compressor resource must contain at least one of: {', '.join(_VARIABLE_HEADERS)}.",
        )

    has_fuel, has_power = get_sampled_compressor_topology(resource)

    if has_fuel:
        energy_usage_values = resource.get_float_column(FUEL_HEADER)
        power_interpolation_values = resource.get_float_column(POWER_HEADER) if has_power else None
    else:
        energy_usage_values = resource.get_float_column(POWER_HEADER)
        power_interpolation_values = None

    compressor = SampledCompressor(
        energy_usage_values=energy_usage_values,
        rate_values=resource.get_float_column(RATE_HEADER) if RATE_HEADER in headers else None,
        suction_pressure_values=(
            resource.get_float_column(SUCTION_PRESSURE_HEADER) if SUCTION_PRESSURE_HEADER in headers else None
        ),
        discharge_pressure_values=(
            resource.get_float_column(DISCHARGE_PRESSURE_HEADER) if DISCHARGE_PRESSURE_HEADER in headers else None
        ),
        power_interpolation_values=power_interpolation_values,
    )
    # SampledCompressor's own constructor already validates FUEL/POWER invertibility -
    # no separate check needed here.
    return SampledCompressorModel(compressor=compressor, consumes_fuel=has_fuel)


def validate_input_energy_type(unit_name: str, has_fuel: bool, input_energy_type: EnergyType) -> None:
    """Cross-checks a SAMPLED_COMPRESSOR unit's declared INPUT against what FILE
    actually provides: FUEL column requires fuel gas input; POWER-only accepts either
    electrical or mechanical. Takes has_fuel directly rather than a full
    SampledCompressorModel, since this never needs the built model."""
    allowed_energy_types = {EnergyType.FUEL_GAS} if has_fuel else {EnergyType.ELECTRICAL, EnergyType.MECHANICAL}
    if input_energy_type not in allowed_energy_types:
        raise ValueError(
            f"'{unit_name}': INPUT provides {input_energy_type}, but FILE has a "
            f"{'FUEL' if has_fuel else 'POWER'} column, requiring "
            f"{' or '.join(sorted(allowed_energy_types))} input."
        )
