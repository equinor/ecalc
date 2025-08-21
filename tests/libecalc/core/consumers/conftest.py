from datetime import datetime
from uuid import uuid4

import pytest

from libecalc.common.component_type import ComponentType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import ExpressionEvaluator, VariablesMap
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumerComponent
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_component import (
    GeneratorSetEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated import TabularConsumerFunction
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.regularity import Regularity
from libecalc.dto import Emission, FuelType
from libecalc.dto.types import FuelTypeUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.expression_time_series_variable import ExpressionTimeSeriesVariable
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.yaml_entities import MemoryResource


@pytest.fixture
def methane_values():
    return [0.005, 1.5, 3, 4]


@pytest.fixture
def fuel_gas() -> dict[Period, FuelType]:
    return {
        Period(datetime(1900, 1, 1), datetime(2021, 1, 1)): FuelType(
            id=uuid4(),
            name="fuel_gas",
            user_defined_category=FuelTypeUserDefinedCategoryType.FUEL_GAS,
            emissions=[
                Emission(
                    name="co2",
                    factor=Expression.setup_from_expression(value="2.20"),
                )
            ],
        )
    }


@pytest.fixture
def tabulated_fuel_consumer_factory(fuel_gas, expression_evaluator_factory, tabular_consumer_function_factory):
    def create_tabulated_fuel_consumer(
        expression_evaluator: ExpressionEvaluator,
    ) -> FuelConsumerComponent:
        regularity = Regularity(
            expression_input=1,
            expression_evaluator=expression_evaluator,
            target_period=expression_evaluator.get_period(),
        )
        tabulated = tabular_consumer_function_factory(
            function_values=[0, 2, 4],
            variables={"RATE": [0, 1, 2]},
            expression_evaluator=expression_evaluator,
            regularity=regularity,
        )

        return FuelConsumerComponent(
            id=uuid4(),
            path_id=PathID("fuel_consumer"),
            component_type=ComponentType.GENERIC,
            fuel=fuel_gas,
            energy_usage_model=TemporalModel({Period(datetime(1900, 1, 1)): tabulated}),
            regularity=regularity,
            expression_evaluator=expression_evaluator,
        )

    return create_tabulated_fuel_consumer


@pytest.fixture
def electricity_consumer_factory(direct_expression_model_factory):
    def _create_electricity_consumer(
        expression_evaluator: ExpressionEvaluator, energy_usage_model: TemporalModel = None, values: list[float] = None
    ) -> ElectricityConsumer:
        regularity = Regularity(
            expression_evaluator=expression_evaluator,
            target_period=expression_evaluator.get_period(),
            expression_input=1,
        )
        if energy_usage_model is None:
            periods = expression_evaluator.get_periods().periods
            if values is None:
                values = [0.0] * len(periods)
            else:
                # Pad or truncate values to match periods
                values = (values + [0.0] * len(periods))[: len(periods)]

            energy_usage_model = TemporalModel(
                {
                    period: direct_expression_model_factory(
                        expression=value,
                        energy_usage_type=EnergyUsageType.POWER,
                        consumption_rate_type=RateType.STREAM_DAY,
                        expression_evaluator=expression_evaluator.get_subset(
                            *period.get_period_indices(expression_evaluator.get_periods())
                        ),
                        regularity=regularity.get_subset(
                            *period.get_period_indices(expression_evaluator.get_periods())
                        ),
                    )
                    for period, value in zip(periods, values)
                }
            )

        return ElectricityConsumer(
            id=uuid4(),
            path_id=PathID("direct_consumer"),
            component_type=ComponentType.GENERIC,
            energy_usage_model=energy_usage_model,
            regularity=regularity,
            expression_evaluator=expression_evaluator,
        )

    return _create_electricity_consumer


@pytest.fixture
def generator_set_sampled_model_2mw() -> GeneratorSetModel:
    resource = MemoryResource(
        headers=["POWER", "FUEL"],
        data=[[0, 0.5, 1, 2], [0, 0.6, 1, 2]],
    )
    return GeneratorSetModel(
        name="generator_set_sampled_model_2mw",
        resource=resource,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


@pytest.fixture
def generator_set_sampled_model_1000mw() -> GeneratorSetModel:
    resource = MemoryResource(
        headers=["POWER", "FUEL"],
        data=[[0, 0.1, 1, 1000], [0, 0.1, 1, 1000]],
    )
    return GeneratorSetModel(
        name="generator_set_sampled_model_1000mw",
        resource=resource,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


@pytest.fixture
def genset_2mw_dto(fuel_dto, electricity_consumer_factory, generator_set_sampled_model_2mw):
    def _genset_2mw_dto(variables: VariablesMap) -> GeneratorSetEnergyComponent:
        regularity = Regularity(
            expression_evaluator=variables, target_period=variables.get_period(), expression_input=1
        )
        return GeneratorSetEnergyComponent(
            id=uuid4(),
            path_id=PathID("genset"),
            fuel={Period(datetime(1900, 1, 1)): fuel_dto},
            generator_set_model={
                Period(datetime(1900, 1, 1)): generator_set_sampled_model_2mw,
            },
            consumers=[electricity_consumer_factory(variables)],
            regularity=regularity,
            component_type=ComponentType.GENERATOR_SET,
            expression_evaluator=variables,
        )

    return _genset_2mw_dto


@pytest.fixture
def genset_1000mw_late_startup_dto(fuel_dto, electricity_consumer_factory, generator_set_sampled_model_1000mw):
    def _genset_1000mw_late_startup_dto(variables: VariablesMap) -> GeneratorSetEnergyComponent:
        regularity = Regularity(
            expression_evaluator=variables, target_period=variables.get_period(), expression_input=1
        )
        return GeneratorSetEnergyComponent(
            id=uuid4(),
            path_id=PathID("genset_late_startup"),
            fuel={Period(datetime(1900, 1, 1)): fuel_dto},
            generator_set_model={
                Period(datetime(2022, 1, 1)): generator_set_sampled_model_1000mw,
            },
            consumers=[electricity_consumer_factory(variables)],
            regularity=regularity,
            component_type=ComponentType.GENERATOR_SET,
            expression_evaluator=variables,
        )

    return _genset_1000mw_late_startup_dto
