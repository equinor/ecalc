from io import StringIO

import pytest

from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlEnergyNetwork
from libecalc.presentation.yaml.yaml_types.energy.yaml_generator_definition import YamlGeneratorDefinition
from libecalc.testing.energy_builders import (
    YamlElectricalConsumerBuilder,
    YamlEnergyGeneratorBuilder,
    YamlEnergyNetworkBuilder,
    YamlFuelGasSourceBuilder,
    YamlGeneratorDefinitionBuilder,
)
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlCompressorModelChartBuilder,
    YamlDefinitionsBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
    compressors_in,
    shaft_for,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder

COMPRESSOR_MODEL = "compressor_model"


def _energy_network(generator_model: str | YamlGeneratorDefinition) -> YamlEnergyNetwork:
    source = YamlFuelGasSourceBuilder().with_test_data().validate()
    generator = (
        YamlEnergyGeneratorBuilder().with_test_data().with_input(source.name).with_model(generator_model).validate()
    )
    load = YamlElectricalConsumerBuilder().with_test_data().with_input(generator.name).validate()
    return YamlEnergyNetworkBuilder().with_sources([source]).with_units([generator, load]).validate()


def _create_model(
    yaml_model_factory,
    compressor_models: list[str],
    energy_network: YamlEnergyNetwork | None = None,
    end: str | None = None,
):
    pipelines = [
        YamlProcessPipelineBuilder()
        .with_name(f"train_{index}")
        .with_compressor_item(compressor=f"compressor_{index}", model=model)
        .validate()
        for index, model in enumerate(compressor_models)
    ]
    simulations = [
        YamlProcessSimulationBuilder()
        .with_name(f"sim_{index}")
        .with_pipeline(pipeline)
        .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        .validate()
        for index, pipeline in enumerate(pipelines)
    ]
    asset_builder = (
        YamlAssetBuilder()
        .with_test_data()
        .with_shafts([shaft_for(pipeline, name=f"shaft_{pipeline.name}") for pipeline in pipelines])
        .with_compressors([compressor for pipeline in pipelines for compressor in compressors_in(pipeline)])
        .with_process_pipelines({pipeline.name: pipeline for pipeline in pipelines})
        .with_process_simulations(simulations)
        .with_definitions(
            YamlDefinitionsBuilder()
            .with_compressor_model(COMPRESSOR_MODEL, YamlCompressorModelChartBuilder().with_test_data().validate())
            .validate()
        )
    )
    if energy_network is not None:
        asset_builder = asset_builder.with_energy_network(energy_network)
    if end is not None:
        asset_builder = asset_builder.with_end(end)

    yaml_string = PyYamlYamlModel.dump_yaml(
        yaml_dict=asset_builder.validate().model_dump(
            serialize_as_any=True, mode="json", exclude_unset=True, by_alias=True
        )
    )
    return yaml_model_factory(
        configuration=ResourceStream(name="nextgen_model", stream=StringIO(yaml_string)), resources={}
    )


def test_valid_process_simulations_and_energy_network(yaml_model_factory):
    model = _create_model(
        yaml_model_factory,
        compressor_models=[COMPRESSOR_MODEL],
        energy_network=_energy_network(YamlGeneratorDefinitionBuilder().with_test_data().validate()),
    )

    assert model.validate_nextgen() is model


def test_errors_from_process_simulations_and_energy_network_are_combined(yaml_model_factory):
    model = _create_model(
        yaml_model_factory,
        compressor_models=["ghost_1", COMPRESSOR_MODEL, "ghost_2"],
        energy_network=_energy_network("missing_generator"),
    )

    with pytest.raises(ModelValidationException) as exc_info:
        model.validate_nextgen()

    errors = exc_info.value.errors()
    assert len(errors) == 3
    assert "'ghost_1' not found" in errors[0].message
    assert "'ghost_2' not found" in errors[1].message
    assert "'missing_generator' not found" in errors[2].message
    assert errors[2].location.keys[0] == "ENERGY_NETWORK"


def test_unconnected_source_is_reported(yaml_model_factory):
    connected_network = _energy_network(YamlGeneratorDefinitionBuilder().with_test_data().validate())
    unconnected_source = YamlFuelGasSourceBuilder().with_test_data().with_name("unconnected_fuel_gas").validate()
    energy_network = (
        YamlEnergyNetworkBuilder()
        .with_sources([*connected_network.sources, unconnected_source])
        .with_units(connected_network.units)
        .validate()
    )
    model = _create_model(yaml_model_factory, compressor_models=[COMPRESSOR_MODEL], energy_network=energy_network)

    with pytest.raises(ModelValidationException) as exc_info:
        model.validate_nextgen()

    (error,) = exc_info.value.errors()
    assert "unconnected_fuel_gas" in error.message
    assert error.location.as_dot_separated() == "ENERGY_NETWORK.SOURCES[1]"
    assert error.file_context is not None


def test_validate_for_run_errors_are_reported_once(yaml_model_factory):
    model = _create_model(
        yaml_model_factory,
        compressor_models=[COMPRESSOR_MODEL],
        energy_network=_energy_network(YamlGeneratorDefinitionBuilder().with_test_data().validate()),
        end="1900-01-01",
    )

    with pytest.raises(ModelValidationException) as exc_info:
        model.validate_nextgen()

    (error,) = exc_info.value.errors()
    assert "end date" in error.message
