from dataclasses import dataclass
from typing import get_args

from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    CONSUMER_TYPES,
    FILE_DEFINED_INPUT_TYPES,
    GENERATOR_INPUT_ENERGY,
    INPUT_ENERGY,
    OUTPUT_ENERGY,
    SOURCE_OUTPUT_ENERGY,
    EnergyType,
    YamlComponent,
    YamlEnergySourceType,
)

FILE_DEFINED_INPUT_ENERGY = {EnergyType.FUEL_GAS, EnergyType.ELECTRICAL, EnergyType.MECHANICAL}

ENERGY_TYPE_COLORS: dict[EnergyType, str] = {
    EnergyType.FUEL_GAS: "#f0a35e",
    EnergyType.ELECTRICAL: "#5b9bd5",
    EnergyType.MECHANICAL: "#70ad47",
    EnergyType.DIESEL: "#a6a6a6",
}

CATEGORY_SOURCE = "Sources"
CATEGORY_PROVIDER = "Providers"
CATEGORY_CONSUMER = "Consumers"
CATEGORIES = (CATEGORY_SOURCE, CATEGORY_PROVIDER, CATEGORY_CONSUMER)


@dataclass(frozen=True)
class EnergyComponent:
    type: str
    category: str
    input_energy: tuple[EnergyType, ...]
    output_energy: tuple[EnergyType, ...]


def _ordered(energy_types: set[EnergyType]) -> tuple[EnergyType, ...]:
    return tuple(energy_type for energy_type in EnergyType if energy_type in energy_types)


def _component_type_names() -> list[str]:
    union = get_args(YamlComponent)[0]
    return [get_args(component.model_fields["type"].annotation)[0] for component in get_args(union)]


def _input_energy(component_type: str) -> set[EnergyType]:
    if component_type == "GENERATOR":
        return set(GENERATOR_INPUT_ENERGY)
    if component_type in FILE_DEFINED_INPUT_TYPES:
        return set(FILE_DEFINED_INPUT_ENERGY)
    return {INPUT_ENERGY[component_type]}


def get_energy_components() -> list[EnergyComponent]:
    sources = [
        EnergyComponent(
            type=source_type.value,
            category=CATEGORY_SOURCE,
            input_energy=(),
            output_energy=(SOURCE_OUTPUT_ENERGY[source_type],),
        )
        for source_type in YamlEnergySourceType
    ]
    units = [
        EnergyComponent(
            type=component_type,
            category=CATEGORY_CONSUMER if component_type in CONSUMER_TYPES else CATEGORY_PROVIDER,
            input_energy=_ordered(_input_energy(component_type)),
            output_energy=_ordered({OUTPUT_ENERGY[component_type]} if component_type in OUTPUT_ENERGY else set()),
        )
        for component_type in _component_type_names()
    ]
    return sources + units


def _stub_identifier(component_type: str, direction: str, energy_type: EnergyType) -> str:
    return f"{component_type}_{direction}_{energy_type.value}"


def generate_energy_components_mermaid(category: str) -> str:
    lines = ["graph LR"]
    edges_by_energy_type: dict[EnergyType, list[int]] = {energy_type: [] for energy_type in EnergyType}
    stub_identifiers_by_energy_type: dict[EnergyType, list[str]] = {energy_type: [] for energy_type in EnergyType}
    edge_count = 0

    lines.append('    subgraph legend ["Energy types"]')
    lines.append("        direction LR")
    for energy_type in EnergyType:
        identifier = f"legend_{energy_type.value}"
        stub_identifiers_by_energy_type[energy_type].append(identifier)
        lines.append(f'        {identifier}(["{energy_type.value}"])')
    lines.append("    end")

    for component in (component for component in get_energy_components() if component.category == category):
        lines.append(f'    subgraph box_{component.type} [" "]')
        lines.append("        direction LR")
        lines.append(f'        {component.type}["{component.type}"]')
        for energy_type in component.input_energy:
            identifier = _stub_identifier(component.type, "in", energy_type)
            stub_identifiers_by_energy_type[energy_type].append(identifier)
            lines.append(f'        {identifier}(["{energy_type.value}"]) --> {component.type}')
            edges_by_energy_type[energy_type].append(edge_count)
            edge_count += 1
        for energy_type in component.output_energy:
            identifier = _stub_identifier(component.type, "out", energy_type)
            stub_identifiers_by_energy_type[energy_type].append(identifier)
            lines.append(f'        {component.type} --> {identifier}(["{energy_type.value}"])')
            edges_by_energy_type[energy_type].append(edge_count)
            edge_count += 1
        lines.append("    end")

    for energy_type, color in ENERGY_TYPE_COLORS.items():
        lines.append(f"    classDef {energy_type.value} fill:{color},stroke:{color},color:#000")
        lines.append(f"    class {','.join(stub_identifiers_by_energy_type[energy_type])} {energy_type.value}")
        if edges_by_energy_type[energy_type]:
            edge_indices = ",".join(str(index) for index in edges_by_energy_type[energy_type])
            lines.append(f"    linkStyle {edge_indices} stroke:{color},stroke-width:3px")

    return "\n".join(lines)
