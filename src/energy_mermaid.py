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
    YamlConverterBase,
    YamlEnergySourceType,
    YamlJunctionBase,
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

SUBCATEGORY_CONVERTERS = "Converters"
SUBCATEGORY_JUNCTIONS = "Junctions"
PROVIDER_SUBCATEGORY_BASE_CLASSES: dict[type, str] = {
    YamlConverterBase: SUBCATEGORY_CONVERTERS,
    YamlJunctionBase: SUBCATEGORY_JUNCTIONS,
}

MULTIPLE_INPUTS_COUNT = 2
SOLID_EDGE = "-->"
DASHED_EDGE = "-.->"
DASHED_LINK_STYLE = "stroke-dasharray:6 4"


@dataclass(frozen=True)
class EnergyComponent:
    type: str
    category: str
    input_energy: tuple[EnergyType, ...]
    output_energy: tuple[EnergyType, ...]
    multiple_inputs: bool = False
    subcategory: str | None = None

    @property
    def has_alternative_inputs(self) -> bool:
        return len(self.input_energy) > 1 and not self.multiple_inputs

    @property
    def input_count(self) -> int:
        return MULTIPLE_INPUTS_COUNT if self.multiple_inputs else 1


def _ordered(energy_types: set[EnergyType]) -> tuple[EnergyType, ...]:
    return tuple(energy_type for energy_type in EnergyType if energy_type in energy_types)


def _component_classes() -> list[type]:
    union = get_args(YamlComponent)[0]
    return list(get_args(union))


def _component_type_name(component_class: type) -> str:
    return get_args(component_class.model_fields["type"].annotation)[0]


def _provider_subcategory(component_class: type) -> str | None:
    for base_class, subcategory in PROVIDER_SUBCATEGORY_BASE_CLASSES.items():
        if issubclass(component_class, base_class):
            return subcategory
    return None


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
    units = []
    for component_class in _component_classes():
        component_type = _component_type_name(component_class)
        is_consumer = component_type in CONSUMER_TYPES
        units.append(
            EnergyComponent(
                type=component_type,
                category=CATEGORY_CONSUMER if is_consumer else CATEGORY_PROVIDER,
                input_energy=_ordered(_input_energy(component_type)),
                output_energy=_ordered({OUTPUT_ENERGY[component_type]} if component_type in OUTPUT_ENERGY else set()),
                multiple_inputs=issubclass(component_class, YamlJunctionBase),
                subcategory=None if is_consumer else _provider_subcategory(component_class),
            )
        )
    return sources + units


def get_subcategories(category: str) -> list[str]:
    return list(
        dict.fromkeys(
            component.subcategory
            for component in get_energy_components()
            if component.category == category and component.subcategory is not None
        )
    )


def _stub_identifier(component_type: str, direction: str, energy_type: EnergyType, index: int = 0) -> str:
    return f"{component_type}_{direction}{index}_{energy_type.value}"


def generate_energy_components_mermaid(category: str, subcategory: str | None = None) -> str:
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

    selected_components = (
        component
        for component in get_energy_components()
        if component.category == category and (subcategory is None or component.subcategory == subcategory)
    )
    for component in selected_components:
        lines.append(f'    subgraph box_{component.type} [" "]')
        lines.append("        direction LR")
        lines.append(f'        {component.type}["{component.type}"]')
        input_edge = DASHED_EDGE if component.has_alternative_inputs else SOLID_EDGE
        for energy_type in component.input_energy:
            for index in range(component.input_count):
                identifier = _stub_identifier(component.type, "in", energy_type, index)
                stub_identifiers_by_energy_type[energy_type].append(identifier)
                lines.append(f'        {identifier}(["{energy_type.value}"]) {input_edge} {component.type}')
                edges_by_energy_type[energy_type].append(edge_count)
                if component.has_alternative_inputs:
                    dashed_edges.append(edge_count)
                edge_count += 1
        for energy_type in component.output_energy:
            identifier = _stub_identifier(component.type, "out", energy_type)
            stub_identifiers_by_energy_type[energy_type].append(identifier)
            lines.append(f'        {component.type} {SOLID_EDGE} {identifier}(["{energy_type.value}"])')
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
