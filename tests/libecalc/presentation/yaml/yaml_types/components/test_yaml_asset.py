import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.yaml_shaft import YamlShaft
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlEcalcEventBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder


def test_ecalc_events_requires_yaml_version_v2_or_later():
    """ECALC_EVENTS was introduced in yaml version 2 and must not be usable in v1 documents."""
    dump_kwargs = {"serialize_as_any": True, "mode": "json", "exclude_unset": True, "by_alias": True}
    asset_data = YamlAssetBuilder().with_test_data().validate().model_dump(**dump_kwargs)
    event_data = YamlEcalcEventBuilder().with_test_data().validate().model_dump(**dump_kwargs)

    with pytest.raises(ValidationError, match="ECALC_EVENTS"):
        YamlAsset.model_validate({**asset_data, "ECALC_EVENTS": [event_data]})

    with pytest.raises(ValidationError, match="ECALC_EVENTS"):
        YamlAsset.model_validate({**asset_data, "VERSION": 1, "ECALC_EVENTS": [event_data]})

    asset = YamlAsset.model_validate({**asset_data, "VERSION": 2, "ECALC_EVENTS": [event_data]})
    assert asset.version == 2
    assert len(asset.ecalc_events) == 1


def test_default_yaml_version_is_v1():
    asset = YamlAssetBuilder().with_test_data().validate()
    assert asset.version == 1


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
    yaml_compressor_builder_factory,
    yaml_asset_builder_factory,
):
    pipeline_1 = (
        yaml_process_pipeline_builder_factory()
        .with_name("train_1")
        .with_shaft_driven_item(
            name="compressor_1", target=yaml_compressor_builder_factory().with_test_data().validate(), shaft="shaft_1"
        )
        .validate()
    )
    pipeline_2 = (
        yaml_process_pipeline_builder_factory()
        .with_name("train_2")
        .with_shaft_driven_item(
            name="compressor_2", target=yaml_compressor_builder_factory().with_test_data().validate(), shaft="shaft_2"
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
        .with_shafts([YamlShaft(name="shaft_1"), YamlShaft(name="shaft_2")])
        .with_process_pipelines({pipeline_1.name: pipeline_1, pipeline_2.name: pipeline_2})
        .with_process_simulations([simulation_1, simulation_2])
        .validate()
    )

    assert [simulation.name for simulation in asset.process_simulations] == ["simulation_1", "simulation_2"]
