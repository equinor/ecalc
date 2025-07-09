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
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_component import (
    GeneratorSetEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated import (
    TabularConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated.common import VariableExpression
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.regularity import Regularity
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_entities import MemoryResource


@pytest.fixture
def methane_values():
    return [0.005, 1.5, 3, 4]


@pytest.fixture
def tabulated_fuel_consumer_factory(fuel_gas, expression_evaluator_factory, tabulated_energy_usage_model_factory):
    def create_tabulated_fuel_consumer(
        expression_evaluator: ExpressionEvaluator,
    ) -> FuelConsumer:
        tabulated = tabulated_energy_usage_model_factory(function_values=[0, 2, 4], variables={"RATE": [0, 1, 2]})

        regularity = Regularity(
            expression_input=1,
            expression_evaluator=expression_evaluator,
            target_period=expression_evaluator.get_period(),
        )
        return FuelConsumer(
            id=uuid4(),
            path_id=PathID("fuel_consumer"),
            component_type=ComponentType.GENERIC,
            fuel=fuel_gas,
            energy_usage_model=TemporalModel({Period(datetime(1900, 1, 1)): tabulated}),
            user_defined_category={Period(datetime(1900, 1, 1)): ConsumerUserDefinedCategoryType.MISCELLANEOUS},
            regularity=regularity,
            expression_evaluator=expression_evaluator,
        )

    return create_tabulated_fuel_consumer


@pytest.fixture
def electricity_consumer_factory(direct_expression_model_factory):
    def _create_electricity_consumer(
        expression_evaluator: ExpressionEvaluator, energy_usage_model: TemporalModel = None
    ) -> ElectricityConsumer:
        if energy_usage_model is None:
            energy_usage_model = TemporalModel(
                {
                    Period(datetime(2020, 1, 1), datetime(2021, 1, 1)): direct_expression_model_factory(
                        expression=Expression.setup_from_expression(value=1),
                        energy_usage_type=EnergyUsageType.POWER,
                        consumption_rate_type=RateType.STREAM_DAY,
                    ),
                    Period(
                        datetime(2021, 1, 1), datetime(2022, 1, 1)
                    ): direct_expression_model_factory(  # Run above capacity
                        expression=Expression.setup_from_expression(value=2),
                        energy_usage_type=EnergyUsageType.POWER,
                        consumption_rate_type=RateType.STREAM_DAY,
                    ),
                    Period(
                        datetime(2022, 1, 1), datetime(2023, 1, 1)
                    ): direct_expression_model_factory(  # Run above capacity
                        expression=Expression.setup_from_expression(value=10),
                        energy_usage_type=EnergyUsageType.POWER,
                        consumption_rate_type=RateType.STREAM_DAY,
                    ),
                    Period(datetime(2023, 1, 1)): direct_expression_model_factory(  # Ensure we handle 0 load as well.
                        expression=Expression.setup_from_expression(value=0),
                        energy_usage_type=EnergyUsageType.POWER,
                        consumption_rate_type=RateType.STREAM_DAY,
                    ),
                }
            )

        regularity = Regularity(
            expression_evaluator=expression_evaluator,
            target_period=expression_evaluator.get_period(),
            expression_input=1,
        )
        return ElectricityConsumer(
            id=uuid4(),
            path_id=PathID("direct_consumer"),
            component_type=ComponentType.GENERIC,
            user_defined_category={Period(datetime(1900, 1, 1)): ConsumerUserDefinedCategoryType.FIXED_PRODUCTION_LOAD},
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
            user_defined_category={Period(datetime(1900, 1, 1)): "TURBINE-GENERATOR"},
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
            user_defined_category={Period(datetime(1900, 1, 1)): "TURBINE-GENERATOR"},
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


@pytest.fixture
def tabulated_energy_usage_model_factory(tabular_consumer_function_factory):
    def create_tabulated_energy_usage_model(
        function_values: list[float],
        variables: dict[str, list[float]],
        energy_usage_adjustment_constant: float = 0.0,
        energy_usage_adjustment_factor: float = 1.0,
    ) -> TabularConsumerFunction:
        return TabularConsumerFunction(
            headers=[*variables.keys(), "FUEL"],
            data=[*variables.values(), function_values],
            energy_usage_adjustment_factor=energy_usage_adjustment_factor,
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
            variables_expressions=[
                VariableExpression(name=name, expression=Expression.setup_from_expression(name))
                for name in variables.keys()
            ],
        )

    return create_tabulated_energy_usage_model
