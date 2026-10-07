from collections.abc import Mapping

from libecalc.domain.resource import Resource
from libecalc.energy.models.generator_set_fuel_model import GeneratorSetFuelModel
from libecalc.presentation.yaml.mappers.energy.curve_model_mapper import map_curve_model
from libecalc.presentation.yaml.yaml_types.energy.yaml_generator_set_definition import YamlGeneratorSetDefinition
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile

POWER_HEADER = "POWER"
FUEL_HEADER = "FUEL"


def map_generator_set_fuel_model(
    unit_name: str, definition: YamlGeneratorSetDefinition, resources: Mapping[str, Resource]
) -> GeneratorSetFuelModel:
    curve = definition.curve
    return map_curve_model(
        unit_name=unit_name,
        curve=curve if isinstance(curve, YamlFile) else (curve.power, curve.fuel),
        resources=resources,
        x_header=POWER_HEADER,
        y_header=FUEL_HEADER,
        build=lambda powers, fuels: GeneratorSetFuelModel(powers=powers, fuels=fuels),
    )
