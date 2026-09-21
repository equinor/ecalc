from __future__ import annotations

import enum
from dataclasses import dataclass

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.errors.exceptions import EcalcError
from libecalc.domain.resource import Resource
from libecalc.energy.energy_types import ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.energy.models.sampled_compressor import SampledCompressor
from libecalc.energy.models.sampled_compressor_factory import SampledCompressorFactory
from libecalc.energy.models.turbine_from_compressor_sampled import FuelPowerCurve, get_fuel_power_curve
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlCompressorSampled


class NodeRole(enum.Enum):
    UNIT = "unit"
    TURBINE = "turbine"


class DemandSource(enum.Enum):
    ENERGY_USAGE = "energy_usage"
    POWER = "power"


@dataclass(frozen=True)
class NodeKey:
    name: str
    role: NodeRole = NodeRole.UNIT


def unit_key(name: str) -> NodeKey:
    return NodeKey(name, NodeRole.UNIT)


def turbine_key(name: str) -> NodeKey:
    return NodeKey(name, NodeRole.TURBINE)


@dataclass(frozen=True)
class Columns:
    has_fuel: bool
    has_power: bool
    has_rate: bool
    has_suction_pressure: bool
    has_discharge_pressure: bool


@dataclass(frozen=True)
class ConsumerSpec:
    key: NodeKey
    name: str
    model: SampledCompressor
    input_energy_type: type[Energy]
    demand_source: DemandSource


@dataclass(frozen=True)
class TurbineSpec:
    key: NodeKey
    name: str
    fuel_power_curve: FuelPowerCurve


NodeSpec = ConsumerSpec | TurbineSpec


@dataclass(frozen=True)
class Expansion:
    nodes: tuple[NodeSpec, ...]
    connections: tuple[tuple[NodeKey, NodeKey], ...]


def _float_column_or_none(resource: Resource, header: str) -> list[float] | None:
    return resource.get_float_column(header) if header in resource.get_headers() else None


def load_model(resource: Resource) -> tuple[SampledCompressor, Columns]:
    headers = resource.get_headers()
    columns = Columns(
        has_fuel=EcalcYamlKeywords.consumer_tabular_fuel in headers,
        has_power=EcalcYamlKeywords.consumer_tabular_power in headers,
        has_rate=EcalcYamlKeywords.consumer_function_rate in headers,
        has_suction_pressure=EcalcYamlKeywords.consumer_function_suction_pressure in headers,
        has_discharge_pressure=EcalcYamlKeywords.consumer_function_discharge_pressure in headers,
    )
    if not columns.has_fuel and not columns.has_power:
        raise EcalcValidationException(
            f"Resource must have a {EcalcYamlKeywords.consumer_tabular_fuel} and/or "
            f"{EcalcYamlKeywords.consumer_tabular_power} column, got headers {headers}."
        )

    energy_usage_header = (
        EcalcYamlKeywords.consumer_tabular_fuel if columns.has_fuel else EcalcYamlKeywords.consumer_tabular_power
    )
    power_interpolation_values = (
        resource.get_float_column(EcalcYamlKeywords.consumer_tabular_power)
        if columns.has_fuel and columns.has_power
        else None
    )
    model = SampledCompressorFactory.create(
        energy_usage_values=resource.get_float_column(energy_usage_header),
        rate_values=_float_column_or_none(resource, EcalcYamlKeywords.consumer_function_rate),
        suction_pressure_values=_float_column_or_none(resource, EcalcYamlKeywords.consumer_function_suction_pressure),
        discharge_pressure_values=_float_column_or_none(
            resource, EcalcYamlKeywords.consumer_function_discharge_pressure
        ),
        power_interpolation_values=power_interpolation_values,
    )
    return model, columns


def _check_variables_tabulated(unit: YamlCompressorSampled, columns: Columns) -> None:
    given = {
        EcalcYamlKeywords.consumer_function_rate: (unit.rate, columns.has_rate),
        EcalcYamlKeywords.consumer_function_suction_pressure: (unit.suction_pressure, columns.has_suction_pressure),
        EcalcYamlKeywords.consumer_function_discharge_pressure: (
            unit.discharge_pressure,
            columns.has_discharge_pressure,
        ),
    }
    not_tabulated = [
        name for name, (expression, tabulated) in given.items() if expression is not None and not tabulated
    ]
    if not_tabulated:
        raise EcalcValidationException(f"{', '.join(not_tabulated)} given, but not tabulated in '{unit.file}'.")
    missing = [name for name, (expression, tabulated) in given.items() if expression is None and tabulated]
    if missing:
        raise EcalcValidationException(f"'{unit.file}' tabulates {', '.join(missing)}, which must be given.")


def _energy_name(energy_type: type[Energy]) -> str:
    return energy_type.__name__


def expand(unit: YamlCompressorSampled, resource: Resource, upstream_output_type: type[Energy]) -> Expansion:
    try:
        model, columns = load_model(resource)
    except EcalcError as e:
        raise EcalcValidationException(f"'{unit.name}': invalid sampled compressor file '{unit.file}': {e}") from e

    try:
        _check_variables_tabulated(unit, columns)
    except EcalcValidationException as e:
        raise EcalcValidationException(f"'{unit.name}': {e.message}") from e

    user_input = unit_key(unit.input)

    if columns.has_fuel and columns.has_power:
        _require_upstream(unit, upstream_output_type, FuelGasRate, "a fuel-driven compressor with a generated turbine")
        turbine = TurbineSpec(
            key=turbine_key(unit.name),
            name=f"{unit.name} turbine",
            fuel_power_curve=get_fuel_power_curve(model),
        )
        consumer = ConsumerSpec(
            key=unit_key(unit.name),
            name=unit.name,
            model=model,
            input_energy_type=MechanicalPower,
            demand_source=DemandSource.POWER,
        )
        return Expansion(
            nodes=(turbine, consumer),
            connections=((user_input, turbine.key), (turbine.key, consumer.key)),
        )

    if columns.has_fuel:
        _require_upstream(unit, upstream_output_type, FuelGasRate, "a fuel-driven compressor")
        input_energy_type: type[Energy] = FuelGasRate
    else:
        if upstream_output_type not in (ElectricalPower, MechanicalPower):
            raise EcalcValidationException(
                f"'{unit.name}': a power-driven compressor must be fed electrical or mechanical power, "
                f"but INPUT '{unit.input}' provides {_energy_name(upstream_output_type)}."
            )
        input_energy_type = upstream_output_type

    consumer = ConsumerSpec(
        key=unit_key(unit.name),
        name=unit.name,
        model=model,
        input_energy_type=input_energy_type,
        demand_source=DemandSource.ENERGY_USAGE,
    )
    return Expansion(nodes=(consumer,), connections=((user_input, consumer.key),))


def _require_upstream(
    unit: YamlCompressorSampled,
    upstream_output_type: type[Energy],
    required: type[Energy],
    what: str,
) -> None:
    if upstream_output_type is not required:
        raise EcalcValidationException(
            f"'{unit.name}': {what} must be fed {_energy_name(required)}, "
            f"but INPUT '{unit.input}' provides {_energy_name(upstream_output_type)}."
        )


__all__ = [
    "Columns",
    "ConsumerSpec",
    "DemandSource",
    "Expansion",
    "NodeKey",
    "NodeRole",
    "NodeSpec",
    "TurbineSpec",
    "expand",
    "load_model",
    "turbine_key",
    "unit_key",
]
