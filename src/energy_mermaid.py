from dataclasses import dataclass
from typing import get_args

from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    CONSUMER_TYPES,
    GENERATOR_INPUT_ENERGY,
    INPUT_ENERGY,
    OUTPUT_ENERGY,
    SOURCE_OUTPUT_ENERGY,
    EnergyType,
    YamlComponent,
    YamlConverterBase,
    YamlEnergySourceType,
    YamlJunctionBase,
)

ENERGY_TYPE_COLORS: dict[EnergyType, str] = {
    EnergyType.FUEL_GAS: "#f0a35e",
    EnergyType.ELECTRICAL: "#5b9bd5",
    EnergyType.MECHANICAL: "#70ad47",
    EnergyType.DIESEL: "#a6a6a6",
}

CATEGORY_SOURCES = "Sources"
CATEGORY_CONVERTERS = "Converters"
CATEGORY_TRANSPORTERS = "Transporters"
CATEGORY_JUNCTIONS = "Junctions"
CATEGORY_CONSUMERS = "Consumers"
CATEGORIES = (
    CATEGORY_SOURCES,
    CATEGORY_CONVERTERS,
    CATEGORY_TRANSPORTERS,
    CATEGORY_JUNCTIONS,
    CATEGORY_CONSUMERS,
)

MULTIPLE_INPUTS_COUNT = 2
SOLID_EDGE = "-->"
DASHED_EDGE = "-.->"
DASHED_LINK_STYLE = "stroke-dasharray:6 4"


@dataclass(frozen=True)
class EnergyUnit:
    type: str
    category: str
    input_energy: tuple[EnergyType, ...]
    output_energy: tuple[EnergyType, ...]
    multiple_inputs: bool = False

    @property
    def has_alternative_inputs(self) -> bool:
        return len(self.input_energy) > 1 and not self.multiple_inputs

    @property
    def input_count(self) -> int:
        return MULTIPLE_INPUTS_COUNT if self.multiple_inputs else 1


def _ordered(energy_types: set[EnergyType]) -> tuple[EnergyType, ...]:
    return tuple(energy_type for energy_type in EnergyType if energy_type in energy_types)


def _unit_classes() -> list[type]:
    union = get_args(YamlComponent)[0]
    return list(get_args(union))


def _unit_type_name(unit_class: type) -> str:
    return get_args(unit_class.model_fields["type"].annotation)[0]


def _input_energy(unit_type: str) -> set[EnergyType]:
    if unit_type == "GENERATOR":
        return set(GENERATOR_INPUT_ENERGY)
    return {INPUT_ENERGY[unit_type]}


def _category(unit_class: type, unit_type: str, input_energy: set[EnergyType], output_energy: set[EnergyType]) -> str:
    if unit_type in CONSUMER_TYPES:
        return CATEGORY_CONSUMERS
    if issubclass(unit_class, YamlJunctionBase):
        return CATEGORY_JUNCTIONS
    if issubclass(unit_class, YamlConverterBase) and input_energy == output_energy:
        return CATEGORY_TRANSPORTERS
    return CATEGORY_CONVERTERS


def get_energy_units() -> list[EnergyUnit]:
    sources = [
        EnergyUnit(
            type=source_type.value,
            category=CATEGORY_SOURCES,
            input_energy=(),
            output_energy=(SOURCE_OUTPUT_ENERGY[source_type],),
        )
        for source_type in YamlEnergySourceType
    ]
    units = []
    for unit_class in _unit_classes():
        unit_type = _unit_type_name(unit_class)
        input_energy = _input_energy(unit_type)
        output_energy = {OUTPUT_ENERGY[unit_type]} if unit_type in OUTPUT_ENERGY else set()
        units.append(
            EnergyUnit(
                type=unit_type,
                category=_category(unit_class, unit_type, input_energy, output_energy),
                input_energy=_ordered(input_energy),
                output_energy=_ordered(output_energy),
                multiple_inputs=issubclass(unit_class, YamlJunctionBase),
            )
        )
    return sources + units


def _stub_identifier(unit_type: str, direction: str, energy_type: EnergyType, index: int = 0) -> str:
    return f"{unit_type}_{direction}{index}_{energy_type.value}"


def generate_energy_units_mermaid(category: str) -> str:
    lines = ["graph LR"]
    edges_by_energy_type: dict[EnergyType, list[int]] = {energy_type: [] for energy_type in EnergyType}
    dashed_edges: list[int] = []
    stub_identifiers_by_energy_type: dict[EnergyType, list[str]] = {energy_type: [] for energy_type in EnergyType}
    edge_count = 0

    lines.append('    subgraph legend ["Energy types"]')
    lines.append("        direction LR")
    for energy_type in EnergyType:
        identifier = f"legend_{energy_type.value}"
        stub_identifiers_by_energy_type[energy_type].append(identifier)
        lines.append(f'        {identifier}(["{energy_type.value}"])')
    lines.append("    end")

    for unit in (unit for unit in get_energy_units() if unit.category == category):
        lines.append(f'    subgraph box_{unit.type} [" "]')
        lines.append("        direction LR")
        lines.append(f'        {unit.type}["{unit.type}"]')
        input_edge = DASHED_EDGE if unit.has_alternative_inputs else SOLID_EDGE
        for energy_type in unit.input_energy:
            for index in range(unit.input_count):
                identifier = _stub_identifier(unit.type, "in", energy_type, index)
                stub_identifiers_by_energy_type[energy_type].append(identifier)
                lines.append(f'        {identifier}(["{energy_type.value}"]) {input_edge} {unit.type}')
                edges_by_energy_type[energy_type].append(edge_count)
                if unit.has_alternative_inputs:
                    dashed_edges.append(edge_count)
                edge_count += 1
        for energy_type in unit.output_energy:
            identifier = _stub_identifier(unit.type, "out", energy_type)
            stub_identifiers_by_energy_type[energy_type].append(identifier)
            lines.append(f'        {unit.type} {SOLID_EDGE} {identifier}(["{energy_type.value}"])')
            edges_by_energy_type[energy_type].append(edge_count)
            edge_count += 1
        lines.append("    end")

    for energy_type, color in ENERGY_TYPE_COLORS.items():
        lines.append(f"    classDef {energy_type.value} fill:{color},stroke:{color},color:#000")
        lines.append(f"    class {','.join(stub_identifiers_by_energy_type[energy_type])} {energy_type.value}")
        if edges_by_energy_type[energy_type]:
            edge_indices = ",".join(str(index) for index in edges_by_energy_type[energy_type])
            lines.append(f"    linkStyle {edge_indices} stroke:{color},stroke-width:3px")
    if dashed_edges:
        lines.append(f"    linkStyle {','.join(str(index) for index in dashed_edges)} {DASHED_LINK_STYLE}")

    return "\n".join(lines)
