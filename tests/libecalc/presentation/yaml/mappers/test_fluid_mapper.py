from datetime import datetime

from libecalc.common.time_utils import Period
from libecalc.presentation.yaml.mappers.fluid_mapper import fluid_definition_mapper
from libecalc.presentation.yaml.yaml_types.models.yaml_fluid import YamlEosModel
from libecalc.presentation.yaml.yaml_types.process.yaml_fluid_definitions import (
    YamlFluidComposition,
)
from libecalc.process.fluid_stream.fluid_model import EoSModel, FluidComposition
from libecalc.testing.process_builders import YamlCompositionFluidDefinitionBuilder


def test_composition_fluid_is_materialized_for_each_period(
    expression_evaluator_factory,
):
    periods = [
        Period(
            start=datetime(2020, 1, 1),
            end=datetime(2021, 1, 1),
        ),
        Period(
            start=datetime(2021, 1, 1),
            end=datetime(2022, 1, 1),
        ),
    ]
    evaluator = expression_evaluator_factory.from_periods(
        periods=periods,
        variables={
            "FEED;METHANE": [90.0, 80.0],
            "FEED;ETHANE": [10.0, 20.0],
        },
    )
    definition = (
        YamlCompositionFluidDefinitionBuilder()
        .with_test_data()
        .with_eos_model(YamlEosModel.PR)
        .with_composition(
            YamlFluidComposition(
                methane="FEED;METHANE",
                ethane="FEED;ETHANE",
            )
        )
        .validate()
    )

    time_series_fluid = fluid_definition_mapper(
        definition,
        expression_evaluator=evaluator,
    )

    assert time_series_fluid.get_value(periods[0]).eos_model == EoSModel.PR
    assert time_series_fluid.get_value(periods[0]).composition == FluidComposition(
        methane=90.0,
        ethane=10.0,
    )
    assert time_series_fluid.get_value(periods[1]).composition == FluidComposition(
        methane=80.0,
        ethane=20.0,
    )
