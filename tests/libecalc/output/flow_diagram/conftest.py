import datetime

import pytest

import libecalc.common.energy_usage_type
import libecalc.dto.fuel_type
from libecalc.common.component_type import ComponentType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.domain.hydrocarbon_export import HydrocarbonExport
from libecalc.domain.infrastructure.energy_components.asset.asset import Asset
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.installation.installation import Installation
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.consumer_function import (
    CompressorSystemConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    ConsumerSystemOperationalSettingExpressions,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.types import ConsumerSystemComponent
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.process.compressor import dto
from libecalc.domain.process.compressor.core import create_compressor_model
from libecalc.domain.regularity import Regularity
from libecalc.dto.emission import Emission
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.presentation.flow_diagram.flow_diagram_dtos import Flow, FlowType, Node, NodeType

FUEL_NODE = Node(id="fuel-input", title="Fuel", type=NodeType.INPUT_OUTPUT_NODE)
INPUT_NODE = Node(id="input", title="Input", type=NodeType.INPUT_OUTPUT_NODE)
EMISSION_NODE = Node(id="emission-output", title="Emission", type=NodeType.INPUT_OUTPUT_NODE)

INSTALLATION_NAME = "Installation"

FUEL_FLOW = Flow(id="fuel-flow", label="Fuel", type=FlowType.FUEL)
EMISSIONS_FLOW = Flow(id="emission-flow", label="Emissions", type=FlowType.EMISSION)
ELECTRICITY_FLOW = Flow(
    id="electricity-flow",
    label="Electricity",
    type=FlowType.ELECTRICITY,
)


def compressor_system_compressor_fd(name: str) -> ConsumerSystemComponent:
    """Create a compressor system, only relevant property is the name when used to generate a FlowDiagram
    :param name:
    :return:
    """
    return ConsumerSystemComponent(
        name=name,
        facility_model=create_compressor_model(
            dto.CompressorSampled(
                energy_usage_values=[0, 4500, 9500],
                rate_values=[0, 5000, 10000],
                suction_pressure_values=[5, 5, 5],
                discharge_pressure_values=[50, 50, 50],
                energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
                energy_usage_adjustment_constant=0,
                energy_usage_adjustment_factor=1.0,
            )
        ),
    )


@pytest.fixture
def fuel_type_fd() -> libecalc.dto.fuel_type.FuelType:
    return libecalc.dto.fuel_type.FuelType(
        name="fuel_gas",
        emissions=[
            Emission(
                name="co2",
                factor=Expression.setup_from_expression(value="2.20"),
            )
        ],
    )


@pytest.fixture
def compressor_system_consumer_dto_fd(
    fuel_type_fd,
    expression_evaluator_factory,
    condition_factory,
    power_loss_factor_factory,
) -> FuelConsumer:
    expression_evaluator = expression_evaluator_factory.from_time_vector(
        [datetime.datetime(1900, 1, 1), datetime.datetime.max]
    )
    regularity = Regularity(
        expression_evaluator=expression_evaluator,
        target_period=expression_evaluator.get_period(),
        expression_input=1,
    )
    power_loss_factor_empty = power_loss_factor_factory(expression_evaluator=expression_evaluator)
    condition_empty = condition_factory(expression_evaluator=expression_evaluator)

    return FuelConsumer(
        path_id=PathID("Compressor system 1"),
        component_type=ComponentType.COMPRESSOR_SYSTEM,
        user_defined_category={
            Period(
                datetime.datetime(1900, 1, 1), datetime.datetime(2021, 1, 1)
            ): ConsumerUserDefinedCategoryType.COMPRESSOR
        },
        fuel={Period(datetime.datetime(1900, 1, 1), datetime.datetime(2021, 1, 1)): fuel_type_fd},
        regularity=regularity,
        energy_usage_model=TemporalModel(
            {
                Period(datetime.datetime(2018, 1, 1), datetime.datetime(2020, 1, 1)): CompressorSystemConsumerFunction(
                    consumer_components=[
                        compressor_system_compressor_fd("compressor1"),
                        compressor_system_compressor_fd("compressor2"),
                    ],
                    operational_settings_expressions=[
                        ConsumerSystemOperationalSettingExpressions(
                            rates=[
                                Expression.setup_from_expression(value=5),
                                Expression.setup_from_expression(value=0),
                            ],
                            suction_pressures=[
                                Expression.setup_from_expression(value=3),
                                Expression.setup_from_expression(value=3),
                            ],
                            discharge_pressures=[
                                Expression.setup_from_expression(value=200),
                                Expression.setup_from_expression(value=200),
                            ],
                        ),
                        ConsumerSystemOperationalSettingExpressions(
                            rates=[
                                Expression.setup_from_expression(value=2.5),
                                Expression.setup_from_expression(value=2.5),
                            ],
                            suction_pressures=[Expression.setup_from_expression(value=3)] * 2,
                            discharge_pressures=[Expression.setup_from_expression(value=200)] * 2,
                        ),
                    ],
                    condition=condition_empty,
                    regularity=regularity,
                    power_loss_factor=power_loss_factor_empty,
                ),
                Period(datetime.datetime(2020, 1, 1), datetime.datetime(2021, 1, 1)): CompressorSystemConsumerFunction(
                    consumer_components=[
                        compressor_system_compressor_fd("compressor1"),
                        compressor_system_compressor_fd("compressor2"),
                        compressor_system_compressor_fd("compressor3"),
                    ],
                    operational_settings_expressions=[
                        ConsumerSystemOperationalSettingExpressions(
                            rates=[
                                Expression.setup_from_expression(value=5),
                                Expression.setup_from_expression(value=0),
                                Expression.setup_from_expression(value=0),
                            ],
                            suction_pressures=[
                                Expression.setup_from_expression(value=3),
                                Expression.setup_from_expression(value=3),
                                Expression.setup_from_expression(value=3),
                            ],
                            discharge_pressures=[
                                Expression.setup_from_expression(value=200),
                                Expression.setup_from_expression(value=200),
                                Expression.setup_from_expression(value=200),
                            ],
                        ),
                        ConsumerSystemOperationalSettingExpressions(
                            rates=[
                                Expression.setup_from_expression(value=1.65),
                                Expression.setup_from_expression(value=1.65),
                                Expression.setup_from_expression(value=1.7),
                            ],
                            suction_pressures=[Expression.setup_from_expression(value=3)] * 3,
                            discharge_pressures=[Expression.setup_from_expression(value=200)] * 3,
                        ),
                    ],
                    condition=condition_empty,
                    regularity=regularity,
                    power_loss_factor=power_loss_factor_empty,
                ),
            }
        ),
        expression_evaluator=expression_evaluator,
    )


@pytest.fixture
def compressor_consumer_dto_fd(
    fuel_type_fd, expression_evaluator_factory, direct_expression_model_factory
) -> FuelConsumer:
    expression_evaluator = expression_evaluator_factory.from_time_vector(
        [datetime.datetime(1900, 1, 1), datetime.datetime.max]
    )
    return FuelConsumer(
        path_id=PathID("Compressor 1"),
        component_type=ComponentType.GENERIC,
        user_defined_category={
            Period(
                datetime.datetime(1900, 1, 1), datetime.datetime(2021, 1, 1)
            ): ConsumerUserDefinedCategoryType.COMPRESSOR
        },
        fuel={Period(datetime.datetime(1900, 1, 1), datetime.datetime(2021, 1, 1)): fuel_type_fd},
        energy_usage_model=TemporalModel(
            {
                Period(datetime.datetime(2019, 1, 1), datetime.datetime(2021, 1, 1)): direct_expression_model_factory(
                    energy_usage_expression=5,
                    energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
                    expression_evaluator=expression_evaluator,
                )
            }
        ),
        regularity=Regularity(
            expression_evaluator=expression_evaluator,
            target_period=expression_evaluator.get_period(),
            expression_input=1,
        ),
        expression_evaluator=expression_evaluator,
    )


@pytest.fixture
def installation_with_dates_dto_fd(
    compressor_system_consumer_dto_fd: FuelConsumer,
    compressor_consumer_dto_fd: FuelConsumer,
    expression_evaluator_factory,
) -> Asset:
    expression_evaluator = expression_evaluator_factory.from_time_vector(
        time_vector=[datetime.datetime(1900, 1, 1), datetime.datetime(2021, 1, 1)]
    )
    regularity = Regularity(
        expression_evaluator=expression_evaluator,
        target_period=expression_evaluator.get_period(),
        expression_input=1,
    )
    return Asset(
        path_id=PathID("installation_with_dates"),
        installations=[
            Installation(
                path_id=PathID("Installation1"),
                fuel_consumers=[compressor_system_consumer_dto_fd, compressor_consumer_dto_fd],
                regularity=regularity,
                hydrocarbon_export=HydrocarbonExport(
                    expression_evaluator=expression_evaluator,
                    target_period=expression_evaluator.get_period(),
                    expression_input=0,
                    regularity=regularity,
                ),
                expression_evaluator=expression_evaluator,
            )
        ],
    )
