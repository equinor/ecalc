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

from libecalc.common.errors.exceptions import IllegalStateException, InvalidColumnException
from libecalc.domain.resource import Resource
from libecalc.energy.models.sampled_compressor import SampledCompressor
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
FUEL_HEADER = "FUEL"
POWER_HEADER = "POWER"

_VARIABLE_HEADERS = (RATE_HEADER, SUCTION_PRESSURE_HEADER, DISCHARGE_PRESSURE_HEADER)


def get_sampled_compressor_topology(resource: Resource) -> tuple[bool, bool]:
    """Returns (has_fuel, has_power) from FILE's headers only — cheap enough to call at
    topology-mapping time, before the full model needs to be built."""
    headers = {header.upper() for header in resource.get_headers()}
    has_fuel = FUEL_HEADER in headers
    has_power = POWER_HEADER in headers
    if not has_fuel and not has_power:
        raise InvalidColumnException(
            header=FUEL_HEADER,
            message="Sampled compressor resource must contain FUEL, POWER, or both.",
        )
    return has_fuel, has_power


def build_sampled_compressor_model(resource: Resource) -> SampledCompressor:
    """Parse a tabular Resource into a SampledCompressor model.

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

    return SampledCompressor(
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


def validate_input_energy_type(unit_name: str, has_fuel: bool, input_energy_type: EnergyType) -> None:
    """Cross-checks a SAMPLED_COMPRESSOR unit's declared INPUT against what FILE actually
    provides, narrowing the fuel-or-electrical-or-mechanical ambiguity the schema alone
    permits.

    FILE with a FUEL column always requires fuel gas input. FILE with only a POWER
    column accepts either electrical or mechanical input - whichever it actually is
    determines whether the unit is expanded into an electrical or mechanical consumer,
    so both are valid here."""
    allowed_energy_types = {EnergyType.FUEL_GAS} if has_fuel else {EnergyType.ELECTRICAL, EnergyType.MECHANICAL}
    if input_energy_type not in allowed_energy_types:
        raise ValueError(
            f"'{unit_name}': INPUT provides {input_energy_type}, but FILE has a "
            f"{'FUEL' if has_fuel else 'POWER'} column, requiring "
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
    - a _SampledGasTurbine (fuel -> mechanical power) feeding a _SampledMechanicalConsumer
      (mechanical power -> none), both sharing the same FILE and operating point, if
      both FUEL and POWER are present.
    The result never contains a plain (unresolved) YamlSampledCompressor.
    """
    output_type_by_name: dict[str, EnergyType] = {
        source.name: SOURCE_OUTPUT_ENERGY[source.type] for source in yaml_energy_network.sources
    }
    output_type_by_name.update(
        {unit.name: OUTPUT_ENERGY[unit.type] for unit in yaml_energy_network.units if unit.type in OUTPUT_ENERGY}
    )
    # Every name already in use in the network, regardless of unit type - the set a
    # freshly generated turbine name must never collide with (unlike output_type_by_name
    # above, which is deliberately narrower - it's only used to resolve what a
    # SAMPLED_COMPRESSOR's INPUT itself provides).
    all_names = {source.name for source in yaml_energy_network.sources} | {
        unit.name for unit in yaml_energy_network.units
    }

    expanded_units: list[YamlComponent] = []
    for unit in yaml_energy_network.units:
        if not isinstance(unit, YamlSampledCompressor):
            expanded_units.append(unit)
            continue
        expanded_units.extend(_expand_sampled_compressor(unit, facility_resources, output_type_by_name, all_names))
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
    all_names: set[str],
) -> list[YamlSampledCompressor]:
    if unit.file not in facility_resources:
        raise ValueError(f"'{unit.name}': cannot resolve FILE '{unit.file}' to determine its topology.")
    resource = facility_resources[unit.file]
    has_fuel, has_power = get_sampled_compressor_topology(resource)

    # Cross-check against the actual predecessor's energy type, using YAML names —
    # gives a precise error here rather than a generic type-mismatch error later,
    # keyed by internal node ids, from EnergyNetwork.create.
    provided = output_type_by_name.get(unit.input)
    if provided is None:
        raise IllegalStateException(
            f"'{unit.name}': cannot determine the energy type provided by INPUT '{unit.input}'. "
            "This should be unreachable: YamlEnergyNetwork validation only accepts an INPUT "
            "naming a source or a unit with a known output energy type."
        )
    validate_input_energy_type(unit.name, has_fuel, provided)

    if not has_fuel:
        # POWER-only: INPUT decides whether that's electrical or mechanical power.
        if provided == EnergyType.MECHANICAL:
            return [_retag(unit, _SampledMechanicalConsumer)]
        return [_retag(unit, _SampledElectricalConsumer)]
    if not has_power:
        return [_retag(unit, _SampledFuelGasConsumer)]

    turbine_name = f"{unit.name}-turbine"
    if turbine_name in all_names:
        raise ValueError(
            f"'{unit.name}': cannot generate a distinct turbine name - '{turbine_name}' is already in use."
        )
    turbine = _retag(unit, _SampledGasTurbine, name=turbine_name)
    compressor = _retag(unit, _SampledMechanicalConsumer, input=turbine_name)
    return [turbine, compressor]
