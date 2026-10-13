import pytest
from pydantic import ValidationError

from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder


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


def test_distinct_pipelines_can_each_be_targeted_by_their_own_simulation():
    pipeline_1 = YamlProcessPipelineBuilder().with_test_data().with_name("train_1").validate()
    pipeline_2 = YamlProcessPipelineBuilder().with_test_data().with_name("train_2").validate()

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
        YamlAssetBuilder()
        .with_test_data()
        .with_process_pipelines({pipeline_1.name: pipeline_1, pipeline_2.name: pipeline_2})
        .with_process_simulations([simulation_1, simulation_2])
        .validate()
    )

    assert [simulation.name for simulation in asset.process_simulations] == ["simulation_1", "simulation_2"]
