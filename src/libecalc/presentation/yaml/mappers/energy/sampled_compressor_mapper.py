"""Reimplements legacy's CSV column-header auto-detection for the sampled compressor
facility model (see consumer_function_mapper.py's _create_compressor_sampled).

Which of RATE, SUCTION_PRESSURE, and DISCHARGE_PRESSURE apply, and whether energy usage
is FUEL or POWER (or both), is not declared in YAML - it's detected from which columns
are present in FILE, matching legacy's COMPRESSOR_TABULAR convention (see
YamlSampledCompressor's docstring).

The YAML schema alone permits a SAMPLED_COMPRESSOR unit's INPUT to be either fuel gas
or electrical, since the actual choice depends on FILE's columns and is unknowable at
schema validation time. validate_input_energy_type re-checks that choice once FILE has
been read.
"""

from dataclasses import dataclass

from libecalc.common.errors.ecalc_validation_error import ProcessHeaderValidationException
from libecalc.domain.resource import Resource
from libecalc.energy.models.sampled_compressor import SampledCompressor
from libecalc.energy.models.sampled_compressor_units import get_invertible_fuel_power_samples
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import EnergyType

RATE_HEADER = "RATE"
SUCTION_PRESSURE_HEADER = "SUCTION_PRESSURE"
DISCHARGE_PRESSURE_HEADER = "DISCHARGE_PRESSURE"
POWER_HEADER = "POWER"
FUEL_HEADER = "FUEL"


def _get_float_column_or_none(resource: Resource, header: str) -> list[float] | None:
    if header not in resource.get_headers():
        return None
    return resource.get_float_column(header)


@dataclass
class SampledCompressorModel:
    """Result of build_sampled_compressor_model."""

    compressor: SampledCompressor
    consumes_fuel: bool


def get_sampled_compressor_topology(resource: Resource) -> tuple[bool, bool]:
    """Returns (has_fuel, has_power) from FILE's headers only — no column parsing,
    curve building, or invertibility validation. Cheap enough to call at topology-
    mapping time, before the full runtime model is needed."""
    headers = resource.get_headers()
    has_fuel = FUEL_HEADER in headers
    has_power = POWER_HEADER in headers
    if not has_fuel and not has_power:
        raise ProcessHeaderValidationException(message=f"FILE must have a '{FUEL_HEADER}' or '{POWER_HEADER}' header")
    return has_fuel, has_power


def build_sampled_compressor_model(resource: Resource) -> SampledCompressorModel:
    """Builds a SampledCompressorModel from FILE's columns."""
    has_fuel, _ = get_sampled_compressor_topology(resource)
    energy_usage_header = FUEL_HEADER if has_fuel else POWER_HEADER

    rate_values = _get_float_column_or_none(resource, RATE_HEADER)
    suction_pressure_values = _get_float_column_or_none(resource, SUCTION_PRESSURE_HEADER)
    discharge_pressure_values = _get_float_column_or_none(resource, DISCHARGE_PRESSURE_HEADER)
    energy_usage_values = resource.get_float_column(energy_usage_header)

    # Only meaningful (and only read) when the compressor is fuel-driven: POWER then
    # gives the turbine's power output for the corresponding fuel usage, not a
    # standalone energy usage value.
    power_values = _get_float_column_or_none(resource, POWER_HEADER) if has_fuel else None

    compressor = SampledCompressor(
        energy_usage_values=energy_usage_values,
        rate_values=rate_values,
        suction_pressure_values=suction_pressure_values,
        discharge_pressure_values=discharge_pressure_values,
        power_interpolation_values=power_values,
    )
    if power_values is not None:
        # Only called for its validation side effect here (raises if FUEL/POWER can't
        # be inverted into a power-to-fuel curve); the sorted samples themselves are
        # recomputed later by build_gas_turbine, if/when this compressor is actually
        # split into a turbine + consumer pair.
        get_invertible_fuel_power_samples(name="FILE", compressor=compressor)
    return SampledCompressorModel(compressor=compressor, consumes_fuel=has_fuel)


def validate_input_energy_type(unit_name: str, model: SampledCompressorModel, input_energy_type: EnergyType) -> None:
    """Cross-checks a SAMPLED_COMPRESSOR unit's declared INPUT against what FILE actually
    provides, narrowing the fuel-or-electrical ambiguity the schema alone permits (see
    AMBIGUOUS_INPUT_ENERGY["SAMPLED_COMPRESSOR"])."""
    expected_energy_type = EnergyType.FUEL_GAS if model.consumes_fuel else EnergyType.ELECTRICAL
    if input_energy_type != expected_energy_type:
        raise ValueError(
            f"'{unit_name}': INPUT provides {input_energy_type}, but FILE has a "
            f"{'FUEL' if model.consumes_fuel else 'POWER'} column, requiring {expected_energy_type} input."
        )
