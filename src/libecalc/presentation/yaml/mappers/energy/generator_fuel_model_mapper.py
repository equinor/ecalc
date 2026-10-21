from collections.abc import Mapping

from libecalc.domain.resource import Resource
from libecalc.energy.models.generator_fuel_model import GeneratorFuelModel
from libecalc.presentation.yaml.mappers.energy.curve_model_mapper import map_curve_model
from libecalc.presentation.yaml.yaml_types.energy.yaml_generator_definition import YamlGeneratorDefinition
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile

POWER_HEADER = "POWER"
FUEL_HEADER = "FUEL"


def map_generator_fuel_model(
    unit_name: str, definition: YamlGeneratorDefinition, resources: Mapping[str, Resource]
) -> GeneratorFuelModel:
    curve = definition.curve
    return map_curve_model(
        unit_name=unit_name,
        curve=curve if isinstance(curve, YamlFile) else (curve.power, curve.fuel),
        resources=resources,
        x_header=POWER_HEADER,
        y_header=FUEL_HEADER,
        build=lambda powers, fuels: GeneratorFuelModel(powers=powers, fuels=fuels),
    )
