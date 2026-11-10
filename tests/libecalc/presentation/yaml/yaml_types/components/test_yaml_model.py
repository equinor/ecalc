import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_document import validate_yaml_document
from libecalc.presentation.yaml.yaml_types.components.yaml_model import YamlNextgenModel
from libecalc.presentation.yaml.yaml_types.yaml_compressor import YamlCompressor
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlDefinitionsBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
    YamlTimelineBuilder,
    shaft_for,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder, YamlLegacyAssetBuilder


def test_timeline_requires_yaml_version_v4_or_later():
    dump_kwargs = {"serialize_as_any": True, "mode": "json", "exclude_unset": True, "by_alias": True}
    asset_data = {"END": "2025-01-01"}
    timeline_data = YamlTimelineBuilder().with_test_data().validate().model_dump(**dump_kwargs)

    with pytest.raises(ValidationError, match="TIMELINE"):
        YamlNextgenModel.model_validate({**asset_data, "YAML_VERSION": 3, "TIMELINE": timeline_data})

    asset = YamlNextgenModel.model_validate({**asset_data, "YAML_VERSION": 4, "TIMELINE": timeline_data})
    assert asset.yaml_version == 4
    assert len(asset.timeline.events) == 1


def test_default_yaml_version_is_v1():
    dump_kwargs = {"serialize_as_any": True, "mode": "json", "exclude_unset": True, "by_alias": True}
    asset_data = YamlLegacyAssetBuilder().with_test_data().validate().model_dump(**dump_kwargs)
    del asset_data["YAML_VERSION"]

    asset = validate_yaml_document(asset_data)
    assert isinstance(asset, YamlAsset)
    assert asset.yaml_version == 1


@pytest.mark.parametrize(
    ("version", "extra_data"),
    [(2, {"FUEL_TYPES": [], "INSTALLATIONS": []}), (3, {}), (4, {})],
)
def test_yaml_version_2_and_later_is_validated_as_nextgen_model(version, extra_data):
    asset = validate_yaml_document({"YAML_VERSION": version, "END": "2025-01-01", **extra_data})
    assert isinstance(asset, YamlNextgenModel)
    assert asset.yaml_version == version


def test_nextgen_root_elements_are_rejected_for_legacy_yaml():
    with pytest.raises(ValidationError, match="SHAFTS"):
        validate_yaml_document({"END": "2025-01-01", "FUEL_TYPES": [], "INSTALLATIONS": [], "SHAFTS": []})


def test_invalid_yaml_version_is_reported_on_yaml_version():
    with pytest.raises(ValidationError, match="YAML_VERSION"):
        validate_yaml_document({"YAML_VERSION": 99, "END": "2025-01-01"})


def test_pipeline_can_only_be_targeted_by_one_simulation():
    pipeline = YamlProcessPipelineBuilder().with_test_data().validate()

    simulation_1 = (
        YamlProcessSimulationBuilder()
        .with_name("simulation_1")
        .with_pipeline(pipeline)
        .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        .validate()
    )
    simulation_2 = (
        YamlProcessSimulationBuilder()
        .with_name("simulation_2")
        .with_pipeline(pipeline)
        .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        .validate()
    )

    with pytest.raises(
        ValidationError,
        match="A process pipeline can currently only be targeted by one process simulation",
    ):
        (
            YamlAssetBuilder()
            .with_test_data()
            .with_process_pipelines({pipeline.name: pipeline})
            .with_process_simulations([simulation_1, simulation_2])
            .validate()
        )


def test_distinct_pipelines_can_each_be_targeted_by_their_own_simulation(
    yaml_process_pipeline_builder_factory,
    yaml_asset_builder_factory,
):
    pipeline_1 = (
        yaml_process_pipeline_builder_factory()
        .with_name("train_1")
        .with_compressor_item(
            compressor="compressor_1",
        )
        .validate()
    )
    pipeline_2 = (
        yaml_process_pipeline_builder_factory()
        .with_name("train_2")
        .with_compressor_item(
            compressor="compressor_2",
        )
        .validate()
    )

    simulation_1 = (
        YamlProcessSimulationBuilder()
        .with_name("simulation_1")
        .with_pipeline(pipeline_1)
        .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        .validate()
    )
    simulation_2 = (
        YamlProcessSimulationBuilder()
        .with_name("simulation_2")
        .with_pipeline(pipeline_2)
        .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        .validate()
    )

    asset = (
        yaml_asset_builder_factory()
        .with_test_data()
        .with_definitions(YamlDefinitionsBuilder().with_test_data().validate())
        .with_shafts([shaft_for(pipeline_1, name="shaft_1"), shaft_for(pipeline_2, name="shaft_2")])
        .with_compressors([YamlCompressor(name="compressor_1"), YamlCompressor(name="compressor_2")])
        .with_process_pipelines({pipeline_1.name: pipeline_1, pipeline_2.name: pipeline_2})
        .with_process_simulations([simulation_1, simulation_2])
        .validate()
    )

    assert [simulation.name for simulation in asset.process_simulations] == ["simulation_1", "simulation_2"]
