import pytest
from pydantic import ValidationError

from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlIndividualStreamDistributionBuilder,
    YamlInletStreamBuilder,
    YamlProcessSimulationBuilder,
)


def test_common_stream_requires_one_rate_fraction_per_target():
    stream_distribution = YamlCommonStreamDistributionBuilder().with_test_data().with_rate_fractions([1.0]).validate()

    with pytest.raises(
        ValidationError,
        match="Expected 2 RATE_FRACTIONS in common stream setting 1, got 1",
    ):
        (
            YamlProcessSimulationBuilder()
            .with_name("simulation")
            .with_target("train_a")
            .with_target("train_b")
            .with_stream_distribution(stream_distribution)
            .validate()
        )


def test_individual_streams_requires_one_inlet_stream_per_target():
    stream_distribution = (
        YamlIndividualStreamDistributionBuilder()
        .with_inlet_streams([YamlInletStreamBuilder().with_test_data().validate()])
        .validate()
    )

    with pytest.raises(
        ValidationError,
        match="Expected 2 INLET_STREAMS for the process simulation targets, got 1",
    ):
        (
            YamlProcessSimulationBuilder()
            .with_name("simulation")
            .with_target("train_a")
            .with_target("train_b")
            .with_stream_distribution(stream_distribution)
            .validate()
        )
