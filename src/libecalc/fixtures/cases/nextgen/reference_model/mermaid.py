import re

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlDriveTrain, get_input_names

_UNSAFE_IDENTIFIER_CHARACTERS = re.compile(r"\W")
_SHAFT_PREFIX = "shaft_"


def _node_identifier(name: str, prefix: str = "") -> str:
    return prefix + _UNSAFE_IDENTIFIER_CHARACTERS.sub("_", name)


def _label(*lines: str) -> str:
    return "<br/>".join(line.replace('"', "'") for line in lines)


def energy_network_to_mermaid(model: YamlAsset) -> str:
    network = model.energy_network
    if network is None:
        return ""

    shaft_compressors = {shaft.name: shaft.compressors for shaft in model.shafts or []}
    lines = ["graph TD"]

    for source in network.sources:
        lines.append(f'    {_node_identifier(source.name)}(["{_label(source.name, source.type)}"])')

    for unit in network.units:
        lines.append(f'    {_node_identifier(unit.name)}["{_label(unit.name, unit.type)}"]')

    drive_trains = [unit for unit in network.units if isinstance(unit, YamlDriveTrain)]
    for shaft_name in dict.fromkeys(drive_train.shaft for drive_train in drive_trains):
        compressors = ", ".join(shaft_compressors.get(shaft_name) or [])
        lines.append(
            f'    {_node_identifier(shaft_name, _SHAFT_PREFIX)}[/"{_label(shaft_name, "SHAFT", compressors)}"/]'
        )

    for unit in network.units:
        for input_name in get_input_names(unit):
            lines.append(f"    {_node_identifier(input_name)} --> {_node_identifier(unit.name)}")

    for drive_train in drive_trains:
        lines.append(
            f"    {_node_identifier(drive_train.name)} --> {_node_identifier(drive_train.shaft, _SHAFT_PREFIX)}"
        )

    return "\n".join(lines)
