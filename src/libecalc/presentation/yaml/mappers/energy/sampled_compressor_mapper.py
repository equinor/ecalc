"""Reimplements legacy's CSV column-header auto-detection for the sampled compressor
facility model (see consumer_function_mapper.py's _create_compressor_sampled).

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
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.resource import Resource
from libecalc.energy.models.sampled_compressor import SampledCompressor
from libecalc.energy.models.sampled_compressor_units import get_invertible_fuel_power_samples
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    OUTPUT_ENERGY,
    SOURCE_OUTPUT_ENERGY,
    EnergyType,
    YamlComponent,
    YamlEnergyNetwork,
    YamlSampledCompressor,
    _SampledElectricalConsumer,
    _SampledFuelGasConsumer,
    _SampledGasTurbine,
    _SampledMechanicalConsumer,
)

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
    provides, narrowing the fuel-or-electrical-or-mechanical ambiguity the schema alone
    permits (see AMBIGUOUS_INPUT_ENERGY["SAMPLED_COMPRESSOR"]).

    FILE with a FUEL column always requires fuel gas input. FILE with only a POWER
    column accepts either electrical or mechanical input - whichever it actually is
    determines whether the unit is expanded into an electrical or mechanical consumer,
    so both are valid here."""
    allowed_energy_types = (
        {EnergyType.FUEL_GAS} if model.consumes_fuel else {EnergyType.ELECTRICAL, EnergyType.MECHANICAL}
    )
    if input_energy_type not in allowed_energy_types:
        raise ValueError(
            f"'{unit_name}': INPUT provides {input_energy_type}, but FILE has a "
            f"{'FUEL' if model.consumes_fuel else 'POWER'} column, requiring "
            f"{' or '.join(sorted(allowed_energy_types))} input."
        )


def expand_sampled_compressors(
    yaml_energy_network: YamlEnergyNetwork, facility_resources: dict[str, Resource]
) -> YamlEnergyNetwork:
    """Resolves every SAMPLED_COMPRESSOR unit's FILE-dependent topology up front, cloning
    it (same FILE/RATE/SUCTION_PRESSURE/DISCHARGE_PRESSURE) into:
    - a single _SampledFuelGasConsumer, if only FUEL is present in FILE; or
    - a single _SampledElectricalConsumer or _SampledMechanicalConsumer, if only POWER
      is present in FILE, chosen by what INPUT itself provides (electrical or
      mechanical, respectively); or
    - a _SampledGasTurbine (fuel -> mechanical power) feeding a
      _SampledMechanicalConsumer (mechanical power -> none), both sharing the
      same FILE and operating point, if both FUEL and POWER are present.
    The result never contains a plain (unresolved) YamlSampledCompressor, so
    EnergyNetworkMapper itself never needs facility_resources.
    """
    output_type_by_name: dict[str, EnergyType] = {
        source.name: SOURCE_OUTPUT_ENERGY[source.type] for source in yaml_energy_network.sources
    }
    output_type_by_name.update(
        {unit.name: OUTPUT_ENERGY[unit.type] for unit in yaml_energy_network.units if unit.type in OUTPUT_ENERGY}
    )

    expanded_units: list[YamlComponent] = []
    for unit in yaml_energy_network.units:
        if not isinstance(unit, YamlSampledCompressor):
            expanded_units.append(unit)
            continue
        expanded_units.extend(_expand_sampled_compressor(unit, facility_resources, output_type_by_name))
    return yaml_energy_network.model_copy(update={"units": expanded_units})


def _retag(unit: YamlSampledCompressor, cls: type[YamlSampledCompressor], **overrides: str) -> YamlSampledCompressor:
    """Builds a cls instance carrying unit's already-validated field values (plus any
    overrides), without re-running validation - cls is one of the internal
    _Sampled*Consumer/_SampledGasTurbine subclasses, never user-constructible.

    Copies by declared field name (not unit.__dict__ directly), so this stays correct
    if YamlSampledCompressor ever gains extra fields or private attributes that aren't
    plain __dict__ entries.
    """
    field_values = {name: getattr(unit, name) for name in type(unit).model_fields}
    return cls.model_construct(_fields_set=unit.model_fields_set, **{**field_values, **overrides})


def _expand_sampled_compressor(
    unit: YamlSampledCompressor,
    facility_resources: dict[str, Resource],
    output_type_by_name: dict[str, EnergyType],
) -> list[YamlSampledCompressor]:
    if unit.file not in facility_resources:
        raise ValueError(f"'{unit.name}': cannot resolve FILE '{unit.file}' to determine its topology.")
    resource = facility_resources[unit.file]
    has_fuel, has_power = get_sampled_compressor_topology(resource)

    # Cross-check against the actual predecessor's energy type, using YAML names —
    # gives a precise error here rather than a generic type-mismatch error later,
    # keyed by internal node ids, from EnergyNetwork.create.
    provided = output_type_by_name.get(unit.input)
    if provided is not None:
        validate_input_energy_type(unit.name, build_sampled_compressor_model(resource), provided)

    if not has_fuel:
        # POWER-only: INPUT decides whether that's electrical or mechanical power.
        # provided is None when INPUT's energy type can't be determined statically
        # (e.g. it references another SAMPLED_COMPRESSOR); default to the legacy
        # COMPRESSOR_TABULAR assumption (electrical/genset) in that case.
        if provided == EnergyType.MECHANICAL:
            return [_retag(unit, _SampledMechanicalConsumer)]
        return [_retag(unit, _SampledElectricalConsumer)]
    if not has_power:
        return [_retag(unit, _SampledFuelGasConsumer)]

    turbine_name = str(ecalc_id_generator())
    turbine = _retag(unit, _SampledGasTurbine, name=turbine_name)
    compressor = _retag(unit, _SampledMechanicalConsumer, input=turbine_name)
    return [turbine, compressor]
