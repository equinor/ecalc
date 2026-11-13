import re

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    YamlComponent,
    YamlCompressorSampled,
    YamlDriveTrain,
    get_input_names,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import YamlCompressorProcessUnitInstance

_UNSAFE_IDENTIFIER_CHARACTERS = re.compile(r"\W")
_SHAFT_PREFIX = "shaft_"
_DRIVE_TRAIN_PREFIX = "drive_train_"
_COMPRESSOR_PREFIX = "compressor_"
_PIPELINE_PREFIX = "pipeline_"
_PROCESS_CLASS = "process"
_PROCESS_CLASS_DEFINITION = f"classDef {_PROCESS_CLASS} fill:#fde8c8,stroke:#d98a00,color:#000"


def _node_identifier(name: str, prefix: str = "") -> str:
    return prefix + _UNSAFE_IDENTIFIER_CHARACTERS.sub("_", name)


def _label(*lines: str) -> str:
    return "<br/>".join(line.replace('"', "'") for line in lines)


def _unit_identifier(unit: YamlComponent) -> str:
    match unit:
        case YamlDriveTrain():
            return _node_identifier(unit.shaft, _DRIVE_TRAIN_PREFIX)
        case YamlCompressorSampled():
            return _node_identifier(unit.compressor)
        case _:
            return _node_identifier(unit.name)


def _unit_label(unit: YamlComponent) -> str:
    match unit:
        case YamlDriveTrain():
            return _label(unit.type)
        case YamlCompressorSampled():
            return _label(unit.compressor, unit.type)
        case _:
            return _label(unit.name, unit.type)


def energy_network_to_mermaid(model: YamlAsset) -> str:
    network = model.energy_network
    if network is None:
        return ""

    lines = ["graph TD"]

    for source in network.sources:
        lines.append(f'    {_node_identifier(source.name)}(["{_label(source.name, source.type)}"])')

    for unit in network.units:
        lines.append(f'    {_unit_identifier(unit)}["{_unit_label(unit)}"]')

    drive_trains = [unit for unit in network.units if isinstance(unit, YamlDriveTrain)]
    shaft_names = list(dict.fromkeys(drive_train.shaft for drive_train in drive_trains))
    shaft_compressors = {shaft.name: shaft.compressors or [] for shaft in model.shafts or []}
    for shaft_name in shaft_names:
        lines.append(f'    {_node_identifier(shaft_name, _SHAFT_PREFIX)}[/"{_label(shaft_name, "SHAFT")}"/]')

    pipeline_compressors = {
        pipeline_name: [
            unit.compressor for unit in pipeline.process_units if isinstance(unit, YamlCompressorProcessUnitInstance)
        ]
        for pipeline_name, pipeline in (model.process_pipelines or {}).items()
    }
    process_compressors = list(
        dict.fromkeys(
            [
                *(compressor for shaft_name in shaft_names for compressor in shaft_compressors.get(shaft_name, [])),
                *(compressor for compressors in pipeline_compressors.values() for compressor in compressors),
            ]
        )
    )
    process_nodes = []
    for compressor in process_compressors:
        identifier = _node_identifier(compressor, _COMPRESSOR_PREFIX)
        process_nodes.append(identifier)
        lines.append(f'    {identifier}[["{_label(compressor, "COMPRESSOR")}"]]')
    for pipeline_name in pipeline_compressors:
        identifier = _node_identifier(pipeline_name, _PIPELINE_PREFIX)
        process_nodes.append(identifier)
        lines.append(f'    {identifier}[["{_label(pipeline_name, "PROCESS_PIPELINE")}"]]')

    for unit in network.units:
        for input_name in get_input_names(unit):
            lines.append(f"    {_node_identifier(input_name)} --> {_unit_identifier(unit)}")

    for drive_train in drive_trains:
        lines.append(f"    {_unit_identifier(drive_train)} --> {_node_identifier(drive_train.shaft, _SHAFT_PREFIX)}")

    for shaft_name in shaft_names:
        for compressor in shaft_compressors.get(shaft_name, []):
            lines.append(
                f"    {_node_identifier(shaft_name, _SHAFT_PREFIX)} --> {_node_identifier(compressor, _COMPRESSOR_PREFIX)}"
            )

    for pipeline_name, compressors in pipeline_compressors.items():
        for compressor in compressors:
            lines.append(
                f"    {_node_identifier(compressor, _COMPRESSOR_PREFIX)} --> {_node_identifier(pipeline_name, _PIPELINE_PREFIX)}"
            )

    if process_nodes:
        lines.append(f"    {_PROCESS_CLASS_DEFINITION}")
        lines.append(f"    class {','.join(process_nodes)} {_PROCESS_CLASS}")

    return "\n".join(lines)
