from collections.abc import Mapping

from libecalc.domain.resource import Resource
from libecalc.energy.models.combustion_engine_fuel_model import DieselEngineFuelModel, TurbineFuelModel
from libecalc.energy.models.generator_set_fuel_model import (
    EngineDrivenGeneratorSetFuelModel,
    GeneratorSetFuelModel,
    SampledGeneratorSetFuelModel,
)
from libecalc.presentation.yaml.definition_expander import expect_resolved
from libecalc.presentation.yaml.mappers.energy.combustion_engine_fuel_model_mapper import (
    map_combustion_engine_fuel_model,
)
from libecalc.presentation.yaml.mappers.energy.curve_model_mapper import map_curve_model
from libecalc.presentation.yaml.yaml_types.energy.yaml_generator_definition import YamlGeneratorDefinition
from libecalc.presentation.yaml.yaml_types.energy.yaml_generator_set_definition import (
    YamlGeneratorSetEngineDefinition,
)
from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import YamlTurbineDefinition
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile

_POWER_HEADER = "POWER"
_FUEL_HEADER = "FUEL"


def map_generator_set_fuel_model(
    unit_name: str,
    definition: YamlGeneratorDefinition | YamlGeneratorSetEngineDefinition,
    resources: Mapping[str, Resource],
    source_lower_heating_value: float | None,
    input_name: str,
) -> GeneratorSetFuelModel:
    if isinstance(definition, YamlGeneratorSetEngineDefinition):
        engine = expect_resolved(definition.engine, YamlTurbineDefinition, field="MODEL.ENGINE")
        model_class = TurbineFuelModel if definition.type == "GAS_TURBINE_DRIVEN" else DieselEngineFuelModel
        engine_fuel_model = map_combustion_engine_fuel_model(
            unit_name,
            engine,
            resources,
            source_lower_heating_value=source_lower_heating_value,
            input_name=input_name,
            model_class=model_class,
        )
        return EngineDrivenGeneratorSetFuelModel(
            engine_fuel_model=engine_fuel_model, generator_efficiency=definition.generator_efficiency
        )
    return _map_generator_set_curve_fuel_model(unit_name, definition, resources)


def _map_generator_set_curve_fuel_model(
    unit_name: str, definition: YamlGeneratorDefinition, resources: Mapping[str, Resource]
) -> SampledGeneratorSetFuelModel:
    curve = definition.curve
    return map_curve_model(
        unit_name=unit_name,
        curve=curve if isinstance(curve, YamlFile) else (curve.power, curve.fuel),
        resources=resources,
        x_header=_POWER_HEADER,
        y_header=_FUEL_HEADER,
        build=lambda powers, fuels: SampledGeneratorSetFuelModel(powers=powers, fuels=fuels),
    )
