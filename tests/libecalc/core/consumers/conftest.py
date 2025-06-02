import uuid
from datetime import datetime

import pytest

import libecalc.common.energy_usage_type
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.physical_units import GeneratorPhysicalUnit
from libecalc.domain.process import dto
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_component import (
    GeneratorSetEnergyComponent,
)
from libecalc.common.component_type import ComponentType
from libecalc.common.time_utils import Period
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import VariablesMap
from libecalc.domain.regularity import Regularity
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_entities import MemoryResource


@pytest.fixture
def methane_values():
    return [0.005, 1.5, 3, 4]


@pytest.fixture
def variables_map(methane_values):
    return VariablesMap(
        variables={"TSC1;Methane_rate": methane_values},
        time_vector=[
            datetime(2000, 1, 1, 0, 0),
            datetime(2001, 1, 1, 0, 0),
            datetime(2002, 1, 1),
            datetime(2003, 1, 1, 0, 0),
        ],
    )


@pytest.fixture
def tabulated_fuel_consumer(fuel_gas) -> FuelConsumer:
    tabulated = dto.TabulatedConsumerFunction(
        model=dto.TabulatedData(
            headers=["RATE", "FUEL"],
            data=[[0, 1, 2], [0, 2, 4]],
            energy_usage_adjustment_constant=0.0,
            energy_usage_adjustment_factor=1.0,
        ),
        variables=[dto.Variables(name="RATE", expression=Expression.setup_from_expression(value="RATE"))],
        energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
    )
    variables = VariablesMap(
        variables={},
        time_vector=[Period(datetime(1900, 1, 1)).start, Period(datetime(1900, 1, 1)).end],
    )
    regularity = Regularity.create(
        expression_input=1,
        expression_evaluator=variables,
    )
    return FuelConsumer(
        path_id=PathID("fuel_consumer"),
        component_type=ComponentType.GENERIC,
        fuel=fuel_gas,
        energy_usage_model={Period(datetime(1900, 1, 1)): tabulated},
        user_defined_category={Period(datetime(1900, 1, 1)): "MISCELLANEOUS"},
        regularity=regularity,
        expression_evaluator=variables,
    )


@pytest.fixture
def direct_el_consumer():
    def _direct_el_consumer(variables: VariablesMap) -> ElectricityConsumer:
        regularity = Regularity.create(expression_evaluator=variables, expression_input=1)
        return ElectricityConsumer(
            path_id=PathID("direct_consumer"),
            component_type=ComponentType.GENERIC,
            user_defined_category={Period(datetime(1900, 1, 1)): "FIXED-PRODUCTION-LOAD"},
            energy_usage_model={
                Period(datetime(2020, 1, 1), datetime(2021, 1, 1)): dto.DirectConsumerFunction(
                    load=Expression.setup_from_expression(value=1),
                    energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.POWER,
                    consumption_rate_type=RateType.STREAM_DAY,
                ),
                Period(datetime(2021, 1, 1), datetime(2022, 1, 1)): dto.DirectConsumerFunction(  # Run above capacity
                    load=Expression.setup_from_expression(value=2),
                    energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.POWER,
                    consumption_rate_type=RateType.STREAM_DAY,
                ),
                Period(datetime(2022, 1, 1), datetime(2023, 1, 1)): dto.DirectConsumerFunction(  # Run above capacity
                    load=Expression.setup_from_expression(value=10),
                    energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.POWER,
                    consumption_rate_type=RateType.STREAM_DAY,
                ),
                Period(datetime(2023, 1, 1)): dto.DirectConsumerFunction(  # Ensure we handle 0 load as well.
                    load=Expression.setup_from_expression(value=0),
                    energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.POWER,
                    consumption_rate_type=RateType.STREAM_DAY,
                ),
            },
            regularity=regularity,
            expression_evaluator=variables,
        )

    return _direct_el_consumer


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
def genset_2mw_dto(fuel_dto, direct_el_consumer, generator_set_sampled_model_2mw):
    def _genset_2mw_dto(variables: VariablesMap) -> GeneratorSetEnergyComponent:
        regularity = Regularity.create(expression_evaluator=variables, expression_input=1)
        return GeneratorSetEnergyComponent(
            path_id=PathID("genset"),
            user_defined_category={Period(datetime(1900, 1, 1)): "TURBINE-GENERATOR"},
            fuel={Period(datetime(1900, 1, 1)): fuel_dto},
            generator_set_model={
                Period(datetime(1900, 1, 1)): generator_set_sampled_model_2mw,
            },
            consumers=[direct_el_consumer(variables)],
            regularity=regularity,
            component_type=ComponentType.GENERATOR_SET,
            expression_evaluator=variables,
            physical_unit=GeneratorPhysicalUnit(PathID(name="Generator", unique_id=uuid.uuid4())),
        )

    return _genset_2mw_dto


@pytest.fixture
def genset_1000mw_late_startup_dto(fuel_dto, direct_el_consumer, generator_set_sampled_model_1000mw):
    def _genset_1000mw_late_startup_dto(variables: VariablesMap) -> GeneratorSetEnergyComponent:
        regularity = Regularity.create(expression_evaluator=variables, expression_input=1)
        return GeneratorSetEnergyComponent(
            path_id=PathID("genset_late_startup"),
            user_defined_category={Period(datetime(1900, 1, 1)): "TURBINE-GENERATOR"},
            fuel={Period(datetime(1900, 1, 1)): fuel_dto},
            generator_set_model={
                Period(datetime(2022, 1, 1)): generator_set_sampled_model_1000mw,
            },
            consumers=[direct_el_consumer(variables)],
            regularity=regularity,
            component_type=ComponentType.GENERATOR_SET,
            expression_evaluator=variables,
            physical_unit=GeneratorPhysicalUnit(PathID(name="Generator", unique_id=uuid.uuid4())),
        )

    return _genset_1000mw_late_startup_dto
